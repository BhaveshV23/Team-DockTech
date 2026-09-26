"""Integration tests verifying cost engine and scenario sensitivity alignment."""

import pytest
from backend.app.domain.constants import CongestionLevel, FreightUnit, ScenarioType
from backend.app.domain.entities import DecisionInputs
from backend.app.domain.scenario import ScenarioParameterShock
from backend.app.services.scenario_service import ScenarioService


def test_scenario_cost_alignment_usd_per_mt(sample_decision_inputs: DecisionInputs):
    """Verify scenario shocks apply strictly to cost components for USD_PER_MT."""
    service = ScenarioService()
    results = service.run_scenarios(sample_decision_inputs, persist=False)

    base = results.baseline
    adv = results.adverse
    fav = results.favorable

    # 1. Freight check
    assert adv.cost_breakdown.expected_freight_cost == base.cost_breakdown.expected_freight_cost * 1.25
    assert fav.cost_breakdown.expected_freight_cost == base.cost_breakdown.expected_freight_cost * 0.85

    # 2. Fuel check
    assert adv.cost_breakdown.total_fuel_cost_usd == pytest.approx(base.cost_breakdown.total_fuel_cost_usd * 1.15, abs=0.05)
    assert fav.cost_breakdown.total_fuel_cost_usd == pytest.approx(base.cost_breakdown.total_fuel_cost_usd * 0.90, abs=0.05)

    # 3. Turnaround delay check
    assert adv.cost_breakdown.scenario_delay_total == 48.0
    assert fav.cost_breakdown.scenario_delay_total == 0.0


def test_scenario_cost_alignment_usd_per_day(sample_decision_inputs: DecisionInputs):
    """Verify scenario shocks apply to daily charter hire for USD_PER_DAY."""
    from dataclasses import replace
    day_inputs = replace(
        sample_decision_inputs,
        freight_unit=FreightUnit.USD_PER_DAY,
        base_freight_rate=25000.0,
    )
    service = ScenarioService()
    results = service.run_scenarios(day_inputs, persist=False)

    base = results.baseline
    adv = results.adverse

    # Adverse freight rate = 25000 * 1.25 = 31250 USD/day
    # Adverse vessel days includes 48 extra delay hours (2 days)
    extra_days = 48.0 / 24.0  # 2.0 days
    assert round(adv.cost_breakdown.vessel_days_per_voyage - base.cost_breakdown.vessel_days_per_voyage, 4) == 2.0
    exact_sailing_days = 5600.0 / (13.0 * 24.0)
    exact_adv_vessel_days = exact_sailing_days + (adv.cost_breakdown.estimated_turnaround_hours / 24.0)
    expected_adv_freight = exact_adv_vessel_days * 31250.0 * 1
    assert adv.cost_breakdown.expected_freight_cost == pytest.approx(expected_adv_freight, abs=0.05)


