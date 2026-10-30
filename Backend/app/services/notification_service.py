
from sqlalchemy.orm import Session

from app.models.notification import Notification
from sqlalchemy import select
from app.models.user import User

STAFF_NOTIFICATION_ROLES = {
    "FINANCE_STAFF",
    "EXAM_STAFF",
    "IT_STAFF",
    "HOD",
}

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

def notify_department_staff(
    db: Session,
    *,
    department_id: int,
    notification_type: str,
    title: str,
    message: str,
    query_id: int,
    exclude_user_id: int | None = None,
) -> int:
    """
    Create an in-app notification for every active,
    approved staff member in a department.

    Does not commit. Caller owns the transaction.
    """

    users = db.scalars(
        select(User).where(
            User.department_id == department_id,
            User.role.in_(STAFF_NOTIFICATION_ROLES),
            User.is_active.is_(True),
            User.approval_status == "APPROVED",
        )
    ).all()

    count = 0

    for user in users:
        if user.id == exclude_user_id:
            continue

        create_notification(
            db=db,
            recipient_id=user.id,
            notification_type=notification_type,
            title=title,
            message=message,
            entity_type="QUERY",
            entity_id=query_id,
        )

        count += 1

    return count
