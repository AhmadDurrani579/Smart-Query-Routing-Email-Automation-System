
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.repositories.user_repository import (
    get_user_by_email,
    create_user
)
from app.schemas.auth import SignupRequest

from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token
)

from app.schemas.auth import LoginRequest


def signup_user(db: Session, data: SignupRequest):
    email = str(data.email).strip().lower()

    existing_user = get_user_by_email(db, email)

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    hashed_password = hash_password(data.password)

    try:
        user = create_user(
            db=db,
            full_name=data.full_name,
            email=email,
            hashed_password=hashed_password,
            requested_role=data.requested_role.value
        )

        return user

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Registration could not be completed"
        )


def login_user(db: Session, data: LoginRequest):
    # 1. Find user by email
    email = str(data.email).strip().lower()

    user = get_user_by_email(db, email)

    # 2. Check user and password
    if (
        not user
        or not user.hashed_password
        or not verify_password(
            data.password,
            user.hashed_password
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # 3. Check admin approval
    if user.approval_status == "PENDING":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending admin approval"
        )

    if user.approval_status == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your registration was rejected"
        )

    if user.approval_status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has not been approved"
        )

    # 4. Check account status
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is inactive"
        )

    # 5. Generate JWT tokens
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    # 6. Return tokens
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
