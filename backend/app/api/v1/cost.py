from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.core.dependencies import get_current_user_profile
from app.schemas.auth import UserProfileResponse
from backend.app.domain.cost.errors import CostDomainError
from backend.app.repositories.cargo_repository import CargoPersistenceError
from backend.app.repositories.forecast_repository import ForecastPersistenceError
from backend.app.repositories.reference_repository import (
    ReferenceDataUnavailableError,
    SupabaseCostReferenceRepository,
)
from backend.app.services.cost_service import CostApplicationService, CostEngineService


router = APIRouter(
    prefix="/cost",
    tags=["Cost"],
)


cost_reference_repository = SupabaseCostReferenceRepository()
cost_service = CostApplicationService(
    engine=CostEngineService(repository=cost_reference_repository),
)


class CostRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cargo_request_id: UUID
    forecast_run_id: UUID

    freight_rate_override: Decimal | None = Field(
        default=None,
        gt=0,
    )

    scenario_delay_hours: Decimal = Field(
        default=Decimal("0.0"),
        ge=0,
    )

    freight_adjustment_pct: Decimal = Field(
        default=Decimal("0.0"),
    )

    fuel_adjustment_pct: Decimal = Field(
        default=Decimal("0.0"),
    )

    port_costs_usd: Decimal = Field(
        default=Decimal("0.0"),
        ge=0,
    )


class CostResponse(BaseModel):
    required_voyages: int
    sailing_days_per_voyage: float
    origin_handling_hours_total: float
    dest_handling_hours_total: float
    waiting_hours_total: float
    scenario_delay_hours_total: float
    estimated_turnaround_hours: float
    port_days_per_voyage: float
    vessel_days_per_voyage: float

    vlsfo_price_used: float
    total_fuel_consumption_mt: float
    total_fuel_cost_usd: float

    freight_rate_used: float
    freight_unit: str
    expected_freight_cost: float
    port_costs_usd: float
    expected_total_cost: float
    effective_cost_per_mt: float

    cost_reference_date: str
    assumptions: list[str]


@router.post(
    "",
    response_model=CostResponse,
)
def calculate_cost(
    request: CostRequest,
    current_user: UserProfileResponse = Depends(get_current_user_profile),
) -> CostResponse:

    try:
        result = cost_service.calculate_for_forecast(
            cargo_request_id=request.cargo_request_id,
            forecast_run_id=request.forecast_run_id,
            user_profile=current_user,
            freight_rate_override=request.freight_rate_override,
            scenario_delay_hours=request.scenario_delay_hours,
            freight_adjustment_pct=request.freight_adjustment_pct,
            fuel_adjustment_pct=request.fuel_adjustment_pct,
            port_costs_usd=request.port_costs_usd,
        )

        return CostResponse(
            required_voyages=result.required_voyages,
            sailing_days_per_voyage=float(result.sailing_days_per_voyage),
            origin_handling_hours_total=float(
                result.origin_handling_hours_total
            ),
            dest_handling_hours_total=float(
                result.dest_handling_hours_total
            ),
            waiting_hours_total=float(result.waiting_hours_total),
            scenario_delay_hours_total=float(
                result.scenario_delay_hours_total
            ),
            estimated_turnaround_hours=float(
                result.estimated_turnaround_hours
            ),
            port_days_per_voyage=float(result.port_days_per_voyage),
            vessel_days_per_voyage=float(result.vessel_days_per_voyage),
            vlsfo_price_used=float(result.vlsfo_price_used),
            total_fuel_consumption_mt=float(
                result.total_fuel_consumption_mt
            ),
            total_fuel_cost_usd=float(result.total_fuel_cost_usd),
            freight_rate_used=float(result.freight_rate_used),
            freight_unit=result.freight_unit.value,
            expected_freight_cost=float(result.expected_freight_cost),
            port_costs_usd=float(result.port_costs_usd),
            expected_total_cost=float(result.expected_total_cost),
            effective_cost_per_mt=float(result.effective_cost_per_mt),
            cost_reference_date=result.cost_reference_date.isoformat(),
            assumptions=list(result.assumptions),
        )

    except HTTPException as exc:
        if exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "ERROR_COST_DATA_UNAVAILABLE",
                    "message": "Cost data is unavailable",
                },
            ) from exc
        raise
    except CostDomainError as exc:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if exc.code in {"ERROR_CARGO_REQUEST_NOT_FOUND", "ERROR_FORECAST_RUN_NOT_FOUND"}
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        raise HTTPException(
            status_code=status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except (CargoPersistenceError, ForecastPersistenceError, ReferenceDataUnavailableError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "ERROR_COST_DATA_UNAVAILABLE", "message": "Cost data is unavailable"},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "ERROR_INVALID_COST_INPUT", "message": str(exc)},
        ) from exc
