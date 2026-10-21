
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EscalationHistoryResponse(BaseModel):
    id: int
    query_id: int
    escalation_level: int
    escalation_type: str
    escalated_to: int | None
    reason: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EscalatedQueryResponse(BaseModel):
    query_id: int
    subject: str | None
    priority: str | None
    status: str
    department_id: int | None
    escalation_level: int
    escalated_to: int | None
    escalated_at: datetime
    reason: str | None
