
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.department_repository import (
    get_all_departments
)
from app.schemas.department import DepartmentResponse
from fastapi import HTTPException, status

from app.core.dependencies import require_admin
from app.schemas.department import DepartmentCreate
from app.services.department_service import create_new_department
from app.schemas.department import DepartmentUpdate
from app.services.department_service import update_department

from app.repositories.department_repository import (
    get_department_by_id
)
from app.services.department_service import deactivate_department

router = APIRouter(
    prefix="/departments",
    tags=["Departments"]
)


@router.get(
    "",
    response_model=list[DepartmentResponse]
)
def list_departments(
    current_user: Annotated[
        User, Depends(get_current_user)
    ],
    db: Annotated[
        Session, Depends(get_db)
    ]
):
    return get_all_departments(db)


@router.get(
    "/{department_id}",
    response_model=DepartmentResponse
)
def retrieve_department(
    department_id: int,
    current_user: Annotated[
        User, Depends(get_current_user)
    ],
    db: Annotated[
        Session, Depends(get_db)
    ]
):
    department = get_department_by_id(
        db=db,
        department_id=department_id
    )

    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )

    return department


@router.post(
    "",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED
)
def create_department_endpoint(
    data: DepartmentCreate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)]
):
    return create_new_department(db, data)



@router.patch(
    "/{department_id}",
    response_model=DepartmentResponse
)
def update_department_endpoint(
    department_id: int,
    data: DepartmentUpdate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)]
):
    return update_department(
        db=db,
        department_id=department_id,
        data=data
    )


@router.patch(
    "/{department_id}/deactivate",
    response_model=DepartmentResponse
)
def deactivate_department_endpoint(
    department_id: int,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)]
):
    return deactivate_department(
        db=db,
        department_id=department_id
    )
