
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EscalationRule(Base):
    __tablename__ = "escalation_rules"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True
    )

    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True
    )

    response_time_hours: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
