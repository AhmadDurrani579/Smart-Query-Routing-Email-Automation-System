
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.user import User
from app.models.announcement import Announcement
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementUpdate,
    AnnouncementResponse,
)


router = APIRouter(
    prefix="/admin/announcements",
    tags=["Admin - Announcements"],
)


def get_announcement_or_404(db: Session, announcement_id: int):
    announcement = db.get(Announcement, announcement_id)

    if announcement is None:
        raise HTTPException(
            status_code=404,
            detail="Announcement not found",
        )

    return announcement


@router.post("", response_model=AnnouncementResponse, status_code=201)
def create_announcement(
    data: AnnouncementCreate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    now = datetime.now(timezone.utc)

    announcement = Announcement(
        title=data.title.strip(),
        content=data.content.strip(),
        audience=data.audience,
        status=data.status,
        created_by=admin.id,
        published_at=now if data.status == "PUBLISHED" else None,
    )

    if not announcement.title or not announcement.content:
        raise HTTPException(
            status_code=422,
            detail="Title and content cannot be blank",
        )

    db.add(announcement)

    try:
        db.commit()
        db.refresh(announcement)
    except Exception:
        db.rollback()
        raise

    return announcement


@router.get("", response_model=list[AnnouncementResponse])
def list_admin_announcements(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    return db.scalars(
        select(Announcement)
        .order_by(Announcement.created_at.desc(), Announcement.id.desc())
    ).all()


@router.get("/{announcement_id}", response_model=AnnouncementResponse)
def get_admin_announcement(
    announcement_id: int,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    return get_announcement_or_404(db, announcement_id)


@router.patch("/{announcement_id}", response_model=AnnouncementResponse)
def update_announcement(
    announcement_id: int,
    data: AnnouncementUpdate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    announcement = get_announcement_or_404(db, announcement_id)

    updates = data.model_dump(exclude_unset=True)

    if "title" in updates:
        value = updates["title"]
        if value is None or not value.strip():
            raise HTTPException(status_code=422, detail="Title is required")
        announcement.title = value.strip()

    if "content" in updates:
        value = updates["content"]
        if value is None or not value.strip():
            raise HTTPException(status_code=422, detail="Content is required")
        announcement.content = value.strip()

    if "audience" in updates:
        if updates["audience"] is None:
            raise HTTPException(status_code=422, detail="Audience is required")
        announcement.audience = updates["audience"]

    if "status" in updates:
        new_status = updates["status"]

        if new_status is None:
            raise HTTPException(status_code=422, detail="Status is required")

        if new_status != announcement.status:
            announcement.status = new_status
            announcement.published_at = (
                datetime.now(timezone.utc)
                if new_status == "PUBLISHED"
                else None
            )

    announcement.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(announcement)
    except Exception:
        db.rollback()
        raise

    return announcement


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: int,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    announcement = get_announcement_or_404(db, announcement_id)

    db.delete(announcement)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {"message": "Announcement deleted successfully"}
