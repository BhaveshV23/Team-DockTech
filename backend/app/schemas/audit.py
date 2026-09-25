from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class AuditAction(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    EXPORT = "EXPORT"
    GENERATE_FORECAST = "GENERATE_FORECAST"
    GENERATE_RECOMMENDATION = "GENERATE_RECOMMENDATION"


class AuditEntityType(str, Enum):
    CARGO_REQUEST = "CARGO_REQUEST"
    FORECAST_RUN = "FORECAST_RUN"
    SCENARIO = "SCENARIO"
    RECOMMENDATION = "RECOMMENDATION"
    REPORT = "REPORT"
    PORT = "PORT"
    BERTH = "BERTH"
    VESSEL_CLASS = "VESSEL_CLASS"
    ROUTE = "ROUTE"
    REFERENCE_DATA = "REFERENCE_DATA"


class AuditEventCreate(BaseModel):
    user_id: UUID
    action: AuditAction
    entity_type: AuditEntityType
    entity_id: str = Field(..., min_length=1)
    details: Optional[Union[Dict[str, Any], List[Any], str]] = None


class AuditLogResponse(BaseModel):
    audit_log_id: UUID
    user_id: UUID
    action: AuditAction
    entity_type: AuditEntityType
    entity_id: str
    details: Optional[str] = None
    created_at: Union[datetime, str]

    model_config = ConfigDict(from_attributes=True)
