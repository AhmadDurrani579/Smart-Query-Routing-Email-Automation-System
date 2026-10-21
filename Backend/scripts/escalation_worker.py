
import logging
import time

from app.db.session import SessionLocal
from app.services.escalation_service import (
    process_overdue_queries
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 30


def main():
    logger.info("Escalation worker started")

    while True:
        try:
            with SessionLocal() as db:
                count = process_overdue_queries(db)

            if count:
                logger.info(
                    "Escalated %s overdue queries",
                    count
                )

        except Exception:
            logger.exception("Escalation worker failed")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
