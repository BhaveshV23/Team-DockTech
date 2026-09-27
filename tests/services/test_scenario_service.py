"""Service and persistence tests for canonical scenario orchestration."""

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.app.domain.constants import ScenarioType
from backend.app.repositories.reference_repository import (
    BerthRecord, RouteRecord, VesselClassRecord,
)
from backend.app.repositories.scenario_repository import ScenarioPersistenceError, ScenarioRepository
from backend.app.services.scenario_service import ScenarioService


class _Response:
    def __init__(self, data):
        self.data = data


class _Table:
    def __init__(self, owner, name):
        self.owner, self.name = owner, name
        self.record = None

    def insert(self, record):
        self.record = record
        return self

    def execute(self):
        if self.owner.fail:
            raise RuntimeError("database down")
        self.owner.rows.append(self.record)
        return _Response([self.record])


class _DB:
    def __init__(self, fail=False):
        self.fail, self.rows = fail, []

    def table(self, name):
        return _Table(self, name)


def test_scenario_service_loads_canonical_defaults():
    defaults = ScenarioService().get_scenario_defaults()
    assert {d.scenario_id for d in defaults} == {
        ScenarioType.BASELINE, ScenarioType.ADVERSE, ScenarioType.FAVORABLE,
    }


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


def test_resolves_inputs_from_authorized_cargo_forecast_and_reference_records():
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
        def get_forecast_run(self, requested_id):
            assert requested_id == forecast_id
            return {
                "cargo_request_id": str(cargo_id), "route_id": "R1", "vessel_class_id": "PANAMAX",
                "freight_unit": "USD_PER_MT", "training_data_end_date": "2026-09-20",
            }

        def get_forecast_points(self, requested_id):
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
        def get_route(self, **kwargs):
            assert kwargs == {"origin_port_id": "AU_NCL", "destination_port_id": "IN_PRT", "commodity": "THERMAL_COAL"}
            return route

        def get_vessel_class(self, vessel_class_id):
            return vessel

        def get_compatible_berth(self, port_id, commodity, vessel_class):
            return berth if port_id == "AU_NCL" else BerthRecord(
                "B2", "IN_PRT", "Destination berth", commodity, Decimal("250"), Decimal("40"), Decimal("16"),
                Decimal("30000"), "CANONICAL", "ACTUAL",
            )

        def get_latest_port_waiting_hours(self, port_id, reference_date):
            assert reference_date == date(2026, 9, 20)
            return Decimal("12" if port_id == "AU_NCL" else "36")

        def get_latest_vlsfo_price(self, reference_date):
            return Decimal("620")

    service = ScenarioService(
        repository=ScenarioRepository(db_client=_DB()), cargo_access_service=CargoAccess(),
        forecast_repo=Forecasts(), reference_repository=References(),
    )
    inputs = service.resolve_decision_inputs(cargo_id, forecast_id, profile)
    assert inputs.cargo_request.cargo_volume_mt == 70000
    assert inputs.route.route_id == "R1"
    assert inputs.vessel_class.vessel_class_id == "PANAMAX"
    assert inputs.base_freight_rate == 20
    assert inputs.cost_reference_date == date(2026, 9, 20)
    assert inputs.forecast_spread_pct == pytest.approx(6 / 21 * 100)


def test_forecast_cargo_link_mismatch_is_rejected():
    cargo_id, forecast_id = uuid4(), uuid4()
    service = ScenarioService(
        cargo_access_service=SimpleNamespace(get_cargo_request=lambda *_: SimpleNamespace(cargo_request_id=cargo_id)),
        forecast_repo=SimpleNamespace(get_forecast_run=lambda _: {"cargo_request_id": str(uuid4())}),
        reference_repository=SimpleNamespace(),
    )
    with pytest.raises(Exception, match="does not belong"):
        service.resolve_decision_inputs(cargo_id, forecast_id, SimpleNamespace())
