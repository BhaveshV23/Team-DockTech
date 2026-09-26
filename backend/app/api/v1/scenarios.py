"""FastAPI route handlers for DockTech V1 scenario operations.

Adheres strictly to ARCHITECTURE.md (Lines 490-510) and DESIGN.md (Lines 560-575).
"""

from datetime import date, datetime
from typing import List
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.domain.constants import (
    Commodity,
    CongestionLevel,
    ContractHorizon,
    FreightUnit,
    ScenarioType,
)
from backend.app.domain.entities import (
    Berth,
    CargoRequest,
    DecisionInputs,
    Route,
    ScenarioResult,
    VesselClass,
)
from backend.app.domain.scenario import ScenarioParameterShock
from backend.app.schemas.common import APIResponse
from backend.app.schemas.scenario import (
    CanonicalScenarioSetResponse,
    RunCanonicalScenariosRequest,
    ScenarioComparisonResponse,
    ScenarioDefaultResponse,
    ScenarioEvaluateRequest,
    ScenarioResultResponse,
    VoyageCostBreakdownSchema,
)
from backend.app.services.scenario_service import ScenarioService

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


def get_scenario_service() -> ScenarioService:
    """Dependency provider for ScenarioService."""
    return ScenarioService()


def _convert_scenario_result_to_schema(res: ScenarioResult) -> ScenarioResultResponse:
    return ScenarioResultResponse(
        scenario_instance_id=res.scenario_instance_id,
        cargo_request_id=res.cargo_request_id,
        scenario_type=res.scenario_type,
        freight_change_pct=res.freight_change_pct,
        fuel_change_pct=res.fuel_change_pct,
        delay_hours=res.delay_hours,
        congestion_level=res.congestion_level,
        estimated_total_cost=res.estimated_total_cost,
        estimated_turnaround_hours=res.estimated_turnaround_hours,
        cost_breakdown=VoyageCostBreakdownSchema(
            sailing_days=res.cost_breakdown.sailing_days,
            required_voyages=res.cost_breakdown.required_voyages,
            origin_handling_hours_total=res.cost_breakdown.origin_handling_hours_total,
            destination_handling_hours_total=res.cost_breakdown.destination_handling_hours_total,
            waiting_hours_total=res.cost_breakdown.waiting_hours_total,
            scenario_delay_total=res.cost_breakdown.scenario_delay_total,
            estimated_turnaround_hours=res.cost_breakdown.estimated_turnaround_hours,
            turnaround_hours_per_voyage=res.cost_breakdown.turnaround_hours_per_voyage,
            port_days_per_voyage=res.cost_breakdown.port_days_per_voyage,
            vessel_days_per_voyage=res.cost_breakdown.vessel_days_per_voyage,
            total_fuel_cost_usd=res.cost_breakdown.total_fuel_cost_usd,
            expected_freight_cost=res.cost_breakdown.expected_freight_cost,
            expected_total_cost=res.cost_breakdown.expected_total_cost,
            effective_cost_per_mt=res.cost_breakdown.effective_cost_per_mt,
        ),
        risk_level=res.risk_level,
        created_at=res.created_at,
    )


@router.get(
    "/defaults",
    response_model=APIResponse[List[ScenarioDefaultResponse]],
    summary="Get canonical scenario default presets",
)
def get_scenario_defaults(
    service: ScenarioService = Depends(get_scenario_service),
) -> APIResponse[List[ScenarioDefaultResponse]]:
    """Retrieves the three frozen canonical scenario presets (BASELINE, ADVERSE, FAVORABLE)."""
    defaults = service.get_scenario_defaults()
    data = [
        ScenarioDefaultResponse(
            scenario_id=d.scenario_id,
            scenario_name=d.scenario_name,
            freight_change_pct=d.freight_change_pct,
            fuel_change_pct=d.fuel_change_pct,
            delay_hours=d.delay_hours,
            port_congestion_level=d.port_congestion_level,
            description=d.description,
        )
        for d in defaults
    ]
    return APIResponse(success=True, data=data)


@router.post(
    "/run-canonical",
    response_model=APIResponse[CanonicalScenarioSetResponse],
    summary="Evaluate all three canonical scenarios",
)
def run_canonical_scenarios(
    payload: RunCanonicalScenariosRequest,
    service: ScenarioService = Depends(get_scenario_service),
) -> APIResponse[CanonicalScenarioSetResponse]:
    """Runs BASELINE, ADVERSE, and FAVORABLE scenarios for a chartering decision."""
    cargo_request = CargoRequest(
        cargo_request_id=payload.cargo_request_id,
        user_id=uuid4(),
        commodity=payload.commodity,
        cargo_volume_mt=payload.cargo_volume_mt,
        origin_port_id="ORIGIN_PORT",
        destination_port_id="DEST_PORT",
        laycan_start_date=date.today(),
        laycan_end_date=date.today(),
        contract_horizon=ContractHorizon.SPOT,
    )
    vessel_class = VesselClass(
        vessel_class_id=payload.vessel_class_id,
        vessel_class_name=payload.vessel_class_id,
        dwt_min_mt=payload.cargo_capacity_mt,
        dwt_max_mt=payload.cargo_capacity_mt * 1.2,
        loa_m=225.0,
        beam_m=32.0,
        draft_m=14.0,
        speed_knots=payload.speed_knots,
        cargo_capacity_mt=payload.cargo_capacity_mt,
        fuel_consumption_mt_day=payload.fuel_consumption_mt_day,
    )
    origin_berth = Berth(
        berth_id="B_ORIG",
        port_id="ORIGIN_PORT",
        berth_name="Berth 1",
        commodity=payload.commodity,
        max_loa_m=250.0,
        max_beam_m=40.0,
        max_draft_m=16.0,
        handling_rate_tpd=payload.origin_berth_handling_rate_tpd,
    )
    destination_berth = Berth(
        berth_id="B_DEST",
        port_id="DEST_PORT",
        berth_name="Berth 2",
        commodity=payload.commodity,
        max_loa_m=250.0,
        max_beam_m=40.0,
        max_draft_m=16.0,
        handling_rate_tpd=payload.destination_berth_handling_rate_tpd,
    )
    route = Route(
        route_id="ROUTE_1",
        origin_port_id="ORIGIN_PORT",
        destination_port_id="DEST_PORT",
        commodity=payload.commodity,
        distance_nm=payload.distance_nm,
        typical_sailing_days=payload.distance_nm / (payload.speed_knots * 24.0),
    )
    decision_inputs = DecisionInputs(
        cargo_request=cargo_request,
        vessel_class=vessel_class,
        origin_berth=origin_berth,
        destination_berth=destination_berth,
        route=route,
        base_freight_rate=payload.base_freight_rate,
        freight_unit=payload.freight_unit,
        base_vlsfo_price_usd_mt=payload.base_vlsfo_price_usd_mt,
        origin_waiting_hours=payload.origin_waiting_hours,
        destination_waiting_hours=payload.destination_waiting_hours,
        cost_reference_date=date.today(),
        forecast_spread_pct=payload.forecast_spread_pct,
    )

    try:
        results = service.run_scenarios(decision_inputs, persist=True)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SCENARIO_EVALUATION_ERROR", "message": str(e)},
        )

    data = CanonicalScenarioSetResponse(
        baseline=_convert_scenario_result_to_schema(results.baseline),
        adverse=_convert_scenario_result_to_schema(results.adverse),
        favorable=_convert_scenario_result_to_schema(results.favorable),
    )
    return APIResponse(success=True, data=data)


@router.post(
    "/evaluate",
    response_model=APIResponse[ScenarioComparisonResponse],
    summary="Evaluate custom scenario adjustments vs baseline",
)
def evaluate_custom_scenario(
    payload: ScenarioEvaluateRequest,
    service: ScenarioService = Depends(get_scenario_service),
) -> APIResponse[ScenarioComparisonResponse]:
    """Applies custom parameter adjustments and returns side-by-side comparison with baseline."""
    cargo_request = CargoRequest(
        cargo_request_id=payload.cargo_request_id,
        user_id=uuid4(),
        commodity=payload.commodity,
        cargo_volume_mt=payload.cargo_volume_mt,
        origin_port_id="ORIGIN_PORT",
        destination_port_id="DEST_PORT",
        laycan_start_date=date.today(),
        laycan_end_date=date.today(),
        contract_horizon=ContractHorizon.SPOT,
    )
    vessel_class = VesselClass(
        vessel_class_id=payload.vessel_class_id,
        vessel_class_name=payload.vessel_class_id,
        dwt_min_mt=payload.cargo_capacity_mt,
        dwt_max_mt=payload.cargo_capacity_mt * 1.2,
        loa_m=225.0,
        beam_m=32.0,
        draft_m=14.0,
        speed_knots=payload.speed_knots,
        cargo_capacity_mt=payload.cargo_capacity_mt,
        fuel_consumption_mt_day=payload.fuel_consumption_mt_day,
    )
    origin_berth = Berth(
        berth_id="B_ORIG",
        port_id="ORIGIN_PORT",
        berth_name="Berth 1",
        commodity=payload.commodity,
        max_loa_m=250.0,
        max_beam_m=40.0,
        max_draft_m=16.0,
        handling_rate_tpd=payload.origin_berth_handling_rate_tpd,
    )
    destination_berth = Berth(
        berth_id="B_DEST",
        port_id="DEST_PORT",
        berth_name="Berth 2",
        commodity=payload.commodity,
        max_loa_m=250.0,
        max_beam_m=40.0,
        max_draft_m=16.0,
        handling_rate_tpd=payload.destination_berth_handling_rate_tpd,
    )
    route = Route(
        route_id="ROUTE_1",
        origin_port_id="ORIGIN_PORT",
        destination_port_id="DEST_PORT",
        commodity=payload.commodity,
        distance_nm=payload.distance_nm,
        typical_sailing_days=payload.distance_nm / (payload.speed_knots * 24.0),
    )
    decision_inputs = DecisionInputs(
        cargo_request=cargo_request,
        vessel_class=vessel_class,
        origin_berth=origin_berth,
        destination_berth=destination_berth,
        route=route,
        base_freight_rate=payload.base_freight_rate,
        freight_unit=payload.freight_unit,
        base_vlsfo_price_usd_mt=payload.base_vlsfo_price_usd_mt,
        origin_waiting_hours=payload.origin_waiting_hours,
        destination_waiting_hours=payload.destination_waiting_hours,
        cost_reference_date=date.today(),
        forecast_spread_pct=payload.forecast_spread_pct,
    )

    shock = ScenarioParameterShock(
        freight_change_pct=payload.freight_change_pct,
        fuel_change_pct=payload.fuel_change_pct,
        delay_hours=payload.delay_hours,
        congestion_level=payload.congestion_level,
    )

    try:
        comparison = service.evaluate_custom_scenario(
            base_inputs=decision_inputs,
            shock=shock,
            scenario_type=ScenarioType.ADVERSE,
            persist=True,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SCENARIO_EVALUATION_ERROR", "message": str(e)},
        )

    data = ScenarioComparisonResponse(
        baseline_result=_convert_scenario_result_to_schema(comparison.baseline_result),
        scenario_result=_convert_scenario_result_to_schema(comparison.scenario_result),
        delta_cost_usd=comparison.delta_cost_usd,
        delta_cost_pct=comparison.delta_cost_pct,
        delta_turnaround_hours=comparison.delta_turnaround_hours,
        delta_effective_cost_per_mt=comparison.delta_effective_cost_per_mt,
        risk_transition=comparison.risk_transition,
    )
    return APIResponse(success=True, data=data)
