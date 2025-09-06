import asyncio
import logging
from typing import Any, Dict, List
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from fastapi_filter import FilterDepends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.mysql import get_session as get_async_session
from app.db.mongo import MongoService, get_mongo_service
from app.models.packages import Package
from app.models.types import Type
from app.schemas.packages import PackageBase, PackageIn, PackageOut, PackagesFilter, DeliveryStatsOut
from app.workers.producer import Producer, get_producer
from app.api.dependencies import get_or_create_session_id


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/packages/register")
async def register_package(
    package: PackageBase,
    request: Request,
    session_id: str = Depends(get_or_create_session_id),
    producer: Producer = Depends(get_producer)
):
    """
    Регистрируем посылку:
    - получаем session_id через dependency
    - валидируем как PackageIn
    - отправляем в RabbitMQ асинхронно в фоне
    - возвращаем ответ и при необходимости ставим cookie
    """
    package_data: dict[str, Any] = package.model_dump()
    package_data["session_id"] = session_id

    async def send_package_background(data: dict[str, Any]):
        try:
            await producer.send_package_to_queue(PackageIn(**data))
            logger.info(f"Package sent to queue: session_id={data['session_id']}")
        except Exception:
            logger.exception(f"Error sending package to queue: session_id={data['session_id']}")

    # Запускаем отправку в RabbitMQ в фоне, чтобы не блокировать Swagger/OpenAPI
    asyncio.create_task(send_package_background(package_data))

    response = JSONResponse(
        content={"message": "Package registered", "session_id": session_id}
    )

    # Ставим cookie только если это новая сессия
    if hasattr(request.state, "new_session_id"):
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            max_age=60 * 60 * 24 * 30,  # 30 дней
            samesite="Lax",
            # secure=True,  # включить в продакшене
        )

    return response


@router.get("/packages/types")
async def get_package_types(
    db: AsyncSession = Depends(get_async_session),
) -> Dict[str, List[Dict[str, Any]]]:
    """ Получаем список типов посылок """
    stmt = select(Type.id, Type.name).order_by(Type.id.asc())
    result = await db.execute(stmt)
    types = [{"id": row.id, "name": row.name} for row in result.all()]
    return {"types": types}


@router.get("/packages", response_model=Page[PackageOut])
async def get_my_packages(
    filters: PackagesFilter = FilterDepends(PackagesFilter),
    session_id: str = Depends(get_or_create_session_id),
    db: AsyncSession = Depends(get_async_session),
) -> Page[PackageOut]:
    """ Получаем список посылок для текущей сессии с возможностью фильтрации и пагинации """
    stmt = select(Package).filter(Package.session_id == session_id)
    stmt = filters.filter(stmt)
    return await paginate(db, stmt) 

@router.get("/packages/{package_id}", response_model=PackageOut)
async def get_package_by_id(
    package_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> PackageOut:
    """ Получаем посылку по ID, только если она принадлежит текущей сессии """
    stmt = select(Package).filter(Package.id == package_id)
    result = await db.execute(stmt)
    package = result.scalar_one_or_none()

    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    return package

@router.get("/stats", response_model=List[DeliveryStatsOut])
async def get_delivery_stats(
    date: str | None = None,
    mongo: MongoService = Depends(get_mongo_service),
) -> List[DeliveryStatsOut]:
    return await mongo.get_delivery_stats(date)