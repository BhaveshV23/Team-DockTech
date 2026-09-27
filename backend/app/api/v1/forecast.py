from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user_profile
from app.schemas.auth import UserProfileResponse
from app.schemas.forecast import ForecastRequest, ForecastRunResponse
from app.repositories.forecast_repository import ForecastPersistenceError
from app.services.forecast_service import forecast_application_service


router = APIRouter(prefix="/forecast", tags=["Forecast"])


@router.post("", response_model=ForecastRunResponse)
def create_forecast(
    request: ForecastRequest,
    current_user: UserProfileResponse = Depends(get_current_user_profile),
) -> ForecastRunResponse:
    try:
        result = forecast_application_service.create_forecast(
            cargo_request_id=request.cargo_request_id,
            route_id=request.route_id,
            vessel_class_id=request.vessel_class_id,
            freight_unit=request.freight_unit.value,
            horizon=request.horizon,
            user_profile=current_user,
        )
        return ForecastRunResponse(
            forecast_run_id=result["forecast_run"]["forecast_run_id"],
            cargo_request_id=result["forecast_run"]["cargo_request_id"],
            route_id=result["forecast_run"]["route_id"],
            vessel_class_id=result["forecast_run"]["vessel_class_id"],
            freight_unit=result["forecast_run"]["freight_unit"],
            model_name=result["forecast_run"]["model_name"],
            model_version=result["forecast_run"]["model_version"],
            training_data_end_date=result["forecast_run"]["training_data_end_date"],
            forecast_points=result["forecast_points"],
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ForecastPersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Forecast results could not be persisted",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Forecast generation failed",
        ) from exc
