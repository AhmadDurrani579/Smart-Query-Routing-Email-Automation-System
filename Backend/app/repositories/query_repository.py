
from sqlalchemy.orm import Session

from app.models.query import Query
from sqlalchemy import select
from datetime import timedelta
from app.models.escalation_rule import EscalationRule
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.query import Query



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

    
def get_all_queries_for_admin(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 10,
    status: str | None = None,
    department_id: int | None = None,
    needs_manual_review: bool | None = None,
):
    filters = []

    if status is not None:
        filters.append(Query.status == status)

    if department_id is not None:
        filters.append(Query.department_id == department_id)

    if needs_manual_review is not None:
        filters.append(
            Query.needs_manual_review == needs_manual_review
        )

    total = db.scalar(
        select(func.count(Query.id)).where(*filters)
    ) or 0

    stmt = (
        select(Query)
        .where(*filters)
        .order_by(Query.created_at.desc(), Query.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    queries = db.scalars(stmt).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "queries": queries,
    }
