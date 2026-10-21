
from typing import Annotated

import jwt

from fastapi import (
    APIRouter,
    Depends,
    Response,
    status,
)
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User

from app.schemas.auth import (
    SignupRequest,
    SignupResponse,
    LoginRequest,
    TokenResponse,
    GoogleLoginRequest,
    GoogleLinkRequest,
)

from app.services.auth_service import (
    signup_user,
    login_user,
)
from app.services.google_auth_service import (
    login_with_google,
    link_google_account,
)
from app.services.logout_service import revoke_token


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

logout_bearer = HTTPBearer()


# 1. Email/password signup
@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Email & Password Signup",
)
def signup(
    data: SignupRequest,
    db: Annotated[Session, Depends(get_db)],
):
    return signup_user(db, data)


# 2. Email/password login
@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Email & Password Login",
)
def login(
    data: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
):
    return login_user(db, data)


# 3. Google login
@router.post(
    "/google",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Google Login",
)
def google_login(
    data: GoogleLoginRequest,
    db: Annotated[Session, Depends(get_db)],
):
    return login_with_google(
        db=db,
        token=data.id_token,
    )


# 4. Link Google account to existing user
@router.post(
    "/google/link",
    summary="Link Google Account",
)
def google_link(
    data: GoogleLinkRequest,
    current_user: Annotated[
        User, Depends(get_current_user)
    ],
    db: Annotated[Session, Depends(get_db)],
):
    return link_google_account(
        db=db,
        current_user=current_user,
        id_token=data.id_token,
    )


# 5. Logout
@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout",
)
def logout(
    current_user: Annotated[
        User, Depends(get_current_user)
    ],
    credentials: Annotated[
        HTTPAuthorizationCredentials,
        Depends(logout_bearer)
    ],
    db: Annotated[Session, Depends(get_db)],
):
    token = credentials.credentials

    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["sub", "exp", "iat"]},
    )

    revoke_token(
        db=db,
        token=token,
        expiry_timestamp=payload["exp"],
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )
