
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repository import get_pending_users
from app.schemas.admin import (
    PendingUserResponse,
    ApprovalResponse
)
from app.services.admin_service import approve_user
from app.services.admin_service import reject_user

from app.schemas.admin import (
    StaffDepartmentAssignmentRequest,
    StaffDepartmentAssignmentResponse,
)
from app.services.admin_service import assign_staff_department

router = APIRouter(
    prefix="/admin/users",
    tags=["Admin - User Management"]
)


@router.get(
    "/pending",
    response_model=list[PendingUserResponse]
)
def list_pending_users(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)]
):
    return get_pending_users(db)


@router.patch(
    "/{user_id}/approve",
    response_model=ApprovalResponse
)
def approve_pending_user(
    user_id: int,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)]
):
    return approve_user(
        db=db,
        user_id=user_id,
        admin_id=admin.id
    )


@router.patch(
    "/{user_id}/reject",
    response_model=ApprovalResponse
)
def reject_pending_user(
    user_id: int,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)]
):
    return reject_user(
        db=db,
        user_id=user_id,
        admin_id=admin.id
    )


@router.patch(
    "/{user_id}/department",
    response_model=StaffDepartmentAssignmentResponse
)
def assign_department_to_staff(
    user_id: int,
    data: StaffDepartmentAssignmentRequest,
    admin: Annotated[
        User, Depends(require_admin)
    ],
    db: Annotated[
        Session, Depends(get_db)
    ]
):
    return assign_staff_department(
        db=db,
        user_id=user_id,
        department_id=data.department_id
    )
