
from sqlalchemy.orm import Session

from app.models.email_notification import EmailNotification


def create_email_notification(
    db: Session,
    query_id: int,
    query_message_id: int,
    recipient_email: str,
    subject: str,
    body: str,
) -> EmailNotification:

    notification = EmailNotification(
        query_id=query_id,
        query_message_id=query_message_id,
        recipient_email=recipient_email,
        subject=subject,
        body=body,
        status="PENDING",
        attempt_count=0,
    )

    db.add(notification)
    db.flush()

    return notification
