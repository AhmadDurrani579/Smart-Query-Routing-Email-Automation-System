
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.query import Query
from app.models.user import User
from app.models.query_escalation import QueryEscalation
from app.models.email_notification import EmailNotification

logger = logging.getLogger(__name__)


def process_overdue_queries(db: Session) -> int:
    now = datetime.now(timezone.utc)

    overdue_ids = db.scalars(
        select(Query.id)
        .where(
            Query.status == "OPEN",
            Query.responded_at.is_(None),
            Query.first_response_due_at.is_not(None),
            Query.first_response_due_at <= now,
            Query.escalation_level == 0,
            Query.department_id.is_not(None)
        )
        .order_by(Query.first_response_due_at)
        .limit(50)
    ).all()

    escalated_count = 0

    for query_id in overdue_ids:
        try:
            # Lock the query inside its own transaction.
            query = db.scalar(
                select(Query)
                .where(Query.id == query_id)
                .with_for_update(skip_locked=True)
                .execution_options(populate_existing=True)
            )

            # Recheck after acquiring the lock.
            if (
                query is None
                or query.status != "OPEN"
                or query.responded_at is not None
                or query.first_response_due_at is None
                or query.first_response_due_at > now
                or query.escalation_level != 0
            ):
                db.rollback()
                continue

            # Locate approved Finance/department HOD.
            hod = db.scalar(
                select(User)
                .where(
                    User.role == "HOD",
                    User.department_id == query.department_id,
                    User.approval_status == "APPROVED",
                    User.is_active.is_(True)
                )
                .order_by(User.id)
                .limit(1)
            )

            # Fallback to an approved Admin.
            recipient = hod or db.scalar(
                select(User)
                .where(
                    User.role == "ADMIN",
                    User.approval_status == "APPROVED",
                    User.is_active.is_(True)
                )
                .order_by(User.id)
                .limit(1)
            )

            if recipient is None:
                logger.warning(
                    "No escalation recipient for query %s",
                    query.id
                )
                db.rollback()
                continue

            reason = (
                "First response deadline exceeded "
                f"for {query.priority} priority query."
            )

            escalation = QueryEscalation(
                query_id=query.id,
                escalation_type="FIRST_RESPONSE",
                escalation_level=1,
                escalated_to=recipient.id,
                reason=reason
            )


            # 1. Save the escalation record
            db.add(escalation)
            db.flush()

            # 2. Update the original query
            query.status = "ESCALATED"
            query.escalation_level = 1
            query.updated_at = datetime.now(timezone.utc)

            # 3. Get the HOD's notification address
            recipient_email = (
                recipient.notification_email
                or recipient.email
            )

            # 4. Build the escalation email
            email_subject = (
                f"[Escalation] Query #{query.id} - "
                f"{query.subject or 'University Support Query'}"
            )[:255]

            email_body = (
                f"Dear {recipient.full_name or 'Staff Member'},\n\n"
                "A university student query has exceeded "
                "its first-response deadline.\n\n"
                f"Query ID: {query.id}\n"
                f"Subject: {query.subject or 'University Support Query'}\n"
                f"Priority: {query.priority}\n"
                f"Reason: {reason}\n\n"
                "Please log in to the Smart Query Routing "
                "System to review the query.\n\n"
                "Regards,\n"
                "University Support Team"
            )

            # 5. Queue the email for the Gmail worker
            notification = EmailNotification(
                query_id=query.id,
                query_message_id=None,
                query_escalation_id=escalation.id,
                recipient_email=recipient_email,
                subject=email_subject,
                body=email_body,
                status="PENDING",
                attempt_count=0
            )

            db.add(notification)

            # 6. Commit all three changes together
            db.commit()

            
            escalated_count += 1

            logger.info(
                "Query %s escalated to user %s",
                query.id,
                recipient.id
            )

        except Exception:
            db.rollback()
            logger.exception(
                "Escalation failed for query %s",
                query_id
            )

    return escalated_count
