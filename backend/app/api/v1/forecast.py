from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.services.forecast_service import (
    forecast_application_service,
)


router = APIRouter(
    prefix="/forecast",
    tags=["Forecast"],
)


# ---------------------------------------------------------
# Request
# ---------------------------------------------------------

class ForecastRequest(BaseModel):
    cargo_request_id: UUID
    route_id: str = Field(..., min_length=1)
    vessel_class_id: str = Field(..., min_length=1)
    freight_unit: str = Field(..., min_length=1)
    horizon: int = Field(
        ...,
        description="Forecast horizon: 7, 30, or 90 days",
    )


# ---------------------------------------------------------
# Response
# ---------------------------------------------------------

class ForecastPointResponse(BaseModel):
    forecast_point_id: str | None = None
    forecast_date: str
    central_value: float
    lower_value: float
    upper_value: float
    unit: str


class ForecastRunResponse(BaseModel):
    forecast_run_id: str
    cargo_request_id: str
    route_id: str
    vessel_class_id: str
    freight_unit: str
    model_name: str
    model_version: str
    training_data_end_date: str
    forecast_points: list[ForecastPointResponse]


# ---------------------------------------------------------
# Endpoint
# ---------------------------------------------------------

@router.post(
    "",
    response_model=ForecastRunResponse,
)
def create_forecast(
    request: ForecastRequest,
) -> ForecastRunResponse:

    try:
        result = forecast_application_service.create_forecast(
            cargo_request_id=request.cargo_request_id,
            route_id=request.route_id,
            vessel_class_id=request.vessel_class_id,
            freight_unit=request.freight_unit,
            horizon=request.horizon,
        )

        return ForecastRunResponse(
            forecast_run_id=result["forecast_run"]["forecast_run_id"],
            cargo_request_id=result["forecast_run"]["cargo_request_id"],
            route_id=result["forecast_run"]["route_id"],
            vessel_class_id=result["forecast_run"]["vessel_class_id"],
            freight_unit=result["forecast_run"]["freight_unit"],
            model_name=result["forecast_run"]["model_name"],
            model_version=result["forecast_run"]["model_version"],
            training_data_end_date=result["forecast_run"][
                "training_data_end_date"
            ],
            forecast_points=[
                ForecastPointResponse(
                    forecast_point_id=point.get("forecast_point_id"),
                    forecast_date=point["forecast_date"],
                    central_value=point["central_value"],
                    lower_value=point["lower_value"],
                    upper_value=point["upper_value"],
                    unit=point["unit"],
                )
                for point in result["forecast_points"]
            ],
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc