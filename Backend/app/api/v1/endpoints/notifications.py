
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.notification import Notification


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


@router.get("")
def list_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = QueryParam(default=1, ge=1),
    page_size: int = QueryParam(default=20, ge=1, le=100),
    unread_only: bool = False,
):
    conditions = [
        Notification.recipient_id == current_user.id
    ]

    if unread_only:
        conditions.append(Notification.is_read.is_(False))

    total = db.scalar(
        select(func.count(Notification.id)).where(*conditions)
    ) or 0

    records = db.scalars(
        select(Notification)
        .where(*conditions)
        .order_by(
            Notification.created_at.desc(),
            Notification.id.desc()
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "notifications": records,
    }


@router.get("/unread-count")
def get_unread_count(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    count = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.recipient_id == current_user.id,
            Notification.is_read.is_(False),
        )
    ) or 0

    return {"unread_count": count}


@router.patch("/read-all")
def mark_all_notifications_read(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    result = db.execute(
        update(Notification)
        .where(
            Notification.recipient_id == current_user.id,
            Notification.is_read.is_(False),
        )
        .values(
            is_read=True,
            read_at=datetime.now(timezone.utc),
        )
    )

    db.commit()

    return {"updated_count": result.rowcount}


@router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_id == current_user.id,
        )
    )

    if notification is None:
        raise HTTPException(
            status_code=404,
            detail="Notification not found",
        )

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notification)

    return notification
