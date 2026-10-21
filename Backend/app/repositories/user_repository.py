
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.user import User
from sqlalchemy import select

from app.models.user import User



def get_user_by_email(
    db: Session,
    email: str
) -> User | None:
    statement = select(User).where(
        func.lower(User.email) == email.lower()
    )

    return db.scalar(statement)


def create_user(
    db: Session,
    *,
    full_name: str,
    email: str,
    hashed_password: str,
    requested_role: str
) -> User:
    user = User(
        full_name=full_name,
        email=email,
        hashed_password=hashed_password,
        role="STUDENT",
        requested_role=requested_role,
        approval_status="PENDING",
        is_active=False
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user

def get_pending_users(db: Session):
    stmt = (
        select(User)
        .where(User.approval_status == "PENDING")
        .order_by(User.created_at.asc(), User.id.asc())
    )

    return db.scalars(stmt).all()


def get_user_by_id(db: Session, user_id: int):
    return db.get(User, user_id)

