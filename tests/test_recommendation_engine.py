from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_CEILING
from uuid import UUID

import pytest

from backend.app.domain.constants import (
    Commodity,
    ContractHorizon,
    ContractStrategy,
    FeasibilityStatus,
    FreightUnit,
    MarketEntryAction,
    RiskLevel,
    ScenarioType,
)
from backend.app.domain.entities import Route
from backend.app.domain.recommendation.engine import RecommendationEngine
from backend.app.domain.recommendation.errors import (
    InconsistentRecommendationEvidenceError,
    MissingRecommendationEvidenceError,
    NoFeasibleVesselError,
)
from backend.app.domain.recommendation.models import (
    CandidateEvidence,
    CostEvidence,
    ForecastPointEvidence,
    ForecastRunEvidence,
    RecommendationConfidence,
    RecommendationInput,
    ScenarioRiskEvidence,
)


def uid(value: int) -> UUID:
    return UUID(int=value)


def point(day: int, central: str, lower: str | None = None, upper: str | None = None):
    central_value = Decimal(central)
    return ForecastPointEvidence(
        forecast_date=date(2026, 1, day),
        lower_value=Decimal(lower) if lower else central_value - Decimal("1"),
        central_value=central_value,
        upper_value=Decimal(upper) if upper else central_value + Decimal("1"),
        unit=FreightUnit.USD_PER_MT,
    )


def candidate(
    vessel_id: str = "PANAMAX",
    *,
    points=None,
    feasible=True,
    risk_levels=None,
    cost_per_mt="10",
    turnaround="48",
    voyages=1,
    capacity="100",
    cargo_volume="90",
):
    points = tuple(points if points is not None else [point(1, "10"), point(2, "12")])
    run_id = uid(sum(vessel_id.encode("utf-8")) + 100)
    run = ForecastRunEvidence(
        forecast_run_id=run_id,
        cargo_request_id=uid(1),
        route_id="R1",
        vessel_class_id=vessel_id,
        freight_unit=FreightUnit.USD_PER_MT,
        points=points,
    )
    voyage_count = int(
        (Decimal(cargo_volume) / Decimal(capacity)).to_integral_value(rounding=ROUND_CEILING)
    )
    cost = CostEvidence(
        cargo_request_id=uid(1),
        route_id="R1",
        vessel_class_id=vessel_id,
        forecast_run_id=run_id,
        freight_unit=FreightUnit.USD_PER_MT,
        freight_rate_used=(
            min(points, key=lambda item: item.forecast_date).central_value
            if points else Decimal("10")
        ),
        expected_freight_cost=Decimal("1000"),
        expected_total_cost=Decimal("1250"),
        effective_cost_per_mt=Decimal(cost_per_mt),
        estimated_turnaround_hours=Decimal(turnaround),
        sailing_days_per_voyage=Decimal("3"),
        required_voyages=int(voyage_count),
    )
    levels = risk_levels or [RiskLevel.LOW, RiskLevel.LOW, RiskLevel.LOW]
    risks = tuple(
        ScenarioRiskEvidence(
            scenario_type=scenario,
            risk_level=level,
            cargo_request_id=uid(1),
            route_id="R1",
            vessel_class_id=vessel_id,
            forecast_run_id=run_id,
        )
        for scenario, level in zip(
            (ScenarioType.BASELINE, ScenarioType.ADVERSE, ScenarioType.FAVORABLE), levels
        )
    )
    return CandidateEvidence(
        vessel_class_id=vessel_id,
        cargo_capacity_mt=Decimal(capacity),
        feasibility_status=(FeasibilityStatus.FEASIBLE if feasible else FeasibilityStatus.INFEASIBLE),
        feasibility_is_feasible=feasible,
        feasibility_cargo_request_id=uid(1),
        feasibility_commodity=Commodity.THERMAL_COAL,
        feasibility_origin_port_id="P1",
        feasibility_destination_port_id="P2",
        feasibility_cargo_volume_mt=Decimal(cargo_volume),
        feasibility_required_voyages=int(voyage_count),
        forecast_run=run,
        cost=cost,
        scenario_risks=risks,
    )


def request(*candidates):
    return RecommendationInput(
        recommendation_id=uid(999),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        cargo_request_id=uid(1),
        commodity=Commodity.THERMAL_COAL,
        cargo_volume_mt=Decimal("90"),
        origin_port_id="P1",
        destination_port_id="P2",
        route=Route(
            route_id="R1",
            origin_port_id="P1",
            destination_port_id="P2",
            commodity=Commodity.THERMAL_COAL.value,
            distance_nm=1000,
            typical_sailing_days=3,
        ),
        laycan_start_date=date(2026, 1, 1),
        laycan_end_date=date(2026, 1, 10),
        contract_horizon=ContractHorizon.SPOT,
        candidates=tuple(candidates),
    )


def test_trend_uses_first_and_final_chronological_points_and_first_point_rate():
    vessel = candidate(points=[point(3, "20"), point(1, "10"), point(2, "13")])
    result = RecommendationEngine.recommend(request(vessel))
    assert result.trend == "RISING"
    assert result.market_entry_action == MarketEntryAction.FIX_NOW
    assert result.forecast_uncertainty[1] == Decimal("10")


@pytest.mark.parametrize(
    ("values", "trend"),
    [(["10", "10"], "FLAT"), (["12", "10"], "FALLING")],
)
def test_flat_and_falling_trend(values, trend):
    result = RecommendationEngine.recommend(
        request(candidate(points=[point(1, values[0]), point(2, values[1])]))
    )
    assert result.trend == trend
    assert result.market_entry_action == (
        MarketEntryAction.WAIT if trend == "FALLING" else MarketEntryAction.FIX_NOW
    )
    if trend == "FLAT":
        assert result.confidence == RecommendationConfidence.MEDIUM


def test_falling_market_fixes_now_when_risk_high_or_operation_exceeds_laycan():
    falling = [point(1, "12"), point(2, "10")]
    high_risk = candidate(points=falling, risk_levels=[RiskLevel.LOW, RiskLevel.HIGH, RiskLevel.LOW])
    assert RecommendationEngine.recommend(request(high_risk)).market_entry_action == MarketEntryAction.FIX_NOW

    long_operation = replace(candidate(points=falling), cost=replace(
        candidate(points=falling).cost,
        estimated_turnaround_hours=Decimal("200"),
    ))
    assert RecommendationEngine.recommend(request(long_operation)).market_entry_action == MarketEntryAction.FIX_NOW


def test_single_forecast_point_means_fix_now_and_low_confidence():
    result = RecommendationEngine.recommend(request(candidate(points=[point(1, "10")])))
    assert result.trend == "INSUFFICIENT"
    assert result.market_entry_action == MarketEntryAction.FIX_NOW
    assert result.confidence == RecommendationConfidence.LOW


def test_risk_is_worst_scenario_and_confidence_requires_scenario_agreement():
    result = RecommendationEngine.recommend(request(candidate(
        risk_levels=[RiskLevel.LOW, RiskLevel.HIGH, RiskLevel.MEDIUM]
    )))
    assert result.risk_level == RiskLevel.HIGH
    assert result.confidence == RecommendationConfidence.MEDIUM


def test_ranking_is_lexicographic_and_uses_vessel_id_as_final_tie_break():
    costly = candidate("A", cost_per_mt="11")
    cheaper = candidate("B", cost_per_mt="10", risk_levels=[RiskLevel.HIGH] * 3)
    safer = candidate("C", cost_per_mt="10", risk_levels=[RiskLevel.LOW] * 3)
    result = RecommendationEngine.recommend(request(costly, cheaper, safer))
    assert result.recommended_vessel_class_id == "C"

    tie_a = candidate("ALPHA")
    tie_b = candidate("BETA")
    assert RecommendationEngine.recommend(request(tie_b, tie_a)).recommended_vessel_class_id == "ALPHA"


def test_ranking_uses_turnaround_then_required_voyages_after_cost_and_risk():
    quick = candidate("QUICK", turnaround="24")
    slow = candidate("SLOW", turnaround="48")
    assert RecommendationEngine.recommend(request(slow, quick)).recommended_vessel_class_id == "QUICK"

    two_voyages = candidate("TWO", capacity="45", cargo_volume="90", turnaround="24")
    three_voyages = candidate("THREE", capacity="30", cargo_volume="90", turnaround="24")
    assert RecommendationEngine.recommend(request(three_voyages, two_voyages)).recommended_vessel_class_id == "TWO"


def test_infeasible_vessels_are_filtered_and_no_feasible_candidate_fails():
    eligible = candidate("GOOD")
    rejected = candidate("BAD", feasible=False)
    assert RecommendationEngine.recommend(request(rejected, eligible)).recommended_vessel_class_id == "GOOD"
    with pytest.raises(NoFeasibleVesselError):
        RecommendationEngine.recommend(request(rejected))


def test_required_voyages_select_multiple_voyage_strategy_without_capacity_rejection():
    multi_voyage = candidate(capacity="30", cargo_volume="90")
    result = RecommendationEngine.recommend(request(multi_voyage))
    assert result.required_voyages == 3
    assert result.contract_strategy == ContractStrategy.SHORT_TERM_MULTIPLE_VOYAGE

    single_voyage = RecommendationEngine.recommend(request(candidate()))
    assert single_voyage.contract_strategy == ContractStrategy.SPOT


@pytest.mark.parametrize("field", ["cargo_request_id", "route_id", "vessel_class_id", "forecast_run_id"])
def test_inconsistent_cost_provenance_is_rejected(field):
    item = candidate()
    bad_cost = replace(item.cost, **{field: uid(7) if field.endswith("id") and field != "route_id" else "OTHER"})
    with pytest.raises(InconsistentRecommendationEvidenceError):
        RecommendationEngine.recommend(request(replace(item, cost=bad_cost)))


def test_inconsistent_forecast_and_scenario_provenance_is_rejected():
    item = candidate()
    bad_run = replace(item.forecast_run, route_id="OTHER")
    with pytest.raises(InconsistentRecommendationEvidenceError):
        RecommendationEngine.recommend(request(replace(item, forecast_run=bad_run)))
    bad_risk = replace(item.scenario_risks[0], forecast_run_id=uid(555))
    with pytest.raises(InconsistentRecommendationEvidenceError):
        RecommendationEngine.recommend(request(replace(item, scenario_risks=(bad_risk, *item.scenario_risks[1:]))))


def test_missing_forecast_cost_or_scenario_evidence_fails():
    item = candidate(points=[])
    with pytest.raises(MissingRecommendationEvidenceError):
        RecommendationEngine.recommend(request(item))

    item = candidate()
    with pytest.raises(MissingRecommendationEvidenceError):
        RecommendationEngine.recommend(request(replace(item, scenario_risks=())))
    with pytest.raises(MissingRecommendationEvidenceError):
        RecommendationEngine.recommend(request(replace(item, scenario_risks=item.scenario_risks[:2])))

    incomplete_cost = replace(item.cost, expected_total_cost=Decimal("0"))
    with pytest.raises(MissingRecommendationEvidenceError):
        RecommendationEngine.recommend(request(replace(item, cost=incomplete_cost)))


def test_infeasible_status_cannot_be_marked_feasible():
    item = replace(candidate(), feasibility_status=FeasibilityStatus.INSUFFICIENT_DATA)
    with pytest.raises(InconsistentRecommendationEvidenceError):
        RecommendationEngine.recommend(request(item))
