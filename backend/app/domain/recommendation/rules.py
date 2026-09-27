"""Deterministic V1 rules shared by the Recommendation Engine."""

from __future__ import annotations

from decimal import Decimal, ROUND_CEILING
from typing import Iterable

from backend.app.domain.constants import RiskLevel, ScenarioType
from .errors import InconsistentRecommendationEvidenceError, MissingRecommendationEvidenceError
from .models import CandidateEvidence, ForecastPointEvidence, RecommendationInput


SCENARIO_TYPES = frozenset(ScenarioType)
RISK_ORDER = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}


def required_voyages(cargo_volume_mt: Decimal, vessel_capacity_mt: Decimal) -> int:
    if cargo_volume_mt <= 0 or vessel_capacity_mt <= 0:
        raise InconsistentRecommendationEvidenceError("Cargo volume and vessel capacity must be positive")
    return int((cargo_volume_mt / vessel_capacity_mt).to_integral_value(rounding=ROUND_CEILING))


def ordered_forecast_points(points: tuple[ForecastPointEvidence, ...]) -> tuple[ForecastPointEvidence, ...]:
    if not points:
        raise MissingRecommendationEvidenceError("Forecast has no points")
    ordered = tuple(sorted(points, key=lambda item: item.forecast_date))
    if len({point.forecast_date for point in ordered}) != len(ordered):
        raise InconsistentRecommendationEvidenceError("Forecast contains duplicate dates")
    for point in ordered:
        if point.lower_value <= 0 or point.central_value <= 0 or point.upper_value <= 0:
            raise InconsistentRecommendationEvidenceError("Forecast values must be positive")
        if not point.lower_value <= point.central_value <= point.upper_value:
            raise InconsistentRecommendationEvidenceError("Forecast bounds do not contain the central value")
    return ordered


def forecast_trend(points: tuple[ForecastPointEvidence, ...]) -> str:
    if len(points) < 2:
        return "INSUFFICIENT"
    first, final = points[0].central_value, points[-1].central_value
    if final > first:
        return "RISING"
    if final < first:
        return "FALLING"
    return "FLAT"


def worst_risk(levels: Iterable[RiskLevel]) -> RiskLevel:
    return max(levels, key=RISK_ORDER.__getitem__)


def validate_candidate(candidate: CandidateEvidence, request: RecommendationInput) -> int:
    if candidate.feasibility_status.value != "FEASIBLE" or not candidate.feasibility_is_feasible:
        raise InconsistentRecommendationEvidenceError(
            f"Candidate {candidate.vessel_class_id} is not marked feasible"
        )
    if candidate.feasibility_cargo_request_id != request.cargo_request_id:
        raise InconsistentRecommendationEvidenceError("Feasibility cargo does not match recommendation cargo")
    if candidate.feasibility_commodity != request.commodity:
        raise InconsistentRecommendationEvidenceError("Feasibility commodity does not match cargo")
    if candidate.feasibility_origin_port_id != request.origin_port_id:
        raise InconsistentRecommendationEvidenceError("Feasibility origin does not match cargo")
    if candidate.feasibility_destination_port_id != request.destination_port_id:
        raise InconsistentRecommendationEvidenceError("Feasibility destination does not match cargo")
    if candidate.feasibility_cargo_volume_mt != request.cargo_volume_mt:
        raise InconsistentRecommendationEvidenceError("Feasibility volume does not match cargo")

    run, cost = candidate.forecast_run, candidate.cost
    if (request.route.origin_port_id, request.route.destination_port_id, request.route.commodity) != (
        request.origin_port_id, request.destination_port_id, request.commodity.value
    ):
        raise InconsistentRecommendationEvidenceError("Resolved route does not match cargo ports and commodity")
    if run.cargo_request_id != request.cargo_request_id or run.route_id != request.route.route_id:
        raise InconsistentRecommendationEvidenceError("Forecast run cargo or route does not match request")
    if run.vessel_class_id != candidate.vessel_class_id:
        raise InconsistentRecommendationEvidenceError("Forecast run vessel does not match candidate")
    if cost.cargo_request_id != request.cargo_request_id or cost.route_id != request.route.route_id:
        raise InconsistentRecommendationEvidenceError("Cost cargo or route does not match request")
    if cost.vessel_class_id != candidate.vessel_class_id or cost.forecast_run_id != run.forecast_run_id:
        raise InconsistentRecommendationEvidenceError("Cost vessel or forecast run does not match candidate")
    if cost.freight_unit != run.freight_unit:
        raise InconsistentRecommendationEvidenceError("Cost freight unit does not match forecast run")
    if not candidate.forecast_run.points:
        raise MissingRecommendationEvidenceError("Candidate forecast has no points")
    if any(point.unit != run.freight_unit for point in candidate.forecast_run.points):
        raise InconsistentRecommendationEvidenceError("Forecast point unit does not match forecast run")
    first_point = min(candidate.forecast_run.points, key=lambda item: item.forecast_date)
    if cost.freight_rate_used != first_point.central_value:
        raise InconsistentRecommendationEvidenceError("Cost did not use the first forecast point central value")
    if cost.expected_freight_cost <= 0 or cost.expected_total_cost <= 0 or cost.effective_cost_per_mt <= 0:
        raise MissingRecommendationEvidenceError("Candidate cost values must be positive")
    if cost.estimated_turnaround_hours <= 0 or cost.sailing_days_per_voyage < 0:
        raise MissingRecommendationEvidenceError("Candidate turnaround or sailing duration is invalid")

    computed_voyages = required_voyages(request.cargo_volume_mt, candidate.cargo_capacity_mt)
    if candidate.feasibility_required_voyages != computed_voyages:
        raise InconsistentRecommendationEvidenceError("Feasibility voyages do not match cargo capacity")
    if cost.required_voyages != computed_voyages:
        raise InconsistentRecommendationEvidenceError("Cost voyages do not match cargo capacity")
    if len(candidate.scenario_risks) != len(SCENARIO_TYPES):
        raise MissingRecommendationEvidenceError("Exactly baseline, adverse, and favorable risk evidence is required")
    scenario_types = [item.scenario_type for item in candidate.scenario_risks]
    if set(scenario_types) != SCENARIO_TYPES or len(set(scenario_types)) != len(scenario_types):
        raise MissingRecommendationEvidenceError("Baseline, adverse, and favorable risks must each appear once")
    for item in candidate.scenario_risks:
        if (item.cargo_request_id, item.route_id, item.vessel_class_id, item.forecast_run_id) != (
            request.cargo_request_id, request.route.route_id, candidate.vessel_class_id, run.forecast_run_id
        ):
            raise InconsistentRecommendationEvidenceError("Scenario risk provenance does not match candidate")
    return computed_voyages
