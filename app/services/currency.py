import aioredis
import httpx

from app.core.config import settings

CACHE_KEY = "cbr_usd_rub"
CACHE_TTL = 60 * 60  # 1 час


class CurrencyService:
    def __init__(self):
        self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def get_usd_to_rub_rate(self) -> float | None:
        """
        Возвращает курс USD->RUB.
        Если не удалось получить курс из кэша и с ЦБ — возвращает None.
        """
        # Попробуем получить из кэша
        cached = await self.redis.get(CACHE_KEY)
        if cached:
            return float(cached)

        # Попробуем получить с ЦБ
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(settings.CBR_DAILY_URL, timeout=10.0)
                resp.raise_for_status()
                data = resp.json()
                usd_rate = data["Valute"]["USD"]["Value"]
        except Exception:
            usd_rate = None  # не удалось получить

        # Сохраняем в Redis, если есть
        if usd_rate is not None:
            await self.redis.set(CACHE_KEY, usd_rate, ex=CACHE_TTL)

        return usd_rate
