
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.roles import UserRole
from app.models.user import User

from datetime import datetime, timezone
from app.models.department import Department

ALLOWED_REQUESTED_ROLES = {
    UserRole.STUDENT.value,
    UserRole.HOD.value,
    UserRole.EXAM_STAFF.value,
    UserRole.FINANCE_STAFF.value,
    UserRole.IT_STAFF.value,
}


def approve_user(
    db: Session,
    user_id: int,
    admin_id: int
) -> User:

    # Lock the user row during approval.
    stmt = (
        select(User)
        .where(User.id == user_id)
        .with_for_update()
    )

    user = db.scalar(stmt)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.approval_status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is not pending approval"
        )

    if user.requested_role not in ALLOWED_REQUESTED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid requested role"
        )

    # Grant the requested role only after Admin approval.
    user.role = user.requested_role
    user.approval_status = "APPROVED"
    user.is_active = True
    user.approved_by = admin_id

    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise

    return user


def reject_user(
    db: Session,
    user_id: int,
    admin_id: int
) -> User:

    stmt = (
        select(User)
        .where(User.id == user_id)
        .with_for_update()
    )

    user = db.scalar(stmt)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.approval_status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending users can be rejected"
        )

    user.approval_status = "REJECTED"
    user.is_active = False
    user.approved_by = admin_id

    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise

    return user


def assign_staff_department(
    db: Session,
    user_id: int,
    department_id: int
):
    # 1. Find the staff member
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # 2. Check the user's role
    if user.role not in {"EXAM_STAFF", "FINANCE_STAFF", "IT_STAFF", "HOD"}:
        raise HTTPException(
            status_code=403,
            detail="Only Instructors and HODs can be assigned departments"
        )

    # 3. Check account approval and activation
    if (
        not user.is_active
        or user.approval_status != "APPROVED"
    ):
        raise HTTPException(
            status_code=409,
            detail="Staff account must be active and approved"
        )

    # 4. Verify the department
    department = db.get(Department, department_id)

    if department is None:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    if not department.is_active:
        raise HTTPException(
            status_code=409,
            detail="Cannot assign an inactive department"
        )

    # 5. Avoid unnecessary updates
    if user.department_id == department_id:
        raise HTTPException(
            status_code=409,
            detail="Staff member is already assigned to this department"
        )

    # 6. Assign department
    user.department_id = department.id
    user.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise

    return {
        "user_id": user.id,
        "full_name": user.full_name,
        "role": user.role,
        "department_id": department.id,
        "department_name": department.name,
        "message": "Staff department assigned successfully"
    }
