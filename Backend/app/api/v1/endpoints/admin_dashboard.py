
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.user import User
from app.models.query import Query
from app.models.department import Department
from datetime import datetime, timedelta, timezone
from fastapi import Query as QueryParam

router = APIRouter(
    prefix="/admin/dashboard",
    tags=["Admin - Dashboard"]
)


@router.get("/summary")
def get_admin_dashboard_summary(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    days: int = QueryParam(default=30, ge=1, le=365)
):
    total_queries = db.scalar(
        select(func.count(Query.id))
    ) or 0

    open_queries = db.scalar(
        select(func.count(Query.id)).where(
            Query.status.in_([
                "OPEN",
                "IN_PROGRESS",
                "ESCALATED"
            ])
        )
    ) or 0

    resolved_queries = db.scalar(
        select(func.count(Query.id)).where(
            Query.status == "RESOLVED"
        )
    ) or 0

    escalated_queries = db.scalar(
        select(func.count(Query.id)).where(
            Query.escalation_level > 0,
            Query.status != "RESOLVED"
        )
    ) or 0

    registered_users = db.scalar(
        select(func.count(User.id))
    ) or 0

    active_departments = db.scalar(
        select(func.count(Department.id))
    ) or 0

    pending_approvals = db.scalar(
        select(func.count(User.id)).where(
            User.approval_status == "PENDING"
        )
    ) or 0

    avg_resolution_hours = db.scalar(
        select(
            func.avg(
                func.extract(
                    "epoch",
                    Query.resolved_at - Query.created_at
                ) / 3600.0
            )
        ).where(
            Query.status == "RESOLVED",
            Query.resolved_at.is_not(None)
        )
    )


    # Query activity by day (UTC)
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=days - 1)

    start_time = datetime.combine(
        start_date,
        datetime.min.time(),
        tzinfo=timezone.utc
    )

    end_time = datetime.combine(
        today + timedelta(days=1),
        datetime.min.time(),
        tzinfo=timezone.utc
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
            func.count(Query.id)
        )
        .where(
            Query.created_at >= start_time,
            Query.created_at < end_time
        )
        .group_by(created_day)
    ).all()

    resolved_rows = db.execute(
        select(
            resolved_day.label("day"),
            func.count(Query.id)
        )
        .where(
            Query.resolved_at >= start_time,
            Query.resolved_at < end_time
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
            "resolved": resolved_counts.get(day, 0)
        })

    # Query status distribution
    status_rows = db.execute(
        select(
            Query.status,
            func.count(Query.id)
        )
        .group_by(Query.status)
        .order_by(Query.status)
    ).all()

    query_status = [
        {
            "status": query_status,
            "count": count
        }
        for query_status, count in status_rows
    ]


    # Department workload: total queries assigned to each department
    department_rows = db.execute(
        select(
            Department.name,
            func.count(Query.id).label("query_count")
        )
        .outerjoin(
            Query,
            Query.department_id == Department.id
        )
        .group_by(
            Department.id,
            Department.name
        )
        .order_by(
            func.count(Query.id).desc(),
            Department.name
        )
    ).all()

    department_workload = [
        {
            "name": name,
            "value": count
        }
        for name, count in department_rows
    ]



    return {
        "total_queries": total_queries,
        "open_queries": open_queries,
        "resolved_queries": resolved_queries,
        "escalated_queries": escalated_queries,
        "registered_users": registered_users,
        "active_departments": active_departments,
        "pending_approvals": pending_approvals,
        "avg_resolution_hours": round(
            float(avg_resolution_hours or 0), 2
        ),
        "query_activity": query_activity,
        "query_status": query_status,
        "department_workload": department_workload
    }