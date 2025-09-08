import asyncio
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi_filter import FilterDepends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_or_create_session_id
from app.db.mongo import MongoService, get_mongo_service
from app.db.mysql import get_session as get_async_session
from app.models.packages import Package
from app.models.types import Type
from app.schemas.packages import (
    DeliveryStatsOut,
    PackageBase,
    PackageIn,
    PackageOut,
    PackagesFilter,
)
from app.workers.producer import Producer, get_producer

logger = logging.getLogger(__name__)
router = APIRouter()


get_session_dep = Depends(get_or_create_session_id)
get_producer_dep = Depends(get_producer)
get_async_session_dep = Depends(get_async_session)
get_mongo_service_dep = Depends(get_mongo_service)
packages_filter_dep = FilterDepends(PackagesFilter)


@router.post("/packages/register")
async def register_package(
    package: PackageBase,
    request: Request,
    session_id: str = get_session_dep,
    producer: Producer = get_producer_dep,
):
    """
    Регистрация посылки.

    package: данные посылки
    """
    package_data: dict[str, Any] = package.model_dump()
    package_data["session_id"] = session_id

    async def send_package_background(data: dict[str, Any]):
        try:
            await producer.send_package_to_queue(PackageIn(**data))
            logger.info(
                f"Посылка отправлена в очередь: session_id={data['session_id']}"
            )
        except Exception:
            logger.exception(
                f"Ошибка отправки посылки в очередь: session_id={data['session_id']}"
            )

    asyncio.create_task(send_package_background(package_data))

    response = JSONResponse(
        content={"message": "Посылка зарегистрирована", "session_id": session_id}
    )

    # Ставим cookie только если это новая сессия
    if hasattr(request.state, "new_session_id"):
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            max_age=60 * 60 * 24 * 30,
            samesite="lax",
            secure=False,  # True если используем HTTPS
        )

    return response


@router.get("/packages/types")
async def get_package_types(
    db: AsyncSession = get_async_session_dep,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Получение типов посылок.
    """
    stmt = select(Type.id, Type.name).order_by(Type.id.asc())
    result = await db.execute(stmt)
    types = [{"id": row.id, "name": row.name} for row in result.all()]
    return {"types": types}


@router.get("/packages", response_model=Page[PackageOut])
async def get_my_packages(
    filters: PackagesFilter = packages_filter_dep,
    session_id: str = get_session_dep,
    db: AsyncSession = get_async_session_dep,
) -> Page[PackageOut]:
    """
    Получение посылок для текущей сессии.

    filters: фильтры для поиска посылок
    """
    stmt = select(Package).filter(Package.session_id == session_id)
    stmt = filters.filter(stmt)
    return await paginate(db, stmt)


@router.get("/packages/{package_id}", response_model=PackageOut)
async def get_package_by_id(
    package_id: int,
    db: AsyncSession = get_async_session_dep,
) -> PackageOut:
    """
    Получение сведений о посылке.

    package_id: ID посылки
    """
    stmt = select(Package).filter(Package.id == package_id)
    result = await db.execute(stmt)
    package = result.scalar_one_or_none()

    if not package:
        raise HTTPException(status_code=404, detail="Посылка не найдена")

    return package


@router.get("/stats", response_model=List[DeliveryStatsOut])
async def get_delivery_stats(
    date: str | None = None,
    mongo: MongoService = get_mongo_service_dep,
) -> List[DeliveryStatsOut]:
    """
    Получение статистики по доставкам за день.

    date: дата в формате `ДД_ММ_ГГГГ` (опционально, например `03_09_2025`).
    """
    return await mongo.get_delivery_stats(date)
