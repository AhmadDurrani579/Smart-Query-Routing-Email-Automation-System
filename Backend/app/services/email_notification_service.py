
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.email_notification import EmailNotification
from app.services.gmail_service import send_email
from sqlalchemy.dialects.postgresql import insert

from app.models.query import Query
from app.models.user import User

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3


def send_pending_notification(
    db: Session,
    notification_id: int
):
    now = datetime.now(timezone.utc)

    # Lock the row so two workers cannot
    # claim the same notification simultaneously.
    notification = db.scalar(
        select(EmailNotification)
        .where(EmailNotification.id == notification_id)
        .with_for_update(skip_locked=True)
    )

    if notification is None:
        db.rollback()
        return {"status": "NOT_AVAILABLE"}

    if notification.status == "SENT":
        db.rollback()
        return {"status": "ALREADY_SENT"}

    if notification.status not in {"PENDING", "FAILED"}:
        db.rollback()
        return {"status": "NOT_READY"}

    if notification.attempt_count >= MAX_ATTEMPTS:
        db.rollback()
        return {"status": "MAX_ATTEMPTS_REACHED"}

    if (
        notification.next_retry_at is not None
        and notification.next_retry_at > now
    ):
        db.rollback()
        return {"status": "WAITING_FOR_RETRY"}

    # Claim the notification and commit before
    # making the external Gmail request.
    notification.status = "SENDING"
    notification.attempt_count += 1
    notification.next_retry_at = None

    db.commit()

    try:
        result = send_email(
            to_email=notification.recipient_email,
            subject=notification.subject,
            message=notification.body
        )

        notification.gmail_message_id = result["message_id"]
        notification.status = "SENT"
        notification.sent_at = datetime.now(timezone.utc)
        notification.last_error = None
        notification.next_retry_at = None

        db.commit()

        return {
            "status": "SENT",
            "gmail_message_id": result["message_id"]
        }

    except Exception as error:
        logger.exception(
            "Email send failed for notification %s",
            notification_id
        )

        db.rollback()

        notification = db.get(
            EmailNotification,
            notification_id
        )

        notification.status = "FAILED"
        notification.last_error = (
            f"{type(error).__name__}: "
            "Gmail sending failed; check server logs"
        )

        # Exponential backoff: 2, 4, 8 minutes.
        if notification.attempt_count < MAX_ATTEMPTS:
            delay_minutes = 2 ** notification.attempt_count
            notification.next_retry_at = (
                datetime.now(timezone.utc)
                + timedelta(minutes=delay_minutes)
            )
        else:
            notification.next_retry_at = None

        db.commit()

        return {
            "status": "FAILED",
            "attempt_count": notification.attempt_count
        }


def queue_classification_notification(
    db: Session,
    query_id: int,
    recipient_user_id: int,
):
    # Verify that the query exists and has been classified.
    query = db.get(Query, query_id)

    if query is None:
        raise ValueError("Query not found")

    if query.status == "PENDING_CLASSIFICATION":
        raise ValueError("Query is not classified yet")

    # Verify the intended recipient.
    recipient = db.get(User, recipient_user_id)

    if recipient is None:
        raise ValueError("Recipient not found")

    if (
        not recipient.is_active
        or recipient.approval_status != "APPROVED"
        or recipient.role != "HOD"
        or recipient.department_id != query.department_id
    ):
        raise ValueError("Recipient is not an eligible department HOD")

    recipient_email = recipient.notification_email or recipient.email

    subject = f"New Student Query #{query.id} Assigned"

    body = (
        f"Hello {recipient.full_name or 'Department HOD'},\n\n"
        f"A new student query has been routed to your department.\n\n"
        f"Query ID: {query.id}\n"
        f"Priority: {query.priority}\n\n"
        "Please log in to the Smart Query Routing dashboard "
        "to review it.\n\n"
        "Regards,\n"
        "Smart Query Routing System"
    )

    statement = (
        insert(EmailNotification)
        .values(
            query_id=query.id,
            recipient_user_id=recipient.id,
            notification_type="QUERY_CLASSIFIED",
            recipient_email=recipient_email,
            subject=subject,
            body=body,
            status="PENDING",
            attempt_count=0,
        )
        .on_conflict_do_nothing(
            constraint="uq_email_query_recipient_type"
        )
        .returning(EmailNotification.id)
    )

    notification_id = db.scalar(statement)
    created = notification_id is not None

    if not created:
        existing = db.scalar(
            select(EmailNotification.id).where(
                EmailNotification.query_id == query_id,
                EmailNotification.recipient_user_id == recipient_user_id,
                EmailNotification.notification_type == "QUERY_CLASSIFIED",
            )
        )
        notification_id = existing

    db.commit()

    return {
        "notification_id": notification_id,
        "created": created,
        "status": "QUEUED" if created else "ALREADY_EXISTS",
    }
