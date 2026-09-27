from __future__ import annotations

import datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.domain.cost.models import FreightUnit
from backend.app.repositories.reference_repository import reference_repository
from backend.app.services.cost_service import CostEngineService


router = APIRouter(
    prefix="/cost",
    tags=["Cost"],
)


cost_service = CostEngineService(
    repository=reference_repository,
)


class CostRequest(BaseModel):
    cargo_volume_mt: Decimal = Field(..., gt=0)
    origin_port_id: str = Field(..., min_length=1)
    destination_port_id: str = Field(..., min_length=1)
    commodity: str = Field(..., min_length=1)
    vessel_class_id: str = Field(..., min_length=1)
    freight_unit: str = Field(..., min_length=1)
    cost_reference_date: datetime.date

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
) -> CostResponse:

    try:
        result = cost_service.calculate(
            cargo_volume_mt=request.cargo_volume_mt,
            origin_port_id=request.origin_port_id,
            destination_port_id=request.destination_port_id,
            commodity=request.commodity,
            vessel_class_id=request.vessel_class_id,
            freight_unit=FreightUnit.from_str(request.freight_unit),
            cost_reference_date=request.cost_reference_date,
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

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc