from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.core.utils import msk_now
from app.models.base import Base


class Package(Base):
    __tablename__ = "packages"

    # уникальный идентификатор посылки:
    id = Column(Integer, primary_key=True, index=True)
    # уникальный идентификатор сессии:
    session_id = Column(String(36), nullable=False, index=True)
    # наименование посылки:
    name = Column(String(255), nullable=False)
    # вес посылки в килограммах:
    weight_kg = Column(Numeric(10, 2), nullable=False)
    # стоимость содержимого посылки в USD:
    content_value_usd = Column(Numeric(10, 2), nullable=False)
    # тип посылки (внешний ключ на таблицу типов):
    type_id = Column(Integer, ForeignKey("types.id"), nullable=False)
    # наименование типа посылки (для удобства и оптимизации дублируется здесь):
    type_name = Column(String(50), nullable=False)
    # стоимость доставки посылки в RUB:
    delivery_cost_rub = Column(Numeric(10, 2), nullable=True)
    # дата и время создания записи:
    created_at = Column(DateTime(timezone=True), default=msk_now, nullable=False)
    # дата и время последнего обновления записи:
    updated_at = Column(
        DateTime(timezone=True), default=msk_now, onupdate=msk_now, nullable=False
    )

    type = relationship("Type", back_populates="packages")
