
import logging
import time

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.query import Query
from app.repositories.query_repository import save_classification
from app.services.gemini_service import classify_student_query
from app.services.n8n_service import send_n8n_event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POLL_INTERVAL = 15

# Retry failed classifications with backoff.
# These delays are kept in memory for this worker process.
RETRY_DELAYS = [60, 120, 300, 600]

retry_after = {}
failure_counts = {}


def find_pending_query_ids():
    with SessionLocal() as db:
        query_ids = db.scalars(
            select(Query.id)
            .where(
                Query.status == "PENDING_CLASSIFICATION",
                Query.needs_manual_review.is_(False)
            )
            .order_by(Query.created_at)
            .limit(10)
        ).all()

        return list(query_ids)



def process_query(query_id: int):
    # 1. Retrieve the pending query
    with SessionLocal() as db:
        query = db.get(Query, query_id)

        if (
            query is None
            or query.status != "PENDING_CLASSIFICATION"
            or query.needs_manual_review
        ):
            return

        message = query.message

    # 2. Call Gemini using a separate database session
    with SessionLocal() as db:
        classification = classify_student_query(
            db=db,
            query=message
        )

    # 3. Save the classification in Neon
    with SessionLocal() as db:
        query = db.get(Query, query_id)

        if (
            query is None
            or query.status != "PENDING_CLASSIFICATION"
            or query.needs_manual_review
        ):
            return

        save_classification(
            db=db,
            query=query,
            classification=classification
        )

    # 4. Notify n8n AFTER the database session closes
    if not classification.needs_manual_review:
        sent = send_n8n_event(
            event="QUERY_CLASSIFIED",
            query_id=query_id,
            department_id=classification.department_id,
            priority=classification.priority
        )

        if not sent:
            logger.warning(
                "Query %s classified, but n8n notification failed",
                query_id
            )

    # 5. Log classification result
    logger.info(
        "Query %s classified. Department=%s Priority=%s",
        query_id,
        classification.department_id,
        classification.priority
    )


def main():
    logger.info("Classification worker started")

    while True:
        try:
            query_ids = find_pending_query_ids()
            current_time = time.monotonic()

            for query_id in query_ids:
                if current_time < retry_after.get(query_id, 0):
                    continue

                try:
                    logger.info(
                        "Classifying query %s",
                        query_id
                    )

                    process_query(query_id)

                    retry_after.pop(query_id, None)
                    failure_counts.pop(query_id, None)

                except Exception:
                    count = failure_counts.get(query_id, 0) + 1
                    failure_counts[query_id] = count

                    delay = RETRY_DELAYS[
                        min(count - 1, len(RETRY_DELAYS) - 1)
                    ]

                    retry_after[query_id] = (
                        time.monotonic() + delay
                    )

                    logger.exception(
                        "Classification failed for query %s. "
                        "Retry in %s seconds",
                        query_id,
                        delay
                    )

        except Exception:
            logger.exception(
                "Classification worker encountered an error"
            )

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
