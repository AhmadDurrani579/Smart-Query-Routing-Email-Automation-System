
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QueryReplyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(
        min_length=1,
        max_length=5000
    )


class QueryMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    query_id: int
    sender_id: int
    message: str
    created_at: datetime
