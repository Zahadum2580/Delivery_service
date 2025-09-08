from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.core.utils import msk_now
from app.models.base import Base


class Type(Base):
    __tablename__ = "types"

    # условный номер:
    id = Column(Integer, primary_key=True, index=True)
    # название типа:
    name = Column(String(50), unique=True, nullable=False)
    # дата и время создания записи:
    created_at = Column(DateTime(timezone=True), default=msk_now)
    # дата и время последнего обновления записи:
    updated_at = Column(DateTime(timezone=True), default=msk_now, onupdate=msk_now)

    packages = relationship("Package", back_populates="type")
