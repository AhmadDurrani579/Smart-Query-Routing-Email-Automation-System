
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.core.roles import UserRole


def get_department_notification_recipients(
    db: Session,
    department_id: int
) -> list[dict]:

    stmt = (
        select(User)
        .where(
            User.department_id == department_id,
            User.role.in_([
                UserRole.EXAM_STAFF.value,
                UserRole.FINANCE_STAFF.value,
                UserRole.IT_STAFF.value,
                UserRole.HOD.value
            ]),
            User.is_active.is_(True),
            User.approval_status == "APPROVED"
        )
        .order_by(User.id)
    )

    users = db.scalars(stmt).all()

    return [
        {
            "user_id": user.id,
            "full_name": user.full_name,
            "role": user.role,
            "email": user.notification_email or user.email
        }
        for user in users
    ]
