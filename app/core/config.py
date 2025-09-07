from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # общие
    APP_NAME: str = "delivery_service"
    APP_ENV: str = "development"
    TZ: str = "Europe/Moscow"

    # MySQL
    MYSQL_DB: str = "mydb"
    MYSQL_USER: str = "myuser"
    MYSQL_PASSWORD: str = "mypassword"
    MYSQL_ROOT_PASSWORD: str = "root"
    MYSQL_HOST: str = "mysql"
    MYSQL_PORT: int = 3306

    # RabbitMQ (переменные для образа и для приложения)
    RABBITMQ_DEFAULT_USER: Optional[str] = None
    RABBITMQ_DEFAULT_PASS: Optional[str] = None
    RABBIT_HOST: str = "rabbitmq"
    RABBIT_USER: Optional[str] = None
    RABBIT_PASSWORD: Optional[str] = None

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    # Mongo
    MONGO_HOST: str = "mongo"
    MONGO_PORT: int = 27017

    # внешние AP
    CBR_DAILY_URL: str = "https://www.cbr-xml-daily.ru/daily_json.js"

    # ----- computed values -----
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return (
            f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}?charset=utf8mb4"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        # нужен для Alembic (sync driver)
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}?charset=utf8mb4"
        )

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def MONGO_URL(self) -> str:
        return f"mongodb://{self.MONGO_HOST}:{self.MONGO_PORT}"

    class Config:
        env_file = ".env"
        extra = "ignore"
        case_sensitive = False


settings = Settings()
