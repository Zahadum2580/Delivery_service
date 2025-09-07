import asyncio
import traceback
from datetime import timedelta
from typing import Any, Dict, List, Mapping, Sequence

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from app.core.config import settings
from app.core.utils import msk_now
from app.schemas.packages import DeliveryStatsOut, PackageAdvanced


class MongoService:
    MAX_CACHE_DAYS = 7

    def __init__(
        self, uri: str = settings.MONGO_URL, db_name: str = "delivery_results"
    ):
        self.client: AsyncIOMotorClient = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]
        self._daily_collections_cache: Dict[
            str, AsyncIOMotorCollection[Dict[str, Any]]
        ] = {}
        self._indexes_created: set[str] = set()

        # Лениво создаём индексы для сегодняшней коллекции
        asyncio.create_task(self._init_today_indexes())

    async def _init_today_indexes(self):
        """Создаёт индексы для сегодняшней коллекции при старте приложения"""
        collection = await self.get_daily_collection()
        await self.ensure_indexes_for_daily_collection(collection)

    async def ensure_indexes_for_daily_collection(
        self, collection: AsyncIOMotorCollection[Dict[str, Any]]
    ) -> None:
        if collection.name in self._indexes_created:
            return
        try:
            await collection.create_index("session_id")
            await collection.create_index("created_at")
            self._indexes_created.add(collection.name)
        except Exception:
            print(f"Error creating indexes for collection {collection.name}:")
            traceback.print_exc()

    def _cleanup_cache(self):
        """Удаляет коллекции из кэша старше MAX_CACHE_DAYS"""
        cutoff_date = msk_now() - timedelta(days=self.MAX_CACHE_DAYS)
        cutoff_str = cutoff_date.strftime("%d_%m_%Y")
        keys_to_remove = [
            date for date in self._daily_collections_cache if date < cutoff_str
        ]
        for key in keys_to_remove:
            del self._daily_collections_cache[key]
            self._indexes_created.discard(f"packages_{key}")

    async def get_daily_collection(
        self, date: str | None = None
    ) -> AsyncIOMotorCollection[Dict[str, Any]]:
        if not date:
            date = msk_now().strftime("%d_%m_%Y")

        self._cleanup_cache()

        if date in self._daily_collections_cache:
            return self._daily_collections_cache[date]

        collection_name = f"packages_{date}"
        collection: AsyncIOMotorCollection[Dict[str, Any]] = self.db[collection_name]

        await self.ensure_indexes_for_daily_collection(collection)

        self._daily_collections_cache[date] = collection
        return collection

    async def save_package(self, package: PackageAdvanced) -> None:
        try:
            doc: Dict[str, Any] = package.model_dump()
            collection = await self.get_daily_collection()
            await collection.insert_one(doc)
        except Exception:
            print("Error saving package to MongoDB:")
            traceback.print_exc()

    async def get_delivery_stats(
        self, date: str | None = None
    ) -> List[DeliveryStatsOut]:
        collection = await self.get_daily_collection(date)
        pipeline: Sequence[Mapping[str, Any]] = [
            {"$match": {"delivery_cost_rub": {"$ne": None}}},
            {
                "$group": {
                    "_id": {"type_id": "$type_id", "type_name": "$type_name"},
                    "total_delivery_cost": {"$sum": "$delivery_cost_rub"},
                }
            },
            {"$sort": {"_id.type_id": 1}},
        ]
        results = await collection.aggregate(pipeline).to_list(length=None)
        return [
            DeliveryStatsOut(
                type_id=r["_id"]["type_id"],
                type_name=r["_id"]["type_name"],
                total_delivery_cost=r["total_delivery_cost"],
            )
            for r in results
        ]


# Синглтон
_mongo_service: MongoService | None = None


async def get_mongo_service() -> MongoService:
    global _mongo_service
    if _mongo_service is None:
        _mongo_service = MongoService()
        await _mongo_service._init_today_indexes()
    return _mongo_service
