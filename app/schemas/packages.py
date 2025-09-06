import enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, NonNegativeFloat, Field, field_validator
from fastapi_filter.contrib.sqlalchemy import Filter
from app.core.utils import msk_now, round_2, round_3
from app.models.packages import Package


class PackageType(enum.IntEnum):
    ОДЕЖДА = 1
    ЭЛЕКТРОНИКА = 2
    РАЗНОЕ = 3


class PackageBase(BaseModel):
    name: str = Field(..., description="Название посылки", example="Ноутбук")
    weight_kg: NonNegativeFloat = Field(
        ..., description="Вес в кг (округляется до 3 знаков)", example=1.234
    )
    content_value_usd: NonNegativeFloat = Field(
        ..., description="Стоимость содержимого в USD (округляется до 2 знаков)", example=123.45
    )
    type_id: PackageType = Field(
        ..., description="ID типа посылки: 1=одежда, 2=электроника, 3=разное", example=2
    )

    @field_validator("weight_kg", mode="before")
    @classmethod
    def round_to_3_decimals(cls, v: NonNegativeFloat) -> NonNegativeFloat:
        return round_3(v)

    @field_validator("content_value_usd", mode="before")
    @classmethod
    def round_to_2_decimals(cls, v: NonNegativeFloat) -> NonNegativeFloat:
        return round_2(v)


class PackageIn(PackageBase):
    session_id: Optional[str] = Field(
        None, description="ID пользовательской сессии", example="550e8400-e29b-41d4-a716-446655440000"
    )


class PackageAdvanced(PackageIn):
    type_name: Optional[str] = Field(None, description="Название типа посылки", example="электроника")
    delivery_cost_rub: Optional[NonNegativeFloat] = Field(None, description="Стоимость доставки в рублях", example=1234.56)
    created_at: Optional[datetime] = Field(default_factory=msk_now, description="Московское время регистрации посылки")
    updated_at: Optional[datetime] = None

    @field_validator("delivery_cost_rub", mode="before")
    @classmethod
    def round_delivery_cost(cls, v: Optional[NonNegativeFloat]):
        if v is None:
            return None
        return round_2(v)

    class Config:
        from_attributes = True


class PackageOut(PackageAdvanced):
    id: int = Field(..., description="Уникальный ID посылки", example=1)


class PackagesFilter(Filter):
    """
    Схема для фильтрации GET-запросов по посылкам.
    Не содержит лишних полей, только те, по которым разрешена фильтрация.
    """

    type_id: Optional[PackageType] = Field(
        None, description="ID типа посылки: 1=одежда, 2=электроника, 3=разное", example=2
    )
    delivery_cost_rub__isnull: Optional[bool] = Field(
        None, description="Фильтр по наличию стоимости доставки (True/False)", example=True
    )

    class Constants(Filter.Constants):
        model = Package


class DeliveryStatsOut(BaseModel):
    type_id: int
    type_name: str
    total_delivery_cost: float