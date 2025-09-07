import logging
from typing import Optional

import aio_pika

from app.core.config import settings
from app.schemas.packages import PackageIn

logger = logging.getLogger(__name__)

RABBITMQ_URL = (
    f"amqp://{settings.RABBIT_USER}:{settings.RABBIT_PASSWORD}@"
    f"{settings.RABBIT_HOST}:5672/"
)
QUEUE_NAME = "packages_queue"


class Producer:
    def __init__(self):
        self.connection: Optional[aio_pika.RobustConnection] = None
        self.channel: Optional[aio_pika.RobustChannel] = None
        self.queue_name: str = QUEUE_NAME

    async def connect(self):
        """Подключение к RabbitMQ и создание канала"""
        if self.connection is None or self.connection.is_closed:
            self.connection = await aio_pika.connect_robust(RABBITMQ_URL)
            self.channel = await self.connection.channel()
            await self.channel.declare_queue(self.queue_name, durable=True)
            logger.info("Connected to RabbitMQ and declared queue")

    async def disconnect(self):
        """Закрытие соединения"""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("Disconnected from RabbitMQ")

    async def send_package_to_queue(self, package: PackageIn) -> None:
        """Отправка посылки в очередь"""
        if not self.connection or self.connection.is_closed:
            await self.connect()

        channel = self.channel
        if channel is None:
            raise RuntimeError("Channel is not initialized after connection")

        await channel.default_exchange.publish(
            aio_pika.Message(
                body=package.model_dump_json().encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=self.queue_name,
        )

        logger.info(f"Package sent to queue: session_id={package.session_id}")


async def get_producer() -> Producer:
    return Producer()
