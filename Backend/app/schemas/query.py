
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

class QueryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(
        min_length=10,
        max_length=5000
    )


class QueryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    subject: str | None
    message: str
    department_id: int | None
    intent: str | None
    priority: str | None
    status: str
    ai_reason: str | None
    needs_manual_review: bool
    assigned_to: int | None
    created_at: datetime

class QueryStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["IN_PROGRESS", "RESOLVED"]
