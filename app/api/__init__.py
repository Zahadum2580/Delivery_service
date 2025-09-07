from fastapi import APIRouter

from app.api.routers import packages_router as packages

# Главный роутер приложения
api_router = APIRouter()

# Подключаем все подроутеры
api_router.include_router(packages.router, prefix="/api", tags=["packages"])
