
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserUpdate


def update_user_profile(
    db: Session,
    user: User,
    data: UserUpdate
) -> User:

    user.full_name = data.full_name
    user.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(user)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update profile"
        )

    return user
