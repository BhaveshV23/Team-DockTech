from datetime import datetime
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class UserRole(str, Enum):
    VIEWER = "VIEWER"
    PLANNER = "PLANNER"
    MANAGER = "MANAGER"
    ADMINISTRATOR = "ADMINISTRATOR"


class UserProfileResponse(BaseModel):
    user_id: UUID
    auth_user_id: UUID
    display_name: str
    email: str
    role: str  # 'VIEWER' | 'PLANNER' | 'MANAGER' | 'ADMINISTRATOR'
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
