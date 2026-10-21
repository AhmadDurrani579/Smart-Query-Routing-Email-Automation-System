
from datetime import datetime

from sqlalchemy import Integer, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QueryMessage(Base):
    __tablename__ = "query_messages"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True
    )

    query_id: Mapped[int] = mapped_column(
        ForeignKey("public.queries.id", ondelete="CASCADE"),
        nullable=False
    )

    sender_id: Mapped[int] = mapped_column(
        ForeignKey("public.users.id"),
        nullable=False
    )

    message: Mapped[str] = mapped_column(
        Text, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
