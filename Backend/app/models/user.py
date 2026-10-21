
from datetime import datetime
from app.core.roles import UserRole
from sqlalchemy import (
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    hashed_password: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False
    )

    role: Mapped[str] = mapped_column(
        String(20),
        default=UserRole.STUDENT.value,
        server_default=UserRole.STUDENT.value,
        nullable=False
    )

    department_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "public.departments.id",
            ondelete="SET NULL"
        ),
        nullable=True
    )
    requested_role: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True
    )

    approval_status: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True
    )

    approved_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "public.users.id",
            ondelete="SET NULL"
        ),
        nullable=True
    )

    google_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True
    )

    notification_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )