
import secrets

from fastapi import Header, HTTPException, status

from app.core.config import settings


def verify_internal_api_key(
    x_internal_api_key: str | None = Header(default=None)
):
    expected_key = settings.N8N_INTERNAL_API_KEY

    if (
        not expected_key
        or not x_internal_api_key
        or not secrets.compare_digest(
            x_internal_api_key,
            expected_key
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal API key"
        )
