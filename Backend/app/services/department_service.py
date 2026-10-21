
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.department import Department
from app.schemas.department import DepartmentUpdate


from app.repositories.department_repository import (
    get_department_by_code,
    create_department
)
from app.schemas.department import DepartmentCreate


def create_new_department(
    db: Session,
    data: DepartmentCreate
):
    existing = get_department_by_code(db, data.code)

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department code already exists"
        )

    try:
        return create_department(db, data)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department already exists"
        )

def update_department(
    db: Session,
    department_id: int,
    data: DepartmentUpdate
):
    department = db.get(Department, department_id)

    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )

    updates = data.model_dump(exclude_unset=True)

    if "code" in updates:
        if updates["code"] is None:
            raise HTTPException(
                status_code=422,
                detail="Department code cannot be null"
            )

        new_code = updates["code"].upper()

        duplicate = db.scalar(
            select(Department).where(
                func.lower(Department.code) == new_code.lower(),
                Department.id != department_id
            )
        )

        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Department code already exists"
            )

        updates["code"] = new_code

    if updates.get("name") is None and "name" in updates:
        raise HTTPException(
            status_code=422,
            detail="Department name cannot be null"
        )

    for field, value in updates.items():
        setattr(department, field, value)

    try:
        db.commit()
        db.refresh(department)
        return department

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department update conflicts with existing data"
        )


def deactivate_department(
    db: Session,
    department_id: int
):
    department = db.get(Department, department_id)

    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )

    if not department.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department is already inactive"
        )

    department.is_active = False

    try:
        db.commit()
        db.refresh(department)
        return department

    except Exception:
        db.rollback()
        raise
