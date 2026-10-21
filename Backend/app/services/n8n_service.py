
import logging
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_n8n_event(
    event: str,
    query_id: int,
    department_id: int | None,
    priority: str | None
) -> bool:

    if not settings.N8N_WEBHOOK_URL:
        logger.warning("n8n webhook URL is not configured")
        return False

    try:
        response = httpx.post(
            settings.N8N_WEBHOOK_URL,
            headers={
                "X-Webhook-Secret": settings.N8N_WEBHOOK_SECRET
            },
            json={
                "event": event,
                "query_id": query_id,
                "department_id": department_id,
                "priority": priority
            },
            timeout=10.0
        )

        response.raise_for_status()

        logger.info(
            "n8n event sent successfully: %s for query %s",
            event,
            query_id
        )

        return True

    except httpx.HTTPError:
        logger.exception(
            "Failed to send n8n event for query %s",
            query_id
        )
        return False
