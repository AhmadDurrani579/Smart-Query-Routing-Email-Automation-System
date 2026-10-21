
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ClassificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        min_length=10,
        max_length=5000
    )


class GeminiClassification(BaseModel):
    subject: str = Field(
        min_length=5,
        max_length=150,
        description="Clear and professional subject for the query"
    )
    department_id: int | None
    intent: str
    priority: Literal["LOW", "MEDIUM", "HIGH"]
    reason: str


class ClassificationResponse(GeminiClassification):
    department_name: str | None
    needs_manual_review: bool
