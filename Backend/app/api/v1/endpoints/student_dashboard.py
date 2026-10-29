
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.roles import UserRole
from app.db.session import get_db
from app.models.user import User
from app.models.query import Query
from app.models.department import Department


router = APIRouter(
    prefix="/student/dashboard",
    tags=["Student - Dashboard"],
)


@router.get("/summary")
def get_student_dashboard_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    days: int = QueryParam(default=30, ge=1, le=365),
):
    if current_user.role != UserRole.STUDENT.value:
        raise HTTPException(
            status_code=403,
            detail="Student access required",
        )

    student_id = current_user.id

    # Total number of queries submitted by this student.
    submitted_queries = db.scalar(
        select(func.count(Query.id)).where(
            Query.student_id == student_id
        )
    ) or 0

    # Open includes waiting, escalated, and newly submitted queries.
    open_queries = db.scalar(
        select(func.count(Query.id)).where(
            Query.student_id == student_id,
            Query.status.in_([
                "OPEN",
                "ESCALATED",
                "PENDING_CLASSIFICATION",
            ]),
        )
    ) or 0

    in_progress_queries = db.scalar(
        select(func.count(Query.id)).where(
            Query.student_id == student_id,
            Query.status == "IN_PROGRESS",
        )
    ) or 0

    resolved_queries = db.scalar(
        select(func.count(Query.id)).where(
            Query.student_id == student_id,
            Query.status == "RESOLVED",
        )
    ) or 0

    # Date range, using UTC.
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

    # Daily submissions for this student.
    created_rows = db.execute(
        select(
            created_day.label("day"),
            func.count(Query.id),
        )
        .where(
            Query.student_id == student_id,
            Query.created_at >= start_time,
            Query.created_at < end_time,
        )
        .group_by(created_day)
    ).all()

    # Daily resolutions for this student.
    resolved_rows = db.execute(
        select(
            resolved_day.label("day"),
            func.count(Query.id),
        )
        .where(
            Query.student_id == student_id,
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

    # Status distribution across all of the student's queries.
    status_rows = db.execute(
        select(
            Query.status,
            func.count(Query.id),
        )
        .where(Query.student_id == student_id)
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

    # Five most recent queries, with department names.
    recent_rows = db.execute(
        select(Query, Department.name)
        .outerjoin(
            Department,
            Query.department_id == Department.id,
        )
        .where(Query.student_id == student_id)
        .order_by(
            Query.created_at.desc(),
            Query.id.desc(),
        )
        .limit(5)
    ).all()

    recent_queries = [
        {
            "id": query.id,
            "subject": query.subject,
            "status": query.status,
            "priority": query.priority,
            "department_id": query.department_id,
            "department_name": department_name,
            "created_at": query.created_at,
        }
        for query, department_name in recent_rows
    ]

    return {
        "submitted_queries": submitted_queries,
        "open_queries": open_queries,
        "in_progress_queries": in_progress_queries,
        "resolved_queries": resolved_queries,
        "query_activity": query_activity,
        "query_status": query_status,
        "recent_queries": recent_queries,
    }
