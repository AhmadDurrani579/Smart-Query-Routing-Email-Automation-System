
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Audience = Literal[
    "UNIVERSITY",
    "ALL_STUDENTS",
    "HOD",
    "EXAM_STAFF",
    "FINANCE_STAFF",
    "IT_STAFF",
]

AnnouncementStatus = Literal["DRAFT", "PUBLISHED"]


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    audience: Audience
    status: AnnouncementStatus = "DRAFT"


class AnnouncementUpdate(BaseModel):
    title: str | None = Field(
        default=None, min_length=1, max_length=255
    )
    content: str | None = Field(default=None, min_length=1)
    audience: Audience | None = None
    status: AnnouncementStatus | None = None


class AnnouncementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    audience: Audience
    status: AnnouncementStatus
    created_by: int
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
