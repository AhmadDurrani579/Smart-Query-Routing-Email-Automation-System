
from enum import Enum

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    ConfigDict
)


class SignupRole(str, Enum):
    STUDENT = "STUDENT"
    INSTRUCTOR = "INSTRUCTOR"
    HOD = "HOD"


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    requested_role: SignupRole

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Name must contain at least 2 characters")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not any(c.isalpha() for c in value):
            raise ValueError("Password must contain a letter")

        if not any(c.isdigit() for c in value):
            raise ValueError("Password must contain a number")

        return value


class SignupResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str
    requested_role: str
    approval_status: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginUserResponse(BaseModel):
    id: int
    full_name: str | None
    email: EmailStr
    role: str
    department_id: int | None
    approval_status: str | None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: LoginUserResponse



class RefreshTokenRequest(BaseModel):
    refresh_token: str

class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=20)

class GoogleLinkRequest(BaseModel):
    id_token: str = Field(min_length=20)
