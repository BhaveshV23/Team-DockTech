"""Unit tests for DockTech V1 Scenario Engine.

Covers exact test cases SC-001 through SC-018 mandated in prompt.
"""

from uuid import UUID
import pytest

from backend.app.domain.constants import CongestionLevel, FreightUnit, RiskLevel, ScenarioType
from backend.app.domain.entities import DecisionInputs
from backend.app.domain.scenario import (
    ScenarioComparison,
    ScenarioEngine,
    ScenarioParameterShock,
)
from backend.app.services.scenario_service import ScenarioService


def test_sc_001_baseline_zero_freight_shock(sample_decision_inputs: DecisionInputs):
    """SC-001: BASELINE returns zero freight shock."""
    service = ScenarioService()
    results = service.run_scenarios(sample_decision_inputs, persist=False)
    assert results.baseline.freight_change_pct == 0.0


def test_sc_002_baseline_zero_fuel_shock(sample_decision_inputs: DecisionInputs):
    """SC-002: BASELINE returns zero fuel shock."""
    service = ScenarioService()
    results = service.run_scenarios(sample_decision_inputs, persist=False)
    assert results.baseline.fuel_change_pct == 0.0


def test_sc_003_baseline_zero_delay(sample_decision_inputs: DecisionInputs):
    """SC-003: BASELINE returns zero delay."""
    service = ScenarioService()
    results = service.run_scenarios(sample_decision_inputs, persist=False)
    assert results.baseline.delay_hours == 0.0


def test_sc_004_baseline_medium_congestion(sample_decision_inputs: DecisionInputs):
    """SC-004: BASELINE returns MEDIUM congestion."""
    service = ScenarioService()
    results = service.run_scenarios(sample_decision_inputs, persist=False)
    assert results.baseline.congestion_level == CongestionLevel.MEDIUM


def test_sc_005_adverse_freight_shock(sample_decision_inputs: DecisionInputs):
    """SC-005: ADVERSE returns +25% freight shock."""
    service = ScenarioService()
    results = service.run_scenarios(sample_decision_inputs, persist=False)
    assert results.adverse.freight_change_pct == 25.0


def test_sc_006_adverse_fuel_shock(sample_decision_inputs: DecisionInputs):
    """SC-006: ADVERSE returns +15% fuel shock."""
    service = ScenarioService()
    results = service.run_scenarios(sample_decision_inputs, persist=False)
    assert results.adverse.fuel_change_pct == 15.0


def test_sc_007_adverse_delay_hours(sample_decision_inputs: DecisionInputs):
    """SC-007: ADVERSE returns +48h delay."""
    service = ScenarioService()
    results = service.run_scenarios(sample_decision_inputs, persist=False)
    assert results.adverse.delay_hours == 48.0


def test_sc_008_adverse_high_congestion(sample_decision_inputs: DecisionInputs):
    """SC-008: ADVERSE returns HIGH congestion."""
    service = ScenarioService()
    results = service.run_scenarios(sample_decision_inputs, persist=False)
    assert results.adverse.congestion_level == CongestionLevel.HIGH


def test_sc_009_favorable_freight_shock(sample_decision_inputs: DecisionInputs):
    """SC-009: FAVORABLE returns -15% freight shock."""
    service = ScenarioService()
    results = service.run_scenarios(sample_decision_inputs, persist=False)
    assert results.favorable.freight_change_pct == -15.0


def test_sc_010_favorable_fuel_shock(sample_decision_inputs: DecisionInputs):
    """SC-010: FAVORABLE returns -10% fuel shock."""
    service = ScenarioService()
    results = service.run_scenarios(sample_decision_inputs, persist=False)
    assert results.favorable.fuel_change_pct == -10.0


def test_sc_011_favorable_zero_delay(sample_decision_inputs: DecisionInputs):
    """SC-011: FAVORABLE returns zero delay."""
    service = ScenarioService()
    results = service.run_scenarios(sample_decision_inputs, persist=False)
    assert results.favorable.delay_hours == 0.0


def test_sc_012_favorable_low_congestion(sample_decision_inputs: DecisionInputs):
    """SC-012: FAVORABLE returns LOW congestion."""
    service = ScenarioService()
    results = service.run_scenarios(sample_decision_inputs, persist=False)
    assert results.favorable.congestion_level == CongestionLevel.LOW


def test_sc_013_exactly_three_scenarios_returned(sample_decision_inputs: DecisionInputs):
    """SC-013: Exactly three scenario results are returned."""
    service = ScenarioService()
    results = service.run_scenarios(sample_decision_inputs, persist=False)
    scenario_list = results.as_list()
    assert len(scenario_list) == 3


def test_sc_014_no_duplicate_scenario_type(sample_decision_inputs: DecisionInputs):
    """SC-014: No duplicate scenario type is returned."""
    service = ScenarioService()
    results = service.run_scenarios(sample_decision_inputs, persist=False)
    types = [r.scenario_type for r in results.as_list()]
    assert set(types) == {ScenarioType.BASELINE, ScenarioType.ADVERSE, ScenarioType.FAVORABLE}
    assert len(types) == len(set(types))


def test_sc_015_correct_freight_unit_semantics(sample_decision_inputs: DecisionInputs):
    """SC-015: Correct freight unit semantics are respected (USD_PER_MT vs USD_PER_DAY)."""
    service = ScenarioService()
    
    # USD_PER_MT run
    results_mt = service.run_scenarios(sample_decision_inputs, persist=False)
    assert results_mt.baseline.cost_breakdown.expected_freight_cost == 75000.0 * 18.50

    # USD_PER_DAY run
    # Create input with USD_PER_DAY
    from dataclasses import replace
    day_inputs = replace(
        sample_decision_inputs,
        freight_unit=FreightUnit.USD_PER_DAY,
        base_freight_rate=22000.0,  # USD/day
    )
    results_day = service.run_scenarios(day_inputs, persist=False)
    vessel_days = results_day.baseline.cost_breakdown.vessel_days_per_voyage
    expected_hire = vessel_days * 22000.0 * 1
    assert results_day.baseline.cost_breakdown.expected_freight_cost == pytest.approx(expected_hire, abs=0.50)


def test_sc_016_vlsfo_is_used(sample_decision_inputs: DecisionInputs):
    """SC-016: VLSFO is used for sea-going fuel calculation."""
    service = ScenarioService()
    results = service.run_scenarios(sample_decision_inputs, persist=False)
    
    sailing_days = 5600.0 / (13.0 * 24.0)
    expected_fuel_usd = sailing_days * 28.0 * 620.0 * 1
    assert round(results.baseline.cost_breakdown.total_fuel_cost_usd, 2) == round(expected_fuel_usd, 2)


def test_sc_017_mgo_is_excluded(sample_decision_inputs: DecisionInputs):
    """SC-017: MGO is not used in V1 scenario cost."""
    service = ScenarioService()
    results = service.run_scenarios(sample_decision_inputs, persist=False)
    
    # Total cost = expected_freight_cost + vlsfo_fuel_cost + 0
    breakdown = results.baseline.cost_breakdown
    assert breakdown.expected_total_cost == round(
        breakdown.expected_freight_cost + breakdown.total_fuel_cost_usd, 2
    )


def test_sc_018_scenario_results_consistent_with_cost_engine(sample_decision_inputs: DecisionInputs):
    """SC-018: Scenario results remain consistent with the cost engine."""
    service = ScenarioService()
    results = service.run_scenarios(sample_decision_inputs, persist=False)

    # Adverse freight cost = 75000 * (18.50 * 1.25) = 75000 * 23.125 = 1734375.0
    assert results.adverse.cost_breakdown.expected_freight_cost == 75000.0 * (18.50 * 1.25)
    # Adverse fuel cost = sailing_days * 28.0 * (620.0 * 1.15)
    sailing_days = 5600.0 / (13.0 * 24.0)
    expected_adverse_fuel = sailing_days * 28.0 * (620.0 * 1.15)
    assert round(results.adverse.cost_breakdown.total_fuel_cost_usd, 2) == round(expected_adverse_fuel, 2)
    # Adverse turnaround includes +48h delay
    baseline_turnaround = results.baseline.estimated_turnaround_hours
    adverse_turnaround = results.adverse.estimated_turnaround_hours
    assert round(adverse_turnaround - baseline_turnaround, 2) == 48.0


def test_custom_scenario_delta_comparison(sample_decision_inputs: DecisionInputs):
    """Verifies delta calculations in custom scenario comparisons."""
    service = ScenarioService()
    shock = ScenarioParameterShock(
        freight_change_pct=10.0,
        fuel_change_pct=5.0,
        delay_hours=24.0,
        congestion_level=CongestionLevel.HIGH,
    )
    comparison = service.evaluate_custom_scenario(
        base_inputs=sample_decision_inputs,
        shock=shock,
        scenario_type=ScenarioType.ADVERSE,
        persist=False,
    )
    assert comparison.delta_cost_usd > 0
    assert comparison.delta_cost_pct > 0
    assert comparison.delta_turnaround_hours == 24.0
    assert comparison.baseline_result.scenario_type == ScenarioType.BASELINE
    assert comparison.scenario_result.scenario_type == ScenarioType.ADVERSE
