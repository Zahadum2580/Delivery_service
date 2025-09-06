import asyncio
import httpx
import logging
import traceback
from typing import Optional
from app.db.redis import redis_client
from app.core.config import settings
from app.db.mysql import async_session
from sqlalchemy import select
from app.models.types import Type

logger = logging.getLogger(__name__)

# --- USD_RUB ---
CBR_CACHE_KEY = "cbr:usd_rub"
CBR_CACHE_TTL = 3600  # 1 час
CBR_LOCK_KEY = "cbr:usd_rub:lock"
CBR_LOCK_TTL = 10  # секунд

# --- Package types ---
TYPE_CACHE_KEY = "package_types"
TYPE_CACHE_TTL = 3600  # 1 час
DEFAULT_TYPE_ID = 3
DEFAULT_TYPE_NAME = "разное"


# --- USD_RUB functions ---
async def get_usd_to_rub_rate() -> Optional[float]:
    try:
        cached = await redis_client.get(CBR_CACHE_KEY)
        if cached is not None:
            value = cached.decode() if isinstance(cached, (bytes, bytearray)) else str(cached)
            return float(value.replace(",", "."))
    except Exception as e:
        logger.warning("Redis GET failed for USD_RUB: %s", e)

    got_lock = await redis_client.set(CBR_LOCK_KEY, "1", ex=CBR_LOCK_TTL, nx=True)
    if not got_lock:
        logger.info("Another worker is fetching USD_RUB, waiting for cache...")
        delay = 0.5
        for _ in range(5):
            await asyncio.sleep(delay)
            try:
                cached = await redis_client.get(CBR_CACHE_KEY)
                if cached:
                    value = cached.decode() if isinstance(cached, (bytes, bytearray)) else str(cached)
                    return float(value.replace(",", "."))
            except Exception as e:
                logger.error("Redis GET after wait failed: %s", e)
                return None
            delay *= 2
        return None

    # fetch from CBR API
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(settings.CBR_DAILY_URL)
            resp.raise_for_status()
            data = resp.json()
            raw = data.get("Valute", {}).get("USD", {}).get("Value")
            if raw is None:
                logger.error("USD rate not found in CBR response")
                return None

            rate = float(str(raw).replace(",", "."))
            try:
                await redis_client.set(CBR_CACHE_KEY, str(rate), ex=CBR_CACHE_TTL)
            except Exception as e:
                logger.error("Redis SET failed for USD_RUB: %s", e)
            return rate
    except Exception:
        logger.exception("Unexpected error while fetching USD_RUB")
        return None
    finally:
        try:
            await redis_client.delete(CBR_LOCK_KEY)
        except Exception as e:
            logger.warning("Failed to release Redis lock: %s", e)


async def calculate_delivery_cost(weight_kg: float, content_value_usd: float) -> Optional[float]:
    """Обёртка calculate_delivery_cost с получением курса ЦБ РФ"""
    try:
        rate = await get_usd_to_rub_rate()
        if rate is None:
            return None
        return ((weight_kg * 0.5) + (content_value_usd * 0.01)) * rate
    except Exception:
        traceback.print_exc()
        return None


# --- Package types functions ---
async def load_type_cache():
    """Загружает типы посылок из MySQL в Redis"""
    async with async_session() as session:
        result = await session.execute(select(Type.id, Type.name))
        types = result.all()
        if types:
            async with redis_client.pipeline() as pipe:
                for id_, name in types:
                    await pipe.hset(TYPE_CACHE_KEY, id_, name)
                await pipe.expire(TYPE_CACHE_KEY, TYPE_CACHE_TTL)
                await pipe.execute()


async def get_type_name(type_id: Optional[int]) -> str:
    """Возвращает name по type_id через Redis, если не найдено — default"""
    if type_id is None:
        type_id = DEFAULT_TYPE_ID
    name = await redis_client.hget(TYPE_CACHE_KEY, type_id)
    if not name:
        await load_type_cache()
        name = await redis_client.hget(TYPE_CACHE_KEY, type_id)
        if not name:
            return DEFAULT_TYPE_NAME
    if isinstance(name, (bytes, bytearray)):
        name = name.decode()
    return name


async def validate_type_id(type_id: Optional[int]) -> int:
    """Проверяет существование type_id через Redis"""
    name = await get_type_name(type_id)
    if name == DEFAULT_TYPE_NAME:
        return DEFAULT_TYPE_ID
    return type_id
