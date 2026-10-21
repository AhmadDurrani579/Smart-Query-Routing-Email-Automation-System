
from fastapi import HTTPException, status
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from google.auth.exceptions import GoogleAuthError

from app.core.config import settings
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.core.security import (
    create_access_token,
    create_refresh_token,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User


def verify_google_token(token: str) -> dict:
    if not settings.GOOGLE_LOGIN_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Google Login is not configured"
        )

    try:
        payload = id_token.verify_oauth2_token(
            token,
            Request(),
            settings.GOOGLE_LOGIN_CLIENT_ID
        )
    except (ValueError, GoogleAuthError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google ID token"
        ) from exc

    if payload.get("iss") not in (
        "accounts.google.com",
        "https://accounts.google.com",
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid Google token issuer"
        )

    if payload.get("email_verified") is not True:
        raise HTTPException(
            status_code=401,
            detail="Google email is not verified"
        )

    if not payload.get("sub") or not payload.get("email"):
        raise HTTPException(
            status_code=401,
            detail="Incomplete Google identity"
        )

    return {
        "google_id": payload["sub"],
        "email": payload["email"].strip().lower(),
        "full_name": payload.get("name") or "Google User",
    }


def login_with_google(db: Session, token: str):
    google_user = verify_google_token(token)

    google_id = google_user["google_id"]
    email = google_user["email"]

    # Find an already-linked Google account.
    user = db.scalar(
        select(User).where(User.google_id == google_id)
    )

    if user is None:
        # Prevent automatic linking to existing accounts.
        existing_email_user = db.scalar(
            select(User).where(User.email == email)
        )

        if existing_email_user:
            raise HTTPException(
                status_code=409,
                detail=(
                    "An account already exists with this email. "
                    "Sign in using your existing method first."
                ),
            )

        # Register a new Google-only student.
        user = User(
            full_name=google_user["full_name"],
            email=email,
            google_id=google_id,
            hashed_password=None,
            role="STUDENT",
            requested_role="STUDENT",
            approval_status="PENDING",
            is_active=False,
        )

        db.add(user)

        try:
            db.commit()
            db.refresh(user)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Google account registration conflict",
            )

    # Apply the existing approval rules.
    if user.approval_status == "PENDING":
        raise HTTPException(
            status_code=403,
            detail="Your account is pending admin approval",
        )

    if user.approval_status != "APPROVED":
        raise HTTPException(
            status_code=403,
            detail="Your account has not been approved",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive",
        )

    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
    }


def link_google_account(
    db: Session,
    current_user: User,
    id_token: str,
):
    # Verify Google's signed ID token.
    google_user = verify_google_token(id_token)

    google_id = google_user["google_id"]
    google_email = google_user["email"]

    # Require Google's verified email to match
    # the currently authenticated account.
    if google_email != current_user.email.strip().lower():
        raise HTTPException(
            status_code=403,
            detail="Google email does not match your account email",
        )

    # Check whether this Google account is already linked.
    existing_google_user = db.scalar(
        select(User).where(User.google_id == google_id)
    )

    if existing_google_user is not None:
        if existing_google_user.id == current_user.id:
            return {
                "status": "ALREADY_LINKED",
                "message": "Google account is already linked",
            }

        raise HTTPException(
            status_code=409,
            detail="Google account is already linked to another user",
        )

    # Do not silently replace another linked Google identity.
    if current_user.google_id is not None:
        raise HTTPException(
            status_code=409,
            detail="Your account already has a different Google identity linked",
        )

    # Link Google identity to the existing account.
    current_user.google_id = google_id

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Google account could not be linked",
        )

    return {
        "status": "LINKED",
        "message": "Google account linked successfully",
    }
