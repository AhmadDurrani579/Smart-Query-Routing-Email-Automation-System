
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.announcement import Announcement
from app.schemas.announcement import AnnouncementResponse


router = APIRouter(
    prefix="/announcements",
    tags=["Announcements"],
)


@router.get(
    "",
    response_model=list[AnnouncementResponse],
)
def get_my_announcements(
    current_user: Annotated[
        User, Depends(get_current_user)
    ],
    db: Annotated[
        Session, Depends(get_db)
    ],
):
    # User's role is resolved from the authenticated
    # user record, not supplied by the frontend.

    role = current_user.role

    audience_by_role = {
        "STUDENT": "ALL_STUDENTS",
        "HOD": "HOD",
        "EXAM_STAFF": "EXAM_STAFF",
        "FINANCE_STAFF": "FINANCE_STAFF",
        "IT_STAFF": "IT_STAFF",
    }

    allowed_audiences = ["UNIVERSITY"]

    role_audience = audience_by_role.get(role)

    if role_audience:
        allowed_audiences.append(role_audience)

    stmt = (
        select(Announcement)
        .where(
            Announcement.status == "PUBLISHED",
            Announcement.audience.in_(allowed_audiences),
        )
        .order_by(
            Announcement.published_at.desc(),
            Announcement.id.desc(),
        )
    )

    return db.scalars(stmt).all()
