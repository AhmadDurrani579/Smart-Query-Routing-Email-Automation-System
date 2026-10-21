
from typing import Annotated

import jwt
from jwt import InvalidTokenError

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.roles import UserRole
from app.db.session import get_db
from app.models.user import User
from app.models.revoked_token import RevokedToken
from app.services.logout_service import get_token_hash


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme)
    ],
    db: Annotated[Session, Depends(get_db)]
) -> User:

    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication token",
        headers={"WWW-Authenticate": "Bearer"}
    )

    # 1. Verify token exists and is Bearer
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
    ):
        raise unauthorized

    token = credentials.credentials

    # 2. Decode and validate JWT
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat"]}
        )

        if payload.get("type") != "access":
            raise unauthorized

        user_id = int(payload["sub"])

    except (InvalidTokenError, ValueError, TypeError):
        raise unauthorized

    # 3. Check if token has been revoked
    revoked_token = db.scalar(
        select(RevokedToken).where(
            RevokedToken.token_hash == get_token_hash(token)
        )
    )

    if revoked_token is not None:
        raise unauthorized

    # 4. Retrieve user from database
    user = db.get(User, user_id)

    if user is None:
        raise unauthorized

    # 5. Verify account is approved and active
    if (
        user.approval_status != "APPROVED"
        or not user.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not approved or is inactive"
        )

    return user


def require_admin(
    current_user: Annotated[
        User,
        Depends(get_current_user)
    ]
) -> User:

    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user
