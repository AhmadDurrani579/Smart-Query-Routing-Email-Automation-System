
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.query import Query
from app.models.department import Department


router = APIRouter(
    prefix="/staff/dashboard",
    tags=["Staff - Dashboard"],
)

ALLOWED_ROLES = {
    "FINANCE_STAFF",
    "EXAM_STAFF",
    "IT_STAFF",
}


@router.get("/summary")
def get_staff_dashboard_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    days: int = QueryParam(default=30, ge=1, le=365),
):
    # 1. Only approved, authenticated department staff.
    # get_current_user already checks authentication,
    # account activity, and approval status.
    if current_user.role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Department staff access required",
        )

    department_id = current_user.department_id

    if department_id is None:
        raise HTTPException(
            status_code=403,
            detail="No department assigned to your account",
        )

    department = db.get(Department, department_id)

    if department is None or not department.is_active:
        raise HTTPException(
            status_code=403,
            detail="Assigned department is unavailable",
        )

    # 2. All statistics are scoped to the user's department.
    total_queries = db.scalar(
        select(func.count(Query.id)).where(
            Query.department_id == department_id
        )
    ) or 0

    open_queries = db.scalar(
        select(func.count(Query.id)).where(
            Query.department_id == department_id,
            Query.status.in_([
                "OPEN",
                "PENDING_CLASSIFICATION",
            ]),
        )
    ) or 0

    in_progress_queries = db.scalar(
        select(func.count(Query.id)).where(
            Query.department_id == department_id,
            Query.status == "IN_PROGRESS",
        )
    ) or 0

    resolved_queries = db.scalar(
        select(func.count(Query.id)).where(
            Query.department_id == department_id,
            Query.status == "RESOLVED",
        )
    ) or 0

    escalated_queries = db.scalar(
        select(func.count(Query.id)).where(
            Query.department_id == department_id,
            Query.status == "ESCALATED",
        )
    ) or 0

    # Pending = queries awaiting staff action.
    pending_queries = open_queries

    # 3. UTC date range, identical to Student Dashboard.
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=days - 1)

    start_time = datetime.combine(
        start_date,
        datetime.min.time(),
        tzinfo=timezone.utc,
    )

    end_time = datetime.combine(
        today + timedelta(days=1),
        datetime.min.time(),
        tzinfo=timezone.utc,
    )

    created_day = func.date(
        func.timezone("UTC", Query.created_at)
    )

    resolved_day = func.date(
        func.timezone("UTC", Query.resolved_at)
    )

    created_rows = db.execute(
        select(
            created_day.label("day"),
            func.count(Query.id),
        )
        .where(
            Query.department_id == department_id,
            Query.created_at >= start_time,
            Query.created_at < end_time,
        )
        .group_by(created_day)
    ).all()

    resolved_rows = db.execute(
        select(
            resolved_day.label("day"),
            func.count(Query.id),
        )
        .where(
            Query.department_id == department_id,
            Query.status == "RESOLVED",
            Query.resolved_at >= start_time,
            Query.resolved_at < end_time,
        )
        .group_by(resolved_day)
    ).all()

    created_counts = dict(created_rows)
    resolved_counts = dict(resolved_rows)

    query_activity = []

    for index in range(days):
        day = start_date + timedelta(days=index)

        query_activity.append({
            "date": day.isoformat(),
            "volume": created_counts.get(day, 0),
            "resolved": resolved_counts.get(day, 0),
        })

    # 4. Status distribution.
    status_rows = db.execute(
        select(
            Query.status,
            func.count(Query.id),
        )
        .where(
            Query.department_id == department_id
        )
        .group_by(Query.status)
        .order_by(Query.status)
    ).all()

    query_status = [
        {
            "status": status,
            "count": count,
        }
        for status, count in status_rows
    ]

    # 5. Latest department queries and student information.
    recent_rows = db.execute(
        select(
            Query,
            User.full_name,
        )
        .outerjoin(
            User,
            User.id == Query.student_id,
        )
        .where(
            Query.department_id == department_id
        )
        .order_by(
            Query.created_at.desc(),
            Query.id.desc(),
        )
        .limit(5)
    ).all()

    recent_queries = [
        {
            "id": query.id,
            "student_id": query.student_id,
            "student_name": student_name,
            "subject": query.subject,
            "status": query.status,
            "priority": query.priority,
            "department_id": query.department_id,
            "department_name": department.name,
            "assigned_to": query.assigned_to,
            "created_at": query.created_at,
        }
        for query, student_name in recent_rows
    ]

    # 6. Return one shared response structure.
    return {
        "department_id": department.id,
        "department_name": department.name,
        "total_queries": total_queries,
        "assigned_queries": total_queries,
        "pending_queries": pending_queries,
        "open_queries": open_queries,
        "in_progress_queries": in_progress_queries,
        "resolved_queries": resolved_queries,
        "escalated_queries": escalated_queries,
        "query_activity": query_activity,
        "query_status": query_status,
        "recent_queries": recent_queries,
    }
