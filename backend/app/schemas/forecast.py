from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from backend.app.domain.cost.models import FreightUnit


class ForecastRequest(BaseModel):
    cargo_request_id: UUID
    route_id: str = Field(..., min_length=1)
    vessel_class_id: str = Field(..., min_length=1)
    freight_unit: FreightUnit
    horizon: Literal[7, 30, 90]


class ForecastPointResponse(BaseModel):
    forecast_point_id: UUID | None = None
    forecast_date: str
    central_value: float
    lower_value: float
    upper_value: float
    unit: str


class ForecastRunResponse(BaseModel):
    forecast_run_id: UUID
    cargo_request_id: UUID
    route_id: str
    vessel_class_id: str
    freight_unit: str
    model_name: str
    model_version: str
    training_data_end_date: str
    forecast_points: list[ForecastPointResponse]
