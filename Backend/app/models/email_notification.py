
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    CheckConstraint,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EmailNotification(Base):
    __tablename__ = "email_notifications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'SENDING', 'SENT', 'FAILED')",
            name="chk_email_notification_status",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="chk_email_attempt_count",
        ),
        UniqueConstraint(
            "query_message_id",
            name="uq_email_notification_message",
        ),
        UniqueConstraint(
            "query_id",
            "recipient_user_id",
            "notification_type",
            name="uq_email_query_recipient_type",
        ),
        {"schema": "public"},
    )
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    query_id: Mapped[int] = mapped_column(
        ForeignKey("public.queries.id", ondelete="CASCADE"),
        nullable=False,
    )

    query_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("public.query_messages.id", ondelete="CASCADE"),
        nullable=True,
    )

    recipient_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    subject: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    gmail_message_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    query_escalation_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "public.query_escalations.id",
            ondelete="CASCADE"
        ),
        nullable=True,
        unique=True
    )

    notification_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    recipient_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("public.users.id", ondelete="SET NULL"),
        nullable=True,
    )
