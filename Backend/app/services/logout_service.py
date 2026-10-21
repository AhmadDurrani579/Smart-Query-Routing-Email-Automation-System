
import hashlib
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from app.models.revoked_token import RevokedToken


def get_token_hash(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def revoke_token(
    db: Session,
    token: str,
    expiry_timestamp: int
):
    expiry = datetime.fromtimestamp(
        expiry_timestamp,
        tz=timezone.utc
    )

    statement = (
        insert(RevokedToken)
        .values(
            token_hash=get_token_hash(token),
            expires_at=expiry
        )
        .on_conflict_do_nothing(
            index_elements=["token_hash"]
        )
    )

    try:
        db.execute(statement)
        db.commit()
    except Exception:
        db.rollback()
        raise
