import enum
from datetime import datetime
from typing import Optional

from fastapi_filter.contrib.sqlalchemy import Filter
from pydantic import BaseModel, Field, NonNegativeFloat, field_validator

from app.core.utils import msk_now, round_2, round_3
from app.models.packages import Package


class PackageType(enum.IntEnum):
    ОДЕЖДА = 1
    ЭЛЕКТРОНИКА = 2
    РАЗНОЕ = 3


class PackageBase(BaseModel):
    """
    Базовая схема посылки с валидацией и описаниями полей.
    """

    name: str = Field(
        ...,
        description="Название посылки",
        json_schema_extra={"example": "Ноутбук"},
    )
    weight_kg: NonNegativeFloat = Field(
        ...,
        description="Вес в кг (округляется до 3 знаков)",
        json_schema_extra={"example": 1.234},
    )
    content_value_usd: NonNegativeFloat = Field(
        ...,
        description="Стоимость содержимого в USD (округляется до 2 знаков)",
        json_schema_extra={"example": 123.45},
    )
    type_id: int = Field(
        ...,
        description="ID типа посылки: 1=одежда, 2=электроника, 3=разное",
        json_schema_extra={"example": 2},
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
    """
    Схема для создания посылки.
    """

    session_id: Optional[str] = Field(
        None,
        description="ID пользовательской сессии",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"},
    )


class PackageAdvanced(PackageIn):
    """
    Расширенная схема посылки с дополнительными полями.
    """

    type_name: Optional[str] = Field(
        None,
        description="Название типа посылки",
        json_schema_extra={"example": "электроника"},
    )
    delivery_cost_rub: Optional[NonNegativeFloat] = Field(
        None,
        description="Стоимость доставки в рублях",
        json_schema_extra={"example": 1234.56},
    )
    created_at: Optional[datetime] = Field(
        default_factory=msk_now, description="Московское время регистрации посылки"
    )
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
    """
    Схема для ответа API с полным набором полей посылки.
    """

    id: int = Field(
        ..., description="Уникальный ID посылки", json_schema_extra={"example": 1}
    )


class PackagesFilter(Filter):
    """
    Схема для фильтрации GET-запросов по посылкам.
    """

    type_id: Optional[PackageType] = Field(
        None,
        description="ID типа посылки: 1=одежда, 2=электроника, 3=разное",
        json_schema_extra={"example": 2},
    )
    delivery_cost_rub__isnull: Optional[bool] = Field(
        None,
        description="Фильтр по наличию стоимости доставки (True/False)",
        json_schema_extra={"example": True},
    )

    class Constants(Filter.Constants):
        model = Package


class DeliveryStatsOut(BaseModel):
    """
    Схема для ответа API с общей статистикой по доставкам.
    """

    type_id: int = Field(
        ...,
        description="ID типа посылки: 1=одежда, 2=электроника, 3=разное",
        json_schema_extra={"example": 2},
    )
    type_name: str = Field(
        ...,
        description="Название типа посылки",
        json_schema_extra={"example": "электроника"},
    )
    total_delivery_cost: float = Field(
        ...,
        description="Общая стоимость доставки",
        json_schema_extra={"example": 1234.56},
    )
