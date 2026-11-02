
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
from sqlalchemy.dialects.postgresql import insert
from app.models.email_notification import EmailNotification
from app.models.query_escalation import QueryEscalation

from app.db.session import SessionLocal
from app.models.query import Query
from app.repositories.query_repository import save_classification
from app.services.gemini_service import classify_student_query
from app.services.n8n_service import send_n8n_event
from app.services.notification_service import (
    create_notification,
    notify_department_staff,
)
from app.models.email_notification import EmailNotification

logger = logging.getLogger(__name__)


def submit_student_query(
    db: Session,
    student_id: int,
    message: str
):
    # 1. Save the student query first.
    query = create_query(
        db=db,
        student_id=student_id,
        message=message
    )

    create_notification(
        db=db,
        recipient_id=student_id,
        notification_type="QUERY_SUBMITTED",
        title="Query submitted successfully",
        message=f"Your query #{query.id} has been submitted.",
        entity_type="QUERY",
        entity_id=query.id,
    )

    db.commit()

    query_id = query.id

    # 2. Automatically classify using Gemini.
    try:
        # Use a separate session for the AI classification,
        # following the existing worker design.
        with SessionLocal() as classification_db:
            classification = classify_student_query(
                db=classification_db,
                query=message
            )
        classification_saved = False

        # 3. Save Gemini's classification.
        with SessionLocal() as classification_db:
            saved_query = classification_db.get(Query, query_id)

            if (
                saved_query is not None
                and saved_query.status == "PENDING_CLASSIFICATION"
                and not saved_query.needs_manual_review
            ):
                save_classification(
                    db=classification_db,
                    query=saved_query,
                    classification=classification
                )
                classification_saved = True

        # 4. Notify n8n if classification succeeded.
        if classification_saved and classification.department_id is not None:
            try:
                sent = send_n8n_event(
                    event="QUERY_CLASSIFIED",
                    query_id=query_id,
                    department_id=classification.department_id,
                    priority=classification.priority
                )

                if not sent:
                    logger.warning(
                        "Query %s classified but n8n notification failed",
                        query_id
                    )
            except Exception:
                logger.exception(
                    "n8n notification failed for query %s",
                    query_id
                )

    except Exception:
        logger.exception(
            "Automatic Gemini classification failed for query %s",
            query_id
        )

        # The query remains saved as PENDING_CLASSIFICATION.
        # A worker can retry it later.

    # 5. Reload the updated query from Neon.
    db.expire_all()
    updated_query = db.get(Query, query_id)

    return updated_query



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
    if current_user.role in {"EXAM_STAFF", "FINANCE_STAFF", "IT_STAFF", "HOD"}:
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
    if current_user.role not in {"EXAM_STAFF", "FINANCE_STAFF", "IT_STAFF", "HOD"}:
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




def _deliverable_email(user: User) -> str | None:
    """Exclude reserved example domains used by seeded test accounts."""
    email = (user.notification_email or user.email or "").strip()
    if not email or email.rsplit("@", 1)[-1].lower() in {
        "example.com", "example.org", "example.net"
    } or email.lower().endswith(".example"):
        return None
    return email


def _queue_email_once(db: Session, **values) -> None:
    """Queue without committing; retries won't create duplicate jobs."""
    db.execute(
        insert(EmailNotification)
        .values(**values)
        .on_conflict_do_nothing(constraint="uq_email_query_recipient_type")
    )


def _queue_student_reply_emails(db: Session, query: Query, reply) -> None:
    if query.department_id is None:
        return

    eligible_roles = {"FINANCE_STAFF", "EXAM_STAFF", "IT_STAFF", "HOD"}
    statement = select(User).where(
        User.department_id == query.department_id,
        User.role.in_(eligible_roles),
        User.is_active.is_(True),
        User.approval_status == "APPROVED",
    )

    # For escalated queries, only notify the assigned HOD.
    if query.escalation_level > 0:
        escalation = db.scalar(
            select(QueryEscalation)
            .where(QueryEscalation.query_id == query.id)
            .order_by(QueryEscalation.created_at.desc(), QueryEscalation.id.desc())
        )
        if escalation is None:
            return
        statement = statement.where(
            User.id == escalation.escalated_to,
            User.role == "HOD",
        )

    for recipient in db.scalars(statement).all():
        address = _deliverable_email(recipient)
        if address is None:
            continue

        _queue_email_once(
            db,
            query_id=query.id,
            recipient_user_id=recipient.id,
            # Unique per student message, so later student replies are emailed too.
            notification_type=f"STUDENT_REPLY_{reply.id}",
            recipient_email=address,
            subject=f"Student replied to Query #{query.id}",
            body=(
                f"Hello {recipient.full_name or 'Department Staff'},\n\n"
                f"A student has replied to Query #{query.id}.\n"
                "Please log in to CampusIQ to read the message.\n\n"
                "Regards,\nCampusIQ"
            ),
            status="PENDING",
            attempt_count=0,
        )


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
        if current_user.role in {"EXAM_STAFF", "FINANCE_STAFF", "IT_STAFF", "HOD", "ADMIN"}:
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


        # Create in-app notifications for the new reply.
        if current_user.role == "STUDENT":
            # Student replied: notify their department staff.
            if query.department_id is not None:
                notify_department_staff(
                    db=db,
                    department_id=query.department_id,
                    notification_type="STUDENT_REPLY",
                    title=f"Student replied to Query #{query.id}",
                    message=(
                        f"A student has replied to Query #{query.id}. "
                        "Open the conversation to review their response."
                    ),
                    query_id=query.id,
                    exclude_user_id=current_user.id,
                )
                _queue_student_reply_emails(db, query, reply)

        else:
            # Staff replied: notify the student.
            create_notification(
                db=db,
                recipient_id=query.student_id,
                notification_type="QUERY_REPLY",
                title=f"New reply to Query #{query.id}",
                message=(
                    "Your department has replied to your query. "
                    "Open the conversation to view the response."
                ),
                entity_type="QUERY",
                entity_id=query.id,
            )


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
    if current_user.role not in {"EXAM_STAFF", "FINANCE_STAFF", "IT_STAFF", "HOD", "ADMIN"}:
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


    if new_status == "IN_PROGRESS":

        # 1. Create an in-app notification for the student.
        create_notification(
            db=db,
            recipient_id=query.student_id,
            notification_type="QUERY_IN_PROGRESS",
            title=f"Query #{query.id} is in progress",
            message=(
                f"Your Query #{query.id} is now being reviewed "
                "by the department."
            ),
            entity_type="QUERY",
            entity_id=query.id,
        )

        # 2. Retrieve the student's email address.
        student = db.get(User, query.student_id)

        recipient_email = (
            (student.notification_email or student.email)
            if student else None
        )

        # 3. Queue an email for n8n automatic delivery.
        if recipient_email:
            db.add(
                EmailNotification(
                    query_id=query.id,
                    recipient_user_id=student.id,
                    notification_type="QUERY_IN_PROGRESS",
                    recipient_email=recipient_email,
                    subject=f"Query #{query.id} - Status Update",
                    body=(
                        "Dear Student,\n\n"
                        f"Your Query #{query.id} is now In Progress.\n"
                        "The department is reviewing your request.\n"
                        "You will be notified once your query is resolved.\n\n"
                        "Regards,\n"
                        "CampusIQ Support Team"
                    ),
                    status="PENDING",
                    attempt_count=0,
                )
            )


    if new_status == "RESOLVED":
        query.resolved_at = now

        create_notification(
            db=db,
            recipient_id=query.student_id,
            notification_type="QUERY_RESOLVED",
            title=f"Query #{query.id} resolved",
            message=(
                f"Your Query #{query.id} has been resolved "
                "by the department."
            ),
            entity_type="QUERY",
            entity_id=query.id,
        )

        student = db.get(User, query.student_id)
        if student is not None:
            address = _deliverable_email(student)
            if address is not None:
                _queue_email_once(
                    db,
                    query_id=query.id,
                    recipient_user_id=student.id,
                    notification_type="QUERY_RESOLVED",
                    recipient_email=address,
                    subject=f"Query #{query.id} resolved",
                    body=(
                        "Dear Student,\n\n"
                        f"Your Query #{query.id} has been marked as resolved.\n"
                        "Log in to CampusIQ to review the response.\n\n"
                        "Regards,\nCampusIQ Support Team"
                    ),
                    status="PENDING",
                    attempt_count=0,
                )
    try:
        db.commit()
        db.refresh(query)
    except Exception:
        db.rollback()
        raise

    return query
