
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def record_audit_event(
    db: Session,
    *,
    actor_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    old_values: dict | None = None,
    new_values: dict | None = None,
) -> AuditLog:
    event = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=old_values,
        new_values=new_values,
    )

    db.add(event)

    # Don't commit here.
    # The caller must commit the action and audit
    # event in the same transaction.
    return event
