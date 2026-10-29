
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str | None = None
    email: str
    role: str
    requested_role: str | None = None
    department_id: int | None = None
    department_name: str | None = None
    is_active: bool
    approval_status: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class AdminUserListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    users: list[AdminUserResponse]
