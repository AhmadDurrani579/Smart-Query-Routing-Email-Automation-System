
import getpass

from sqlalchemy import select, func, text

from app.db.session import SessionLocal
from app.models import User
from app.core.security import hash_password


ADMIN_ACCOUNTS = [
    {
        "name": "Ahmad Yar",
        "email": "ahmadyarimran@yahoo.com"
    },
    {
        "name": "Muhammad",
        "email": "muhammadnoor2623@gmail.com"
    }
]


def create_admins():
    with SessionLocal() as db:
        try:
            # Prevent concurrent bootstrap executions
            db.execute(
                text("SELECT pg_advisory_xact_lock(72643001)")
            )

            admin_count = db.scalar(
                select(func.count(User.id)).where(
                    User.role == "ADMIN"
                )
            )

            if admin_count != 0:
                print(
                    "Admin accounts already exist. "
                    "Bootstrap cancelled."
                )
                return

            for account in ADMIN_ACCOUNTS:
                email = account["email"].lower()

                existing = db.scalar(
                    select(User).where(
                        func.lower(User.email) == email
                    )
                )

                if existing:
                    raise ValueError(
                        f"Account already exists: {email}"
                    )

                password = getpass.getpass(
                    f"Enter password for {email}: "
                )

                if len(password) < 12:
                    raise ValueError(
                        "Password must contain at least 12 characters"
                    )

                admin = User(
                    full_name=account["name"],
                    email=email,
                    hashed_password=hash_password(password),
                    role="ADMIN",
                    requested_role=None,
                    approval_status="APPROVED",
                    is_active=True
                )

                db.add(admin)

            db.commit()
            print("Two Admin accounts created successfully.")

        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    create_admins()
