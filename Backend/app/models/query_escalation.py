
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QueryEscalation(Base):
    __tablename__ = "query_escalations"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True
    )

    query_id: Mapped[int] = mapped_column(
        ForeignKey("public.queries.id", ondelete="CASCADE"),
        nullable=False
    )

    escalation_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )

    escalation_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        default="FIRST_RESPONSE"
    )

    escalated_to: Mapped[int | None] = mapped_column(
        ForeignKey("public.users.id", ondelete="SET NULL"),
        nullable=True
    )

    reason: Mapped[str] = mapped_column(
        Text, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
