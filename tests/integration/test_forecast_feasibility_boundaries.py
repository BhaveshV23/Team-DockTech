"""Integration tests for forecast and feasibility boundaries with scenario analysis."""

import pytest
from backend.app.domain.constants import Commodity, FreightUnit, RiskLevel, ScenarioType
from backend.app.domain.entities import Berth, CargoRequest, DecisionInputs, Route, VesselClass
from backend.app.domain.risk import RiskEvaluator
from backend.app.services.scenario_service import ScenarioService


def test_forecast_spread_influences_scenario_risk(sample_decision_inputs: DecisionInputs):
    """Verify widening forecast quantile spread increases scenario risk rating."""
    from dataclasses import replace
    # Low spread (5%)
    low_spread_inputs = replace(sample_decision_inputs, forecast_spread_pct=5.0)
    service = ScenarioService()
    results_low = service.run_scenarios(low_spread_inputs, persist=False)
    assert results_low.favorable.risk_level == RiskLevel.LOW

    # High uncertainty spread (30%)
    high_spread_inputs = replace(sample_decision_inputs, forecast_spread_pct=30.0)
    results_high = service.run_scenarios(high_spread_inputs, persist=False)
    # High forecast uncertainty pushes favorable and baseline to HIGH risk
    assert results_high.baseline.risk_level == RiskLevel.HIGH


def test_feasible_vessel_only_enters_scenario_analysis(
    sample_vessels, sample_berths, sample_route, sample_cargo_request
):
    """Verify that feasible vessel specs execute scenario analysis cleanly."""
    # Panamax is physically compatible with Newcastle and Paradip berths
    panamax = sample_vessels["panamax"]
    orig_berth = sample_berths["origin"]
    dest_berth = sample_berths["destination"]

    # Verify physical feasibility conditions
    assert panamax.loa_m <= orig_berth.max_loa_m
    assert panamax.beam_m <= orig_berth.max_beam_m
    assert panamax.draft_m <= orig_berth.max_draft_m
    assert panamax.loa_m <= dest_berth.max_loa_m
    assert panamax.beam_m <= dest_berth.max_beam_m
    assert panamax.draft_m <= dest_berth.max_draft_m

    inputs = DecisionInputs(
        cargo_request=sample_cargo_request,
        vessel_class=panamax,
        origin_berth=orig_berth,
        destination_berth=dest_berth,
        route=sample_route,
        base_freight_rate=19.0,
        freight_unit=FreightUnit.USD_PER_MT,
        base_vlsfo_price_usd_mt=610.0,
        origin_waiting_hours=10.0,
        destination_waiting_hours=20.0,
        cost_reference_date=sample_cargo_request.laycan_start_date,
    )
    service = ScenarioService()
    results = service.run_scenarios(inputs, persist=False)
    assert results.baseline.estimated_total_cost > 0
    assert len(results.as_list()) == 3
