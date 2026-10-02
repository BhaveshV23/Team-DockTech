"""Service and persistence tests for canonical scenario orchestration."""

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4
import csv
from pathlib import Path

import pytest

from backend.app.domain.constants import ScenarioType
from backend.app.repositories.reference_repository import (
    BerthRecord, RouteRecord, VesselClassRecord,
)
from backend.app.repositories.scenario_repository import ScenarioPersistenceError, ScenarioRepository
from backend.app.domain.cost.resolver import CostInputResolver
from backend.app.services.scenario_service import ScenarioService


class _Response:
    def __init__(self, data):
        self.data = data


class _Table:
    def __init__(self, owner, name):
        self.owner, self.name = owner, name
        self.record = None
        self.selected = False

    def select(self, *_columns):
        self.selected = True
        return self

    def insert(self, record):
        self.record = record
        return self

    def execute(self):
        if self.selected and self.owner.fail_reads:
            raise RuntimeError("database read failed")
        if not self.selected and self.owner.fail_inserts:
            raise RuntimeError("database down")
        if self.selected:
            return _Response(self.owner.scenario_defaults)
        self.owner.rows.append(self.record)
        return _Response([self.record])


class _DB:
    def __init__(self, fail=False, fail_reads=False):
        self.fail_inserts, self.fail_reads, self.rows = fail, fail_reads, []
        self.scenario_defaults = self._load_scenario_defaults()
        self.selected_tables = []

    def table(self, name):
        self.selected_tables.append(name)
        return _Table(self, name)

    @staticmethod
    def _load_scenario_defaults():
        path = Path(__file__).resolve().parents[2] / "data" / "reference" / "scenario_defaults.csv"
        with path.open(encoding="utf-8", newline="") as stream:
            return list(csv.DictReader(stream))


def test_scenario_service_loads_canonical_defaults():
    defaults = ScenarioService(repository=ScenarioRepository(
        reference_data_dir=Path(__file__).resolve().parents[2] / "data" / "reference"
    )).get_scenario_defaults()
    assert {d.scenario_id for d in defaults} == {
        ScenarioType.BASELINE, ScenarioType.ADVERSE, ScenarioType.FAVORABLE,
    }


def test_default_scenario_repository_uses_shared_supabase_reference_repository(monkeypatch):
    from backend.app.repositories.reference_repository import reference_repository

    expected_rows = _DB._load_scenario_defaults()
    queried = []

    def get_rows(table, params):
        queried.append((table, params))
        return expected_rows

    monkeypatch.setattr(reference_repository, "get_rows", get_rows)
    repository = ScenarioRepository()
    defaults = repository.get_scenario_defaults()

    assert repository.use_supabase_reference_data is True
    assert queried == [("scenario_defaults", {"order": "scenario_id.asc"})]
    assert len(defaults) == 3


def test_injected_db_client_reads_scenario_defaults_from_database():
    db = _DB()
    defaults = ScenarioRepository(db_client=db).get_scenario_defaults()

    assert [default.scenario_id for default in defaults] == [
        ScenarioType.BASELINE, ScenarioType.ADVERSE, ScenarioType.FAVORABLE,
    ]
    assert db.selected_tables == ["scenario_defaults"]


def test_injected_db_failure_does_not_read_scenario_defaults_csv(monkeypatch):
    db = _DB(fail_reads=True)
    original_open = Path.open

    def reject_scenario_csv(path, *args, **kwargs):
        if path.name == "scenario_defaults.csv":
            pytest.fail("scenario_defaults.csv must not be read after a DB failure")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", reject_scenario_csv)
    repository = ScenarioRepository(db_client=db)

    from backend.app.repositories.scenario_repository import ScenarioStorageUnavailable
    with pytest.raises(ScenarioStorageUnavailable, match="Canonical scenario defaults are unavailable"):
        repository.get_scenario_defaults()
    assert db.selected_tables == ["scenario_defaults"]


def test_scenario_service_persists_canonical_set_to_database(sample_decision_inputs):
    db = _DB()
    service = ScenarioService(repository=ScenarioRepository(db_client=db))
    results = service.run_scenarios(sample_decision_inputs, persist=True)
    assert [r.scenario_type for r in results.as_list()] == [
        ScenarioType.BASELINE, ScenarioType.ADVERSE, ScenarioType.FAVORABLE,
    ]
    assert len(db.rows) == 3
    assert {row["scenario_type"] for row in db.rows} == {"BASELINE", "ADVERSE", "FAVORABLE"}
    assert all(row["cargo_request_id"] == str(sample_decision_inputs.cargo_request.cargo_request_id) for row in db.rows)


def test_scenario_persistence_failure_propagates_without_false_success(sample_decision_inputs):
    service = ScenarioService(repository=ScenarioRepository(db_client=_DB(fail=True)))
    with pytest.raises(ScenarioPersistenceError):
        service.run_scenarios(sample_decision_inputs, persist=True)


@pytest.mark.parametrize("use_created_forecast", [False, True])
@pytest.mark.parametrize("use_cost_context", [False, True])
def test_resolves_inputs_from_authorized_cargo_forecast_and_reference_records(
    use_created_forecast, use_cost_context
):
    cargo_id, forecast_id, user_id = uuid4(), uuid4(), uuid4()
    profile = SimpleNamespace(user_id=user_id, role="PLANNER")
    cargo = SimpleNamespace(
        cargo_request_id=cargo_id, user_id=user_id, commodity="THERMAL_COAL", cargo_volume_mt=70000,
        origin_port_id="AU_NCL", destination_port_id="IN_PRT", earliest_delivery_date=date(2026, 10, 1),
        latest_delivery_date=date(2026, 10, 31), contract_horizon="SPOT", created_at=datetime.now(timezone.utc),
    )

    class CargoAccess:
        def get_cargo_request(self, requested_id, requested_profile):
            assert requested_id == cargo_id and requested_profile is profile
            return cargo

    class Forecasts:
        run_reads = 0
        point_reads = 0

        def get_forecast_run(self, requested_id):
            self.run_reads += 1
            assert requested_id == forecast_id
            return {
                "forecast_run_id": str(forecast_id),
                "cargo_request_id": str(cargo_id), "route_id": "R1", "vessel_class_id": "PANAMAX",
                "freight_unit": "USD_PER_MT", "training_data_end_date": "2026-09-20",
            }

        def get_forecast_points(self, requested_id):
            self.point_reads += 1
            return [
                {"forecast_run_id": str(forecast_id), "unit": "USD_PER_MT", "central_value": 20, "lower_value": 18, "upper_value": 22},
                {"forecast_run_id": str(forecast_id), "unit": "USD_PER_MT", "central_value": 21, "lower_value": 18, "upper_value": 24},
            ]

    vessel = VesselClassRecord(
        "PANAMAX", "Panamax", Decimal("60000"), Decimal("85000"), Decimal("225"), Decimal("32"),
        Decimal("14"), Decimal("13"), Decimal("75000"), Decimal("28"), "CANONICAL", "ACTUAL",
    )
    route = RouteRecord("R1", "AU_NCL", "IN_PRT", "THERMAL_COAL", Decimal("5600"), Decimal("18"), "CANONICAL", "ACTUAL")
    berth = BerthRecord("B1", "AU_NCL", "Canonical berth", "THERMAL_COAL", Decimal("250"), Decimal("40"), Decimal("16"), Decimal("50000"), "CANONICAL", "ACTUAL")

    class References:
        def __init__(self):
            self.calls = []

        def get_route(self, **kwargs):
            self.calls.append("route")
            assert kwargs == {"origin_port_id": "AU_NCL", "destination_port_id": "IN_PRT", "commodity": "THERMAL_COAL"}
            return route

        def get_vessel_class(self, vessel_class_id):
            self.calls.append("vessel")
            return vessel

        def get_compatible_berth(self, port_id, commodity, vessel_class):
            self.calls.append(f"berth:{port_id}")
            return berth if port_id == "AU_NCL" else BerthRecord(
                "B2", "IN_PRT", "Destination berth", commodity, Decimal("250"), Decimal("40"), Decimal("16"),
                Decimal("30000"), "CANONICAL", "ACTUAL",
            )

        def get_latest_port_waiting_hours(self, port_id, reference_date):
            self.calls.append(f"waiting:{port_id}")
            assert reference_date == date(2026, 9, 20)
            return Decimal("12" if port_id == "AU_NCL" else "36")

        def get_latest_vlsfo_price(self, reference_date):
            self.calls.append("fuel")
            return Decimal("620")

    references = References()
    service = ScenarioService(
        repository=ScenarioRepository(db_client=_DB()), cargo_access_service=CargoAccess(),
        forecast_repo=Forecasts(), reference_repository=references,
    )
    created_run = {
        "forecast_run_id": str(forecast_id), "cargo_request_id": str(cargo_id), "route_id": "R1",
        "vessel_class_id": "PANAMAX", "freight_unit": "USD_PER_MT", "training_data_end_date": "2026-09-20",
    }
    created_points = [
        {"forecast_run_id": str(forecast_id), "unit": "USD_PER_MT", "central_value": 20, "lower_value": 18, "upper_value": 22},
        {"forecast_run_id": str(forecast_id), "unit": "USD_PER_MT", "central_value": 21, "lower_value": 18, "upper_value": 24},
    ]
    forecast_repo = service.forecast_repo
    cost_context = None
    if use_cost_context:
        cost_context = CostInputResolver(references).resolve_cost_context(
            cargo_volume_mt=Decimal("70000"), origin_port_id="AU_NCL", destination_port_id="IN_PRT",
            commodity="THERMAL_COAL", vessel_class_id="PANAMAX", freight_unit="USD_PER_MT",
            cost_reference_date=date(2026, 9, 20), freight_rate_override=Decimal("20"),
        )
    calls_before_scenario = len(references.calls)
    inputs = service.resolve_decision_inputs(
        cargo_id, forecast_id, profile,
        **({"forecast_run": created_run, "forecast_points": created_points} if use_created_forecast else {}),
        **({"cost_context": cost_context} if use_cost_context else {}),
    )
    assert inputs.cargo_request.cargo_volume_mt == 70000
    assert inputs.route.route_id == "R1"
    assert inputs.vessel_class.vessel_class_id == "PANAMAX"
    assert inputs.base_freight_rate == 20
    assert inputs.cost_reference_date == date(2026, 9, 20)
    assert inputs.forecast_spread_pct == pytest.approx(6 / 21 * 100)
    assert forecast_repo.run_reads == (0 if use_created_forecast else 1)
    assert forecast_repo.point_reads == (0 if use_created_forecast else 1)
    assert len(references.calls) - calls_before_scenario == (0 if use_cost_context else 7)
    if cost_context:
        assert inputs.route == cost_context.route
        assert inputs.vessel_class == cost_context.vessel_class
        assert inputs.origin_berth == cost_context.origin_berth
        assert inputs.destination_berth == cost_context.destination_berth
        assert inputs.origin_berth.handling_rate_tpd == 50000
        assert inputs.destination_berth.handling_rate_tpd == 30000
        assert inputs.base_vlsfo_price_usd_mt == 620
        assert inputs.origin_waiting_hours == 12
        assert inputs.destination_waiting_hours == 36


def test_forecast_cargo_link_mismatch_is_rejected():
    cargo_id, forecast_id = uuid4(), uuid4()
    service = ScenarioService(
        cargo_access_service=SimpleNamespace(get_cargo_request=lambda *_: SimpleNamespace(cargo_request_id=cargo_id)),
        forecast_repo=SimpleNamespace(get_forecast_run=lambda _: {"cargo_request_id": str(uuid4())}),
        reference_repository=SimpleNamespace(),
    )
    with pytest.raises(Exception, match="does not belong"):
        service.resolve_decision_inputs(cargo_id, forecast_id, SimpleNamespace())
