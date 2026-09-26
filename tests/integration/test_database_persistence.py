"""Database persistence and integrity tests for scenarios table."""

from uuid import uuid4
import pytest

from backend.app.domain.constants import CongestionLevel, RiskLevel, ScenarioType
from backend.app.domain.entities import DecisionInputs, ScenarioResult
from backend.app.repositories.scenario_repository import ScenarioRepository
from backend.app.services.scenario_service import ScenarioService


def test_scenario_persistence_in_memory_and_query(
    sample_decision_inputs: DecisionInputs,
):
    """Verify ScenarioRepository persists and retrieves scenarios for a cargo request."""
    repo = ScenarioRepository()
    service = ScenarioService(repository=repo)
    results = service.run_scenarios(sample_decision_inputs, persist=True)

    cargo_req_id = sample_decision_inputs.cargo_request.cargo_request_id
    stored = repo.get_scenarios_by_cargo_request(cargo_req_id)

    assert len(stored) == 3
    types = {r.scenario_type for r in stored}
    assert types == {ScenarioType.BASELINE, ScenarioType.ADVERSE, ScenarioType.FAVORABLE}

    for r in stored:
        assert r.cargo_request_id == cargo_req_id
        assert r.estimated_total_cost > 0
        assert r.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]


def test_scenario_defaults_csv_integrity():
    """Verify canonical CSV has exact 3 rows and valid columns."""
    repo = ScenarioRepository()
    defaults = repo.get_scenario_defaults()
    assert len(defaults) == 3

    baseline = repo.get_scenario_default_by_type(ScenarioType.BASELINE)
    assert baseline.freight_change_pct == 0.0
    assert baseline.fuel_change_pct == 0.0
    assert baseline.delay_hours == 0.0
    assert baseline.port_congestion_level == CongestionLevel.MEDIUM

    adverse = repo.get_scenario_default_by_type(ScenarioType.ADVERSE)
    assert adverse.freight_change_pct == 25.0
    assert adverse.fuel_change_pct == 15.0
    assert adverse.delay_hours == 48.0
    assert adverse.port_congestion_level == CongestionLevel.HIGH

    favorable = repo.get_scenario_default_by_type(ScenarioType.FAVORABLE)
    assert favorable.freight_change_pct == -15.0
    assert favorable.fuel_change_pct == -10.0
    assert favorable.delay_hours == 0.0
    assert favorable.port_congestion_level == CongestionLevel.LOW
