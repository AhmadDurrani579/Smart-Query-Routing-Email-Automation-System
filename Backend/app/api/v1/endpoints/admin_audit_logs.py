
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.user import User
from app.models.audit_log import AuditLog


router = APIRouter(
    prefix="/admin/audit-logs",
    tags=["Admin - Audit Logs"],
)


@router.get("")
def get_audit_logs(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    action: str | None = None,
    actor_id: int | None = None,
    entity_type: str | None = None,
):
    conditions = []

    if action:
        conditions.append(AuditLog.action == action)

    if actor_id is not None:
        conditions.append(AuditLog.actor_id == actor_id)

    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)

    count_stmt = select(func.count(AuditLog.id))
    stmt = select(AuditLog)

    for condition in conditions:
        count_stmt = count_stmt.where(condition)
        stmt = stmt.where(condition)

    total = db.scalar(count_stmt) or 0

    stmt = (
        stmt.order_by(
            AuditLog.created_at.desc(),
            AuditLog.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    logs = db.scalars(stmt).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "logs": [
            {
                "id": log.id,
                "actor_id": log.actor_id,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "created_at": log.created_at,
            }
            for log in logs
        ],
    }
