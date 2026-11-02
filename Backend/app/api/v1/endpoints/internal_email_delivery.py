
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.email_notification import EmailNotification
from app.services.email_notification_service import send_pending_notification
from app.core.internal_auth import verify_internal_api_key
# Replace with the SAME internal-key dependency used
# by your existing internal notification endpoints.

router = APIRouter(
    prefix="/internal/emails",
    tags=["Internal Email Delivery"],
    dependencies=[Depends(verify_internal_api_key)],
)


@router.post("/process-pending")
def process_pending_emails(
    limit: int = 10,
    db: Session = Depends(get_db),
):
    if not 1 <= limit <= 50:
        raise HTTPException(
            status_code=422,
            detail="limit must be between 1 and 50",
        )

    # Find pending emails ready to send.
    # Failed emails are included only when retry time arrives.
    from datetime import datetime, timezone
    from sqlalchemy import or_, and_

    now = datetime.now(timezone.utc)

    statement = (
        select(EmailNotification.id)
        .where(
            EmailNotification.attempt_count < 3,
            EmailNotification.status.in_(["PENDING", "FAILED"]),
            or_(
                EmailNotification.next_retry_at.is_(None),
                EmailNotification.next_retry_at <= now,
            ),
        )
        .order_by(EmailNotification.id)
        .limit(limit)
    )

    notification_ids = db.scalars(statement).all()

    results = []

    for notification_id in notification_ids:
        try:
            result = send_pending_notification(
                db=db,
                notification_id=notification_id,
            )

            results.append({
                "notification_id": notification_id,
                **result,
            })
        except Exception:
            db.rollback()
            results.append({
                "notification_id": notification_id,
                "status": "ERROR",
            })

    return {
        "processed": len(results),
        "results": results,
    }
