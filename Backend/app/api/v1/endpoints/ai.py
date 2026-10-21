
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)
from sqlalchemy.orm import Session
import logging

from app.core.dependencies import get_current_user
from app.core.roles import UserRole
from app.db.session import get_db
from app.models.user import User
from app.schemas.classification import (
    ClassificationRequest,
    ClassificationResponse
)
from app.services.gemini_service import (
    classify_student_query
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ai",
    tags=["AI Classification"]
)


@router.post(
    "/classify",
    response_model=ClassificationResponse
)
def classify_query(
    data: ClassificationRequest,
    current_user: Annotated[
        User, Depends(get_current_user)
    ],
    db: Annotated[Session, Depends(get_db)]
):
    if current_user.role not in {
        UserRole.STUDENT.value,
        UserRole.ADMIN.value
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    try:
        return classify_student_query(
            db=db,
            query=data.query
        )

    except Exception:
        logger.exception("Gemini classification failed")

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gemini classification unavailable"
        )