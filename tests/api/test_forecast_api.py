from datetime import date, datetime, timedelta, timezone
import os
import sys
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.api.v1 import forecast as forecast_api
from app.core.dependencies import get_current_user_profile
from app.repositories.cargo_repository import cargo_repository
from app.repositories.forecast_repository import forecast_repository
import app.repositories.forecast_repository as forecast_repository_module
from app.repositories.user_repository import user_repository
from app.services.forecast_service import forecast_application_service
from backend.main import app
from ml.service import ForecastPoint, ForecastResult


client = TestClient(app)


@pytest.fixture
def forecast_api_context(monkeypatch):
    user_id = uuid4()
    cargo_request_id = uuid4()
    now = datetime.now(timezone.utc).isoformat()
    profile = {
        "user_id": str(user_id),
        "auth_user_id": str(uuid4()),
        "display_name": "Forecast Planner",
        "email": "planner@example.test",
        "role": "PLANNER",
        "created_at": now,
        "updated_at": now,
    }
    cargo = {
        "cargo_request_id": str(cargo_request_id),
        "user_id": str(user_id),
        "commodity": "THERMAL_COAL",
        "cargo_volume_mt": 75000,
        "origin_port_id": "NEWCASTLE",
        "destination_port_id": "PARADIP",
        "earliest_delivery_date": "2026-10-01",
        "latest_delivery_date": "2026-10-15",
        "contract_horizon": "SPOT",
        "created_at": now,
    }
    state = {"runs": {}, "points": {}, "fail_table": None}

    class FakeResponse:
        def __init__(self, status_code, payload=None):
            self.status_code = status_code
            self.payload = payload

        def json(self):
            return self.payload

    class FakeSupabaseClient:
        def __init__(self, timeout=None):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, headers, json):
            table = url.rsplit("/", 1)[-1]
            if state["fail_table"] == table:
                return FakeResponse(500, {"message": "database failure"})
            if table == "forecast_runs":
                state["runs"][json["forecast_run_id"]] = dict(json)
                return FakeResponse(201, [dict(json)])
            persisted = []
            for row in json:
                saved = {**row, "forecast_point_id": str(uuid4())}
                persisted.append(saved)
            state["points"].setdefault(persisted[0]["forecast_run_id"], []).extend(persisted)
            return FakeResponse(201, persisted)

        def delete(self, url, headers, params):
            run_id = params["forecast_run_id"].removeprefix("eq.")
            state["runs"].pop(run_id, None)
            state["points"].pop(run_id, None)
            return FakeResponse(204)

    class FakeMLService:
        selected_models = {"NEWCASTLE_PARADIP_THERMAL||PANAMAX||USD_PER_MT": "seasonal_naive_7d"}

        def forecast(self, route_id, vessel_class_id, freight_unit, horizon):
            points = [
                ForecastPoint(
                    forecast_date=(date(2026, 9, 28) + timedelta(days=index)).isoformat(),
                    central=20.0,
                    lower=18.0,
                    upper=22.0,
                    freight_unit=freight_unit,
                    model_version="seasonal-v1",
                    training_data_end_date="2026-09-27",
                )
                for index in range(horizon)
            ]
            return ForecastResult(
                route_id, vessel_class_id, freight_unit, horizon, "seasonal-v1", points
            )

    previous_override = app.dependency_overrides.get(get_current_user_profile)
    app.dependency_overrides[get_current_user_profile] = lambda: forecast_api.UserProfileResponse(**profile)
    monkeypatch.setattr(cargo_repository, "get_by_id", lambda _id: cargo)
    monkeypatch.setattr(forecast_repository, "supabase_url", "https://supabase.test")
    monkeypatch.setattr(forecast_repository, "service_role_key", "test-service-key")
    monkeypatch.setattr(forecast_repository_module.httpx, "Client", FakeSupabaseClient)
    monkeypatch.setattr(forecast_application_service, "ml_service", FakeMLService())

    yield {"profile": profile, "cargo": cargo, "state": state}

    if previous_override is None:
        app.dependency_overrides.pop(get_current_user_profile, None)
    else:
        app.dependency_overrides[get_current_user_profile] = previous_override
    user_repository.clear_mock_profiles()


def _payload(cargo_request_id, **overrides):
    return {
        "cargo_request_id": str(cargo_request_id),
        "route_id": "NEWCASTLE_PARADIP_THERMAL",
        "vessel_class_id": "PANAMAX",
        "freight_unit": "USD_PER_MT",
        "horizon": 7,
        **overrides,
    }


def test_forecast_requires_authentication(forecast_api_context):
    override = app.dependency_overrides.pop(get_current_user_profile)
    try:
        response = client.post(
            "/api/v1/forecast",
            json=_payload(forecast_api_context["cargo"]["cargo_request_id"]),
        )
        assert response.status_code == 401
    finally:
        app.dependency_overrides[get_current_user_profile] = override


def test_forecast_checks_cargo_ownership(forecast_api_context, monkeypatch):
    cargo = dict(forecast_api_context["cargo"], user_id=str(uuid4()))
    monkeypatch.setattr(cargo_repository, "get_by_id", lambda _id: cargo)
    response = client.post(
        "/api/v1/forecast",
        json=_payload(cargo["cargo_request_id"]),
    )
    assert response.status_code == 404
    assert forecast_api_context["state"]["runs"] == {}


def test_forecast_rejects_route_inconsistent_with_cargo(forecast_api_context):
    response = client.post(
        "/api/v1/forecast",
        json=_payload(
            forecast_api_context["cargo"]["cargo_request_id"],
            route_id="NEWCASTLE_PARADIP_COKING",
        ),
    )
    assert response.status_code == 400
    assert forecast_api_context["state"]["runs"] == {}


def test_forecast_persists_run_and_linked_points_with_provenance(forecast_api_context):
    response = client.post(
        "/api/v1/forecast",
        json=_payload(forecast_api_context["cargo"]["cargo_request_id"]),
    )
    assert response.status_code == 200, (response.text, forecast_api_context["state"])
    result = response.json()
    run_id = result["forecast_run_id"]
    persisted_run = forecast_api_context["state"]["runs"][run_id]
    persisted_points = forecast_api_context["state"]["points"][run_id]

    assert persisted_run["cargo_request_id"] == forecast_api_context["cargo"]["cargo_request_id"]
    assert persisted_run["route_id"] == "NEWCASTLE_PARADIP_THERMAL"
    assert persisted_run["vessel_class_id"] == "PANAMAX"
    assert persisted_run["freight_unit"] == "USD_PER_MT"
    assert persisted_run["model_name"] == "seasonal_naive_7d"
    assert persisted_run["model_version"] == "seasonal-v1"
    assert persisted_run["training_data_end_date"] == "2026-09-27"
    assert len(persisted_points) == 7
    assert all(point["forecast_run_id"] == run_id for point in persisted_points)
    assert all(point["unit"] == persisted_run["freight_unit"] for point in persisted_points)


@pytest.mark.parametrize("failed_table", ["forecast_runs", "forecast_points"])
def test_forecast_persistence_failure_is_not_success_or_partial(
    forecast_api_context, failed_table
):
    state = forecast_api_context["state"]
    state["fail_table"] = failed_table
    response = client.post(
        "/api/v1/forecast",
        json=_payload(forecast_api_context["cargo"]["cargo_request_id"]),
    )
    assert response.status_code == 503
    assert state["runs"] == {}
    assert state["points"] == {}
