
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.query import Query
from app.models.query_escalation import QueryEscalation


def get_escalated_queries(
    db: Session,
    hod_id: int | None = None,
    include_resolved: bool = False
):
    # Find the latest escalation event for each query.
    latest_event_ids = (
        select(
            QueryEscalation.id.label("escalation_id")
        )
        .distinct(QueryEscalation.query_id)
        .order_by(
            QueryEscalation.query_id,
            QueryEscalation.created_at.desc(),
            QueryEscalation.id.desc()
        )
        .subquery()
    )

    stmt = (
        select(Query, QueryEscalation)
        .join(
            QueryEscalation,
            QueryEscalation.query_id == Query.id
        )
        .join(
            latest_event_ids,
            latest_event_ids.c.escalation_id
            == QueryEscalation.id
        )
        .order_by(QueryEscalation.created_at.desc())
    )

    if hod_id is not None:
        stmt = stmt.where(
            QueryEscalation.escalated_to == hod_id
        )

    if not include_resolved:
        stmt = stmt.where(
            Query.status.in_(["ESCALATED", "IN_PROGRESS"])
        )
        
    records = db.execute(stmt).all()

    return [
        {
            "query_id": query.id,
            "subject": query.subject,
            "priority": query.priority,
            "status": query.status,
            "department_id": query.department_id,
            "escalation_level": query.escalation_level,
            "escalated_to": escalation.escalated_to,
            "escalated_at": escalation.created_at,
            "reason": escalation.reason,
        }
        for query, escalation in records
    ]


def get_query_escalation_history(
    db: Session,
    query_id: int
):
    return db.scalars(
        select(QueryEscalation)
        .where(QueryEscalation.query_id == query_id)
        .order_by(
            QueryEscalation.created_at.desc(),
            QueryEscalation.id.desc()
        )
    ).all()
