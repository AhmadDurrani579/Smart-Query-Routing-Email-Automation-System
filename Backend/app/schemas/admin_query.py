
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AdminQueryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    subject: str | None
    message: str
    department_id: int | None
    intent: str | None
    priority: str | None
    ai_reason: str | None
    needs_manual_review: bool
    assigned_to: int | None
    status: str
    created_at: datetime
    updated_at: datetime
    responded_at: datetime | None
    resolved_at: datetime | None
    first_response_due_at: datetime | None
    escalation_level: int


class AdminQueryListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    queries: list[AdminQueryResponse]
