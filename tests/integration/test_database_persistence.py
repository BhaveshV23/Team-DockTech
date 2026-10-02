"""Database persistence and integrity tests for scenarios table."""

from types import SimpleNamespace

from backend.app.domain.constants import CongestionLevel, ScenarioType
from backend.app.domain.entities import DecisionInputs
from backend.app.repositories.scenario_repository import ScenarioRepository
from backend.app.services.scenario_service import ScenarioService


def test_scenario_persistence_uses_database_adapter(
    sample_decision_inputs: DecisionInputs,
):
    """Verify scenario results are inserted through the repository database adapter."""
    class DB:
        def __init__(self):
            self.rows = []
            from pathlib import Path
            fixture_dir = Path(__file__).resolve().parents[2] / "data" / "reference"
            self.defaults = [
                {
                    "scenario_id": item.scenario_id.value,
                    "scenario_name": item.scenario_name,
                    "freight_change_pct": str(item.freight_change_pct),
                    "fuel_change_pct": str(item.fuel_change_pct),
                    "delay_hours": str(item.delay_hours),
                    "port_congestion_level": item.port_congestion_level.value,
                    "description": item.description,
                }
                for item in ScenarioRepository(reference_data_dir=fixture_dir).get_scenario_defaults()
            ]

        def table(self, _name):
            db = self
            class Table:
                selected = False

                def select(self, *_columns):
                    self.selected = True
                    return self

                def insert(self, row):
                    self.row = row
                    return self

                def execute(self):
                    if self.selected:
                        return SimpleNamespace(data=db.defaults)
                    db.rows.append(self.row)
                    return SimpleNamespace(data=[self.row])
            return Table()

    db = DB()
    repo = ScenarioRepository(db_client=db)
    service = ScenarioService(repository=repo)
    results = service.run_scenarios(sample_decision_inputs, persist=True)

    cargo_req_id = sample_decision_inputs.cargo_request.cargo_request_id
    assert len(db.rows) == 3
    assert {r["scenario_type"] for r in db.rows} == {"BASELINE", "ADVERSE", "FAVORABLE"}
    assert all(r["cargo_request_id"] == str(cargo_req_id) for r in db.rows)
    assert all(r["estimated_total_cost"] > 0 for r in db.rows)
    assert len(results.as_list()) == 3


def test_scenario_defaults_csv_integrity():
    """Verify canonical CSV has exact 3 rows and valid columns."""
    from pathlib import Path
    repo = ScenarioRepository(reference_data_dir=Path(__file__).resolve().parents[2] / "data" / "reference")
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
