
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    recipient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,
    )

    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    entity_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    entity_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
