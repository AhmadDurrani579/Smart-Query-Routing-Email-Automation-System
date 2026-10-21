
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(
        min_length=2,
        max_length=255
    )

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        value = value.strip()

        if len(value) < 2:
            raise ValueError(
                "Full name must contain at least 2 characters"
            )

        return value


class UserProfileResponse(BaseModel):
    id: int
    email: str
    full_name: str | None
    role: str
    approval_status: str | None
    is_active: bool
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
