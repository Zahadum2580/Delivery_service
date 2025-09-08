import asyncio
import json
import traceback
from typing import Any, Dict, List

import aio_pika
from aio_pika import IncomingMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.mongo import MongoService, get_mongo_service
from app.db.mysql import async_session
from app.models.packages import Package
from app.schemas.packages import PackageAdvanced
from app.workers.tasks import calculate_delivery_cost, get_type_name, validate_type_id

RABBITMQ_URL = (
    f"amqp://{settings.RABBIT_USER}:{settings.RABBIT_PASSWORD}@"
    f"{settings.RABBIT_HOST}:5672/"
)

QUEUE_NAME = "packages_queue"


# MySQL
MYSQL_BUFFER_SIZE = 10
MYSQL_BUFFER_TIMEOUT = 2
MAX_RETRIES = 5
message_buffer: List[PackageAdvanced] = []
buffer_lock = asyncio.Lock()

# Mongo
MONGO_BUFFER_SIZE = 10
MONGO_BUFFER_TIMEOUT = 2
mongo_buffer: List[PackageAdvanced] = []
mongo_buffer_lock = asyncio.Lock()

# MongoService — будет инициализирован в main()
mongo_service: MongoService | None = None


async def process_package_message(message: IncomingMessage):
    """
    Обрабатывает сообщение из RabbitMQ.
    Валидирует, рассчитывает стоимость доставки,
    сохраняет в буферы для MySQL и MongoDB.
    """

    try:
        async with message.process():
            payload: Dict[str, Any] = json.loads(message.body)

            # Проверяем type_id и получаем type_name
            type_id = await validate_type_id(payload.get("type_id"))
            type_name = await get_type_name(type_id)
            payload["type_id"] = type_id
            payload["type_name"] = type_name

            # Рассчитываем delivery_cost
            delivery_cost = await calculate_delivery_cost(
                payload.get("weight_kg", 0), payload.get("content_value_usd", 0)
            )
            payload["delivery_cost_rub"] = delivery_cost

            # Создаём Pydantic-модель
            package = PackageAdvanced(**payload)

            # Добавляем пакет в Mongo буфер
            asyncio.create_task(save_package_batch(package))

            # Добавляем в буфер для MySQL
            async with buffer_lock:
                message_buffer.append(package)
                if len(message_buffer) >= MYSQL_BUFFER_SIZE:
                    await flush_mysql_buffer_locked()

    except Exception:
        print("Error processing message:")
        traceback.print_exc()


async def flush_mysql_buffer_locked():
    """Флашит буфер MySQL в базу данных с ретраями."""
    if not message_buffer:
        return

    retries = 0
    while retries < MAX_RETRIES:
        try:
            async with async_session() as session:
                db: AsyncSession = session
                packages = [
                    Package(
                        name=p.name,
                        weight_kg=p.weight_kg,
                        content_value_usd=p.content_value_usd,
                        type_id=p.type_id,
                        type_name=p.type_name,
                        session_id=p.session_id,
                        delivery_cost_rub=p.delivery_cost_rub,
                    )
                    for p in message_buffer
                ]
                db.add_all(packages)
                await db.commit()
                print(f"Flushed {len(packages)} packages to MySQL")
                message_buffer.clear()
                return
        except Exception as e:
            retries += 1
            wait_time = 2**retries
            print(f"MySQL flush error (attempt {retries}/{MAX_RETRIES}): {e}")
            traceback.print_exc()
            await asyncio.sleep(wait_time)

    print("Failed to flush MySQL buffer after max retries, messages remain in buffer.")


async def periodic_mysql_flush():
    """Периодически флашит буфер MySQL по таймауту."""

    while True:
        await asyncio.sleep(MYSQL_BUFFER_TIMEOUT)
        async with buffer_lock:
            await flush_mysql_buffer_locked()


async def save_package_batch(package: PackageAdvanced):
    """Добавляет пакет в буфер Mongo и триггерит батчевую запись."""
    async with mongo_buffer_lock:
        mongo_buffer.append(package)
        if len(mongo_buffer) >= MONGO_BUFFER_SIZE:
            await flush_mongo_buffer_locked()


async def flush_mongo_buffer_locked():
    """Флашит буфер MongoDB в базу данных."""
    if not mongo_buffer or mongo_service is None:
        return

    batch = mongo_buffer.copy()
    mongo_buffer.clear()

    try:
        docs = [p.model_dump() for p in batch]
        collection = await mongo_service.get_daily_collection()
        await collection.insert_many(docs)
        print(f"Flushed {len(batch)} packages to MongoDB")
    except Exception as e:
        print(f"MongoDB batch save error ({len(batch)} packages): {e}")
        traceback.print_exc()
        # При ошибке возвращаем пакеты обратно в буфер
        async with mongo_buffer_lock:
            mongo_buffer[:0] = batch  # prepend обратно


async def periodic_mongo_flush():
    """Периодически флашит буфер Mongo по таймауту."""
    while True:
        await asyncio.sleep(MONGO_BUFFER_TIMEOUT)
        async with mongo_buffer_lock:
            await flush_mongo_buffer_locked()


async def main():
    """Основная функция воркера."""
    global mongo_service
    mongo_service = await get_mongo_service()

    print("Connecting to RabbitMQ...")
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()

    queue = await channel.declare_queue(QUEUE_NAME, durable=True)
    await queue.consume(process_package_message)
    print(f"Worker listening on queue '{QUEUE_NAME}'...")

    # Запускаем периодические флашеры для буферов MySQL и Mongo
    asyncio.create_task(periodic_mysql_flush())
    asyncio.create_task(periodic_mongo_flush())

    await asyncio.Future()  # держим воркер живым


if __name__ == "__main__":
    asyncio.run(main())
