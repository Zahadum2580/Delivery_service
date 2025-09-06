from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.models.base import Base

class Package(Base):
    __tablename__ = "packages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    weight_kg = Column(Numeric(10, 2), nullable=False)
    content_value_usd = Column(Numeric(10, 2), nullable=False)
    type_id = Column(Integer, ForeignKey("types.id"), nullable=False)
    type_name = Column(String(50), nullable=False)
    delivery_cost_rub = Column(Numeric(10, 2), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    type = relationship("Type", back_populates="packages")