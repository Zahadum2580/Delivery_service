from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi_pagination import add_pagination

from app.api import api_router
from app.core.exceptions import register_exception_handlers
from app.core.logging import LoggingMiddleware
from app.workers.producer import Producer

producer = Producer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: подключаемся к RabbitMQ
    await producer.connect()
    yield
    # Shutdown: отключаемся от RabbitMQ
    await producer.disconnect()


app = FastAPI(title="Delivery Service", version="1.0.0", lifespan=lifespan)

# Подключаем middleware
app.add_middleware(LoggingMiddleware)

# Подключаем API роутеры
app.include_router(api_router)

# Подключаем пагинацию
add_pagination(app)

# подключаем обработчики исключений
register_exception_handlers(app)
