
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PendingUserResponse(BaseModel):
    id: int
    full_name: str | None
    email: EmailStr
    requested_role: str | None
    approval_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApprovalResponse(BaseModel):
    id: int
    email: EmailStr
    role: str
    approval_status: str
    is_active: bool
    approved_by: int | None

    model_config = ConfigDict(from_attributes=True)


class StaffDepartmentAssignmentRequest(BaseModel):
    department_id: int = Field(gt=0)


class StaffDepartmentAssignmentResponse(BaseModel):
    user_id: int
    full_name: str | None
    role: str
    department_id: int
    department_name: str
    message: str
