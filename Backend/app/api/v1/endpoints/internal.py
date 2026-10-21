
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.internal_auth import verify_internal_api_key
from app.db.session import get_db

from app.services.notification_recipient_service import (
    get_department_notification_recipients,
)

from app.services.email_notification_service import (
    queue_classification_notification,
)


router = APIRouter(
    prefix="/internal",
    tags=["Internal Automation"],
    dependencies=[Depends(verify_internal_api_key)],
)


# 1. Retrieve department notification recipients
@router.get(
    "/departments/{department_id}/notification-recipients"
)
def department_notification_recipients(
    department_id: int,
    db: Session = Depends(get_db),
):
    recipients = get_department_notification_recipients(
        db=db,
        department_id=department_id,
    )

    return {
        "department_id": department_id,
        "count": len(recipients),
        "recipients": recipients,
    }


# 2. Request body for classification notification
class ClassificationNotificationRequest(BaseModel):
    query_id: int = Field(gt=0)
    recipient_user_id: int = Field(gt=0)


# 3. Queue classification notification
@router.post("/notifications/classification")
def create_classification_notification(
    payload: ClassificationNotificationRequest,
    db: Session = Depends(get_db),
):
    try:
        result = queue_classification_notification(
            db=db,
            query_id=payload.query_id,
            recipient_user_id=payload.recipient_user_id,
        )

        return result

    except ValueError as error:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error
