
from app.db.session import SessionLocal
from app.services.email_notification_service import (
    send_pending_notification,
)


def main():
    with SessionLocal() as db:
        result = send_pending_notification(
            db=db,
            notification_id=1
        )

        print("Notification result:", result)


if __name__ == "__main__":
    main()
