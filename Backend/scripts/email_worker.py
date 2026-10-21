
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import or_, select

from app.db.session import SessionLocal
from app.models.email_notification import EmailNotification
from app.services.email_notification_service import (
    send_pending_notification,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 10


def get_ready_notification_ids():
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        statement = (
            select(EmailNotification.id)
            .where(
                EmailNotification.status.in_(
                    ["PENDING", "FAILED"]
                ),
                or_(
                    EmailNotification.next_retry_at.is_(None),
                    EmailNotification.next_retry_at <= now
                ),
                EmailNotification.attempt_count < 3
            )
            .order_by(EmailNotification.created_at)
            .limit(20)
        )

        return list(db.scalars(statement).all())


def main():
    logger.info("Email worker started")

    while True:
        try:
            notification_ids = get_ready_notification_ids()

            for notification_id in notification_ids:
                with SessionLocal() as db:
                    result = send_pending_notification(
                        db=db,
                        notification_id=notification_id
                    )

                logger.info(
                    "Notification %s: %s",
                    notification_id,
                    result["status"]
                )

        except Exception:
            logger.exception("Email worker error")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
