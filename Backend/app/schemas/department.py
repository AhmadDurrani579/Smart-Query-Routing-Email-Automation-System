
from pydantic import BaseModel, ConfigDict
from pydantic import BaseModel, Field, ConfigDict, field_validator

class DepartmentResponse(BaseModel):
    id: int
    name: str
    code: str | None
    description: str | None
    is_active: bool | None
    keywords: str | None

    model_config = ConfigDict(from_attributes=True)


class DepartmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=255)
    code: str = Field(min_length=2, max_length=50)
    description: str | None = None
    keywords: str | None = None

    @field_validator("name", "code")
    @classmethod
    def remove_whitespace(cls, value: str) -> str:
        return value.strip()


class DepartmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=255
    )
    code: str | None = Field(
        default=None,
        min_length=2,
        max_length=50
    )
    description: str | None = None
    keywords: str | None = None

    @field_validator("name", "code")
    @classmethod
    def validate_text(cls, value: str | None):
        if value is not None:
            value = value.strip()
            if len(value) < 2:
                raise ValueError("Must contain at least 2 characters")
        return value
