
from typing import Annotated

from fastapi import APIRouter, Depends, Query as QueryParam
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.user import User
from app.repositories.query_repository import (
    get_all_queries_for_admin,
)
from app.schemas.admin_query import AdminQueryListResponse
from app.schemas.admin_query import AdminQueryResponse
from app.services.query_service import get_query_details

router = APIRouter(
    prefix="/admin/queries",
    tags=["Admin - Query Management"],
)


@router.get(
    "",
    response_model=AdminQueryListResponse,
)
def list_all_queries(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    page: int = QueryParam(default=1, ge=1),
    page_size: int = QueryParam(default=10, ge=1, le=100),
    status: str | None = None,
    department_id: int | None = QueryParam(default=None, ge=1),
    needs_manual_review: bool | None = None,
):
    return get_all_queries_for_admin(
        db=db,
        page=page,
        page_size=page_size,
        status=status,
        department_id=department_id,
        needs_manual_review=needs_manual_review,
    )

@router.get(
    "/{query_id}",
    response_model=AdminQueryResponse,
    summary="Get Query Details (Admin)"
)
def get_admin_query_details(
    query_id: int,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)]
):
    return get_query_details(
        db=db,
        query_id=query_id,
        current_user=admin
    )