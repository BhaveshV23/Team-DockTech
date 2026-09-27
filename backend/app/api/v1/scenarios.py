"""Authenticated API routes for scenario analysis."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.core.dependencies import get_current_user_profile, require_roles
from backend.app.schemas.auth import UserProfileResponse
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
from backend.app.domain.scenario import ScenarioParameterShock
from backend.app.services.scenario_service import (
    ScenarioContextError,
    ScenarioPersistenceError,
    ScenarioService,
    ScenarioStorageUnavailable,
)

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


def get_scenario_service() -> ScenarioService:
    return ScenarioService.production()


def _convert_scenario_result_to_schema(res) -> ScenarioResultResponse:
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


@router.get("/defaults", response_model=APIResponse[List[ScenarioDefaultResponse]])
def get_scenario_defaults(
    service: ScenarioService = Depends(get_scenario_service),
    _user: UserProfileResponse = Depends(get_current_user_profile),
):
    try:
        data = [ScenarioDefaultResponse(
            scenario_id=d.scenario_id,
            scenario_name=d.scenario_name,
            freight_change_pct=d.freight_change_pct,
            fuel_change_pct=d.fuel_change_pct,
            delay_hours=d.delay_hours,
            port_congestion_level=d.port_congestion_level,
            description=d.description,
        ) for d in service.get_scenario_defaults()]
    except ScenarioStorageUnavailable as exc:
        raise _storage_error(exc) from exc
    return APIResponse(success=True, data=data)


@router.post("/run-canonical", response_model=APIResponse[CanonicalScenarioSetResponse])
def run_canonical_scenarios(
    payload: RunCanonicalScenariosRequest,
    service: ScenarioService = Depends(get_scenario_service),
    current_user: UserProfileResponse = Depends(
        require_roles("PLANNER", "MANAGER", "ADMINISTRATOR")
    ),
):
    try:
        results = service.run_canonical_for_cargo(
            cargo_request_id=payload.cargo_request_id,
            forecast_run_id=payload.forecast_run_id,
            user_profile=current_user,
        )
    except Exception as exc:
        raise _scenario_error(exc) from exc
    return APIResponse(success=True, data=CanonicalScenarioSetResponse(
        baseline=_convert_scenario_result_to_schema(results.baseline),
        adverse=_convert_scenario_result_to_schema(results.adverse),
        favorable=_convert_scenario_result_to_schema(results.favorable),
    ))


@router.post("/evaluate", response_model=APIResponse[ScenarioComparisonResponse])
def evaluate_custom_scenario(
    payload: ScenarioEvaluateRequest,
    service: ScenarioService = Depends(get_scenario_service),
    current_user: UserProfileResponse = Depends(
        require_roles("PLANNER", "MANAGER", "ADMINISTRATOR")
    ),
):
    try:
        comparison = service.evaluate_canonical_for_cargo(
            cargo_request_id=payload.cargo_request_id,
            forecast_run_id=payload.forecast_run_id,
            user_profile=current_user,
            shock=ScenarioParameterShock(
                freight_change_pct=payload.freight_change_pct,
                fuel_change_pct=payload.fuel_change_pct,
                delay_hours=payload.delay_hours,
                congestion_level=payload.congestion_level,
            ),
        )
    except Exception as exc:
        raise _scenario_error(exc) from exc
    return APIResponse(success=True, data=ScenarioComparisonResponse(
        baseline_result=_convert_scenario_result_to_schema(comparison.baseline_result),
        scenario_result=_convert_scenario_result_to_schema(comparison.scenario_result),
        delta_cost_usd=comparison.delta_cost_usd,
        delta_cost_pct=comparison.delta_cost_pct,
        delta_turnaround_hours=comparison.delta_turnaround_hours,
        delta_effective_cost_per_mt=comparison.delta_effective_cost_per_mt,
        risk_transition=comparison.risk_transition,
    ))


def _storage_error(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"code": "ERROR_SCENARIO_DATA_UNAVAILABLE", "message": str(exc)},
    )


def _scenario_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (ScenarioPersistenceError, ScenarioStorageUnavailable)):
        return _storage_error(exc)
    if isinstance(exc, ScenarioContextError):
        return HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        )
    if isinstance(exc, HTTPException):
        return exc
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"code": "ERROR_SCENARIO_CONTEXT_INVALID", "message": str(exc)},
    )
