
import logging

from sqlalchemy.orm import Session

from app.repositories.query_repository import (
    create_query
)
from fastapi import HTTPException, status

from app.models.user import User
from app.repositories.query_repository import get_query_by_id
from datetime import datetime, timezone

from app.repositories.query_message_repository import (
    create_reply,
    get_query_messages
)
from app.repositories.email_notification_repository import (
    create_email_notification,
)

from sqlalchemy import select
from app.models.query_escalation import QueryEscalation

logger = logging.getLogger(__name__)

def submit_student_query(
    db: Session,
    student_id: int,
    message: str
):
    # Save the query in Neon.
    # create_query() commits the record.
    query = create_query(
        db=db,
        student_id=student_id,
        message=message
    )

    # Gemini classification is now handled
    # by the background classification worker.
    return query



def get_query_details(
    db: Session,
    query_id: int,
    current_user: User
):
    query = get_query_by_id(
        db=db,
        query_id=query_id
    )

    if query is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found"
        )

    # Admin can view all queries.
    if current_user.role == "ADMIN":
        return query

    # Students can view only their own queries.
    if current_user.role == "STUDENT":
        if query.student_id == current_user.id:
            return query

    # Staff can view queries from their department.
    if current_user.role in {"INSTRUCTOR", "HOD"}:
        if (
            current_user.department_id is not None
            and query.department_id == current_user.department_id
        ):
            return query

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You are not authorised to view this query"
    )


def require_query_handler(
    db: Session,
    query,
    current_user: User
):
    """
    Validate who may reply to or update a query.
    """

    # Students can reply to their own queries,
    # but cannot change their status.
    if current_user.role == "STUDENT":
        if query.student_id == current_user.id:
            return
        raise HTTPException(
            status_code=403,
            detail="You cannot modify another student's query"
        )

    # Admin can manage all queries.
    if current_user.role == "ADMIN":
        return

    # Only department staff may manage regular queries.
    if current_user.role not in {"INSTRUCTOR", "HOD"}:
        raise HTTPException(
            status_code=403,
            detail="You cannot manage this query"
        )

    if (
        current_user.department_id is None
        or current_user.department_id != query.department_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Query belongs to another department"
        )

    # Escalated queries remain under HOD control,
    # even when their status becomes IN_PROGRESS.
    if query.escalation_level > 0:
        escalation = db.scalar(
            select(QueryEscalation)
            .where(
                QueryEscalation.query_id == query.id
            )
            .order_by(
                QueryEscalation.created_at.desc(),
                QueryEscalation.id.desc()
            )
        )

        if current_user.role != "HOD":
            raise HTTPException(
                status_code=403,
                detail="This query is managed by the HOD"
            )

        if (
            escalation is None
            or escalation.escalated_to != current_user.id
        ):
            raise HTTPException(
                status_code=403,
                detail="This escalation is not assigned to you"
            )

    return




def reply_to_query(
    db: Session,
    query_id: int,
    current_user: User,
    message: str
):
    query = get_query_details(
        db=db,
        query_id=query_id,
        current_user=current_user
    )

    # Validate query status
    if query.status in {
        "CLOSED",
        "RESOLVED",
        "PENDING_CLASSIFICATION"
    }:
        raise HTTPException(
            status_code=409,
            detail="Cannot reply to this query in its current status"
        )

    # Validate user permissions, including escalation ownership
    require_query_handler(
        db=db,
        query=query,
        current_user=current_user
    )

    if not message.strip():
        raise HTTPException(
            status_code=422,
            detail="Reply cannot be empty"
        )

    try:
        reply = create_reply(
            db=db,
            query_id=query.id,
            sender_id=current_user.id,
            message=message.strip()
        )

        # Queue an email when authorised staff replies
        if current_user.role in {"INSTRUCTOR", "HOD", "ADMIN"}:
            student = db.get(User, query.student_id)

            if student and student.email:
                create_email_notification(
                    db=db,
                    query_id=query.id,
                    query_message_id=reply.id,
                    recipient_email=student.email,
                    subject=(
                        f"Re: [Query #{query.id}] "
                        f"{query.subject or 'University Support Query'}"
                    )[:255],
                    body=(
                        "Dear Student,\n\n"
                        f"{reply.message}\n\n"
                        "Regards,\n"
                        "University Support Team"
                    )
                )

            if query.responded_at is None:
                query.responded_at = datetime.now(timezone.utc)

            if query.status in {"OPEN", "ESCALATED"}:
                query.status = "IN_PROGRESS"

        query.updated_at = datetime.now(timezone.utc)

        # Save reply, status update and email notification together
        db.commit()
        db.refresh(reply)

        return reply

    except Exception:
        db.rollback()
        raise


def get_query_conversation(
    db: Session,
    query_id: int,
    current_user: User
):
    # Verify ownership or department permissions first
    get_query_details(
        db=db,
        query_id=query_id,
        current_user=current_user
    )

    return get_query_messages(
        db=db,
        query_id=query_id
    )

def update_query_status(
    db: Session,
    query_id: int,
    current_user: User,
    new_status: str
):
    query = get_query_details(
        db=db,
        query_id=query_id,
        current_user=current_user
    )

    # Only authorised staff can change query status
    if current_user.role not in {"INSTRUCTOR", "HOD", "ADMIN"}:
        raise HTTPException(
            status_code=403,
            detail="Only authorised staff can update query status"
        )

    # Check department and escalation ownership
    require_query_handler(
        db=db,
        query=query,
        current_user=current_user
    )

    if new_status == query.status:
        raise HTTPException(
            status_code=409,
            detail="Query already has this status"
        )

    allowed_transitions = {
        "OPEN": {"IN_PROGRESS"},
        "ESCALATED": {"IN_PROGRESS"},
        "IN_PROGRESS": {"RESOLVED"}
    }

    if new_status not in allowed_transitions.get(
        query.status, set()
    ):
        raise HTTPException(
            status_code=409,
            detail="Invalid query status transition"
        )

    now = datetime.now(timezone.utc)

    query.status = new_status
    query.updated_at = now

    if new_status == "RESOLVED":
        query.resolved_at = now

    try:
        db.commit()
        db.refresh(query)
    except Exception:
        db.rollback()
        raise

    return query
