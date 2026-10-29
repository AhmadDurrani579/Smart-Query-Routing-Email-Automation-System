
from sqlalchemy.orm import Session

from app.models.notification import Notification


def create_notification(
    db: Session,
    *,
    recipient_id: int,
    notification_type: str,
    title: str,
    message: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
) -> Notification:

    notification = Notification(
        recipient_id=recipient_id,
        notification_type=notification_type,
        title=title,
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
        is_read=False,
    )

    db.add(notification)
    db.flush()

    # Do not commit here.
    # The caller commits the business action
    # and notification together.

    return notification
