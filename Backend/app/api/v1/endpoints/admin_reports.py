
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.user import User
from app.models.query import Query
from app.models.department import Department


router = APIRouter(
    prefix="/admin/reports",
    tags=["Admin - Analytics & Reports"],
)


def hours_between(start, end):
    if not start or not end:
        return None

    hours = (end - start).total_seconds() / 3600
    return hours if hours >= 0 else None


def average_or_none(values):
    return round(sum(values) / len(values), 2) if values else None


@router.get("")
def get_admin_reports(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    date_from: date | None = QueryParam(default=None),
    date_to: date | None = QueryParam(default=None),
):
    today = datetime.now(timezone.utc).date()

    start_date = date_from or (today - timedelta(days=29))
    end_date = date_to or today

    if start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail="date_from cannot be later than date_to",
        )

    if (end_date - start_date).days > 365:
        raise HTTPException(
            status_code=422,
            detail="Reporting period cannot exceed 365 days",
        )

    start_time = datetime.combine(
        start_date, time.min, tzinfo=timezone.utc
    )
    end_time = datetime.combine(
        end_date + timedelta(days=1),
        time.min,
        tzinfo=timezone.utc,
    )

    # Fetch queries and department names together.
    rows = db.execute(
        select(Query, Department.name)
        .outerjoin(
            Department,
            Query.department_id == Department.id,
        )
        .where(
            Query.created_at >= start_time,
            Query.created_at < end_time,
        )
        .order_by(Query.created_at.desc(), Query.id.desc())
    ).all()

    total = len(rows)

    status_counts = Counter()
    received_by_day = Counter()
    resolved_by_day = Counter()
    department_stats = defaultdict(
        lambda: {
            "total": 0,
            "open": 0,
            "resolved": 0,
            "escalated": 0,
        }
    )

    response_minutes = []
    resolution_hours = []
    resolution_hours_by_day = defaultdict(list)

    routing_counts = {
        "Classified": 0,
        "Pending Classification": 0,
        "Manual Review": 0,
        "Unassigned": 0,
    }

    open_statuses = {
        "OPEN",
        "IN_PROGRESS",
        "ESCALATED",
    }

    for query, department_name in rows:
        status_counts[query.status] += 1

        created_day = query.created_at.date()
        received_by_day[created_day] += 1

        if query.responded_at:
            response_hours = hours_between(
                query.created_at,
                query.responded_at,
            )
            if response_hours is not None:
                response_minutes.append(response_hours * 60)

        if query.status == "RESOLVED" and query.resolved_at:
            duration = hours_between(
                query.created_at,
                query.resolved_at,
            )

            if duration is not None:
                resolution_hours.append(duration)

            resolved_day = query.resolved_at.date()

            if start_date <= resolved_day <= end_date:
                resolved_by_day[resolved_day] += 1

                if duration is not None:
                    resolution_hours_by_day[resolved_day].append(
                        duration
                    )

        dept_name = department_name or "Unassigned"
        stats = department_stats[dept_name]

        stats["total"] += 1

        if query.status in open_statuses:
            stats["open"] += 1

        if query.status == "RESOLVED":
            stats["resolved"] += 1

        if query.escalation_level > 0:
            stats["escalated"] += 1

        # Mutually exclusive AI routing categories
        if query.needs_manual_review:
            routing_counts["Manual Review"] += 1
        elif query.status == "PENDING_CLASSIFICATION":
            routing_counts["Pending Classification"] += 1
        elif query.department_id is not None:
            routing_counts["Classified"] += 1
        else:
            routing_counts["Unassigned"] += 1

    resolved_total = status_counts["RESOLVED"]

    query_volume = []
    resolution_trends = []

    day = start_date

    while day <= end_date:
        day_key = day.isoformat()

        query_volume.append({
            "date": day_key,
            "received": received_by_day[day],
            "resolved": resolved_by_day[day],
        })

        resolution_trends.append({
            "date": day_key,
            "avg_resolution_hours": average_or_none(
                resolution_hours_by_day[day]
            ),
        })

        day += timedelta(days=1)

    department_performance = [
        {
            "department_name": name,
            **stats,
            "resolution_rate": round(
                stats["resolved"] / stats["total"] * 100,
                2,
            ) if stats["total"] else 0,
        }
        for name, stats in department_stats.items()
    ]

    department_performance.sort(
        key=lambda item: (-item["total"], item["department_name"])
    )

    return {
        "period": {
            "date_from": start_date.isoformat(),
            "date_to": end_date.isoformat(),
        },
        "summary": {
            "total_queries": total,
            "open_queries": sum(
                status_counts[s] for s in open_statuses
            ),
            "resolved_queries": resolved_total,
            "resolution_rate": round(
                resolved_total / total * 100, 2
            ) if total else 0,
            "avg_response_minutes": average_or_none(
                response_minutes
            ),
            "avg_resolution_hours": average_or_none(
                resolution_hours
            ),
        },
        "query_volume": query_volume,
        "resolution_distribution": [
            {"status": key, "count": value}
            for key, value in sorted(status_counts.items())
        ],
        "department_performance": department_performance,
        "ai_routing_distribution": [
            {"name": key, "value": value}
            for key, value in routing_counts.items()
        ],
        "resolution_trends": resolution_trends,
    }
