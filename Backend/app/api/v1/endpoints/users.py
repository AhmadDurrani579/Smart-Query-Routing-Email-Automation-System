
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.models.user import User

from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.user import UserUpdate, UserProfileResponse
from app.services.user_service import update_user_profile

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.get("/me")
def get_my_profile(
    current_user: Annotated[
        User,
        Depends(get_current_user)
    ]
):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "approval_status": current_user.approval_status
    }


@router.patch(
    "/me",
    response_model=UserProfileResponse
)
def update_my_profile(
    data: UserUpdate,
    current_user: Annotated[
        User, Depends(get_current_user)
    ],
    db: Annotated[
        Session, Depends(get_db)
    ]
):
    return update_user_profile(
        db=db,
        user=current_user,
        data=data
    )
