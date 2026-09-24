"""Service tests for DockTech V1 Scenario Service."""

from uuid import uuid4
import pytest

from backend.app.domain.constants import CongestionLevel, ScenarioType
from backend.app.domain.entities import DecisionInputs
from backend.app.domain.scenario import ScenarioParameterShock
from backend.app.repositories.scenario_repository import ScenarioRepository
from backend.app.services.scenario_service import ScenarioService


def test_scenario_service_loads_canonical_defaults():
    """Verify ScenarioService loads all 3 canonical presets."""
    service = ScenarioService()
    defaults = service.get_scenario_defaults()
    assert len(defaults) == 3
    ids = {d.scenario_id for d in defaults}
    assert ids == {ScenarioType.BASELINE, ScenarioType.ADVERSE, ScenarioType.FAVORABLE}


def test_scenario_service_runs_and_persists_canonical_set(
    sample_decision_inputs: DecisionInputs,
):
    """Verify run_scenarios returns 3 results and saves them to repository."""
    repo = ScenarioRepository()
    service = ScenarioService(repository=repo)
    results = service.run_scenarios(sample_decision_inputs, persist=True)

    assert results.baseline.scenario_type == ScenarioType.BASELINE
    assert results.adverse.scenario_type == ScenarioType.ADVERSE
    assert results.favorable.scenario_type == ScenarioType.FAVORABLE

    saved = service.get_saved_scenarios(sample_decision_inputs.cargo_request.cargo_request_id)
    assert len(saved) == 3


def test_scenario_service_evaluate_custom_shock(
    sample_decision_inputs: DecisionInputs,
):
    """Verify custom parameter shock calculation and comparison."""
    service = ScenarioService()
    shock = ScenarioParameterShock(
        freight_change_pct=15.0,
        fuel_change_pct=10.0,
        delay_hours=12.0,
        congestion_level=CongestionLevel.MEDIUM,
    )
    comparison = service.evaluate_custom_scenario(
        base_inputs=sample_decision_inputs,
        shock=shock,
        scenario_type=ScenarioType.ADVERSE,
        persist=False,
    )

    assert comparison.delta_turnaround_hours == 12.0
    assert comparison.delta_cost_usd > 0
    assert comparison.baseline_result.scenario_type == ScenarioType.BASELINE
    assert comparison.scenario_result.scenario_type == ScenarioType.ADVERSE
