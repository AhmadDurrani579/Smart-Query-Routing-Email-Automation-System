from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.department import Department
from app.models.user import User
from app.services.report_service import build_query_report

router = APIRouter(prefix="/staff/reports", tags=["Staff - Analytics & Reports"])
ALLOWED_ROLES = {"FINANCE_STAFF", "EXAM_STAFF", "IT_STAFF"}


@router.get("")
def get_staff_reports(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    date_from: date | None = QueryParam(default=None),
    date_to: date | None = QueryParam(default=None),
):
    if current_user.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Department staff access required")
    if current_user.department_id is None:
        raise HTTPException(status_code=403, detail="No department assigned to your account")

    department = db.get(Department, current_user.department_id)
    if department is None or not department.is_active:
        raise HTTPException(status_code=403, detail="Assigned department is unavailable")

    return build_query_report(
        db=db,
        date_from=date_from,
        date_to=date_to,
        department_id=current_user.department_id,
    )
