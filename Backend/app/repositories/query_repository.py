
from sqlalchemy.orm import Session

from app.models.query import Query
from sqlalchemy import select
from datetime import timedelta
from app.models.escalation_rule import EscalationRule


def create_query(
    db: Session,
    student_id: int,
    message: str
) -> Query:

    query = Query(
        student_id=student_id,
        message=message,
        status="PENDING_CLASSIFICATION",
        needs_manual_review=False
    )

    db.add(query)
    db.commit()
    db.refresh(query)

    return query



def save_classification(
    db: Session,
    query: Query,
    classification
) -> Query:

    query.subject = classification.subject
    query.department_id = classification.department_id
    query.intent = classification.intent
    query.priority = classification.priority
    query.ai_reason = classification.reason

    query.needs_manual_review = (
        classification.needs_manual_review
    )

    if classification.needs_manual_review:
        query.status = "PENDING_CLASSIFICATION"
    else:
        query.status = "OPEN"

    # Calculate escalation deadline
    query.first_response_due_at = None

    if (
        classification.department_id is not None
        and not classification.needs_manual_review
    ):
        rule = db.scalar(
            select(EscalationRule).where(
                EscalationRule.priority == classification.priority,
                EscalationRule.is_active.is_(True)
            )
        )

        if rule:
            query.first_response_due_at = (
                query.created_at
                + timedelta(
                    hours=rule.response_time_hours
                )
            )

    db.commit()
    db.refresh(query)

    return query


def get_department_queries(
    db: Session,
    department_id: int
) -> list[Query]:

    statement = (
        select(Query)
        .where(Query.department_id == department_id)
        .order_by(Query.created_at.desc())
    )

    return list(db.scalars(statement).all())


def get_query_by_id(
    db: Session,
    query_id: int
) -> Query | None:

    return db.get(Query, query_id)

def get_student_queries(
    db: Session,
    student_id: int
) -> list[Query]:

    statement = (
        select(Query)
        .where(Query.student_id == student_id)
        .order_by(
            Query.created_at.desc(),
            Query.id.desc()
        )
    )

    return list(db.scalars(statement).all())