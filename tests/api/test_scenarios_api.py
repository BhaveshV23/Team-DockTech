"""API tests for authenticated canonical scenario operations."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.core.dependencies import get_current_user_profile
from backend.app.domain.constants import CongestionLevel
from backend.app.domain.scenario import ScenarioParameterShock
from backend.app.main import app
from backend.app.schemas.auth import UserProfileResponse
from backend.app.services.scenario_service import ScenarioService
from backend.app.repositories.scenario_repository import ScenarioPersistenceError

client = TestClient(app)


def _profile():
    uid = uuid4()
    return UserProfileResponse(
        user_id=uid, auth_user_id=uuid4(), display_name="Planner", email="planner@example.test",
        role="PLANNER", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
    )


def test_scenario_endpoints_require_authentication():
    app.dependency_overrides.pop(get_current_user_profile, None)
    assert client.get("/api/v1/scenarios/defaults").status_code == 401
    ids = {"cargo_request_id": str(uuid4()), "forecast_run_id": str(uuid4())}
    assert client.post("/api/v1/scenarios/run-canonical", json=ids).status_code == 401
    assert client.post("/api/v1/scenarios/evaluate", json=ids).status_code == 401


def test_authenticated_requests_pass_only_canonical_ids_and_shock(sample_decision_inputs):
    profile = _profile()
    calls = {}
    base_service = ScenarioService()

    class ServiceDouble:
        def get_scenario_defaults(self):
            return base_service.get_scenario_defaults()

        def run_canonical_for_cargo(self, cargo_request_id, forecast_run_id, user_profile):
            calls["run"] = (cargo_request_id, forecast_run_id, user_profile)
            return base_service.run_scenarios(sample_decision_inputs, persist=False)

        def evaluate_canonical_for_cargo(self, cargo_request_id, forecast_run_id, user_profile, shock):
            calls["evaluate"] = (cargo_request_id, forecast_run_id, user_profile, shock)
            return base_service.evaluate_custom_scenario(sample_decision_inputs, shock, persist=False)

    from backend.app.api.v1.scenarios import get_scenario_service
    app.dependency_overrides[get_current_user_profile] = lambda: profile
    app.dependency_overrides[get_scenario_service] = lambda: ServiceDouble()
    try:
        cargo_id, forecast_id = uuid4(), uuid4()
        response = client.post("/api/v1/scenarios/run-canonical", json={
            "cargo_request_id": str(cargo_id), "forecast_run_id": str(forecast_id),
        })
        assert response.status_code == 200
        assert calls["run"] == (cargo_id, forecast_id, profile)
        evaluate = client.post("/api/v1/scenarios/evaluate", json={
            "cargo_request_id": str(cargo_id), "forecast_run_id": str(forecast_id),
            "freight_change_pct": 12, "fuel_change_pct": 5, "delay_hours": 8,
            "congestion_level": "HIGH",
        })
        assert evaluate.status_code == 200
        assert calls["evaluate"][:3] == (cargo_id, forecast_id, profile)
        assert calls["evaluate"][3] == ScenarioParameterShock(12, 5, 8, CongestionLevel.HIGH)
    finally:
        app.dependency_overrides.clear()


def test_client_cannot_supply_competing_canonical_inputs():
    profile = _profile()
    app.dependency_overrides[get_current_user_profile] = lambda: profile
    try:
        response = client.post("/api/v1/scenarios/run-canonical", json={
            "cargo_request_id": str(uuid4()), "forecast_run_id": str(uuid4()),
            "cargo_volume_mt": 1,
        })
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_database_persistence_failure_returns_structured_503():
    profile = _profile()

    class FailingService:
        def run_canonical_for_cargo(self, **kwargs):
            raise ScenarioPersistenceError("database unavailable")

    from backend.app.api.v1.scenarios import get_scenario_service
    app.dependency_overrides[get_current_user_profile] = lambda: profile
    app.dependency_overrides[get_scenario_service] = lambda: FailingService()
    try:
        response = client.post("/api/v1/scenarios/run-canonical", json={
            "cargo_request_id": str(uuid4()), "forecast_run_id": str(uuid4()),
        })
        assert response.status_code == 503
        assert response.json()["detail"] == {
            "code": "ERROR_SCENARIO_DATA_UNAVAILABLE", "message": "database unavailable",
        }
    finally:
        app.dependency_overrides.clear()
