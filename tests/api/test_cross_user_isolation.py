"""Cross-user ownership tests for registered cargo-scoped API operations."""

from datetime import datetime, timezone
from pathlib import Path
import sys
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

backend_path = str(Path(__file__).resolve().parents[2] / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.core.config import settings
from app.api.v1 import cost as cost_api
from app.repositories.cargo_repository import cargo_repository
from app.repositories.user_repository import user_repository
from app.services.cargo_service import cargo_service
from backend.app.repositories.cargo_repository import cargo_repository as backend_cargo_repository
from backend.main import app
from tests.auth_test_utils import TEST_SUPABASE_URL, supabase_test_token


TEST_SECRET = "cross-user-isolation-test-secret-key-32-bytes"
client = TestClient(app)


def _profile(role="PLANNER"):
    now = datetime.now(timezone.utc).isoformat()
    return {
        "user_id": str(uuid4()),
        "auth_user_id": str(uuid4()),
        "display_name": "Isolation Test User",
        "email": f"{uuid4()}@example.test",
        "role": role,
        "created_at": now,
        "updated_at": now,
    }


def _cargo(cargo_id, owner_id):
    return {
        "cargo_request_id": str(cargo_id),
        "user_id": str(owner_id),
        "commodity": "THERMAL_COAL",
        "cargo_volume_mt": 75000,
        "origin_port_id": "NEWCASTLE",
        "destination_port_id": "PARADIP",
        "earliest_delivery_date": "2026-10-01",
        "latest_delivery_date": "2026-10-15",
        "contract_horizon": "SPOT",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def two_user_context(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", TEST_SECRET)
    monkeypatch.setattr(settings, "SUPABASE_URL", TEST_SUPABASE_URL)
    # Other legacy API tests mutate the module singleton directly, so bind this
    # route back to the real owner-checking cargo service for isolation tests.
    monkeypatch.setattr(cost_api.cost_service, "cargo_access_service", cargo_service)
    user_a = _profile()
    user_b = _profile()
    cargo_a_id, cargo_b_id = uuid4(), uuid4()
    cargo_a = _cargo(cargo_a_id, user_a["user_id"])
    cargo_b = _cargo(cargo_b_id, user_b["user_id"])
    for profile in (user_a, user_b):
        user_repository.add_mock_profile(profile)
    cargo_by_id = {
        str(cargo_a_id): cargo_a,
        str(cargo_b_id): cargo_b,
    }
    monkeypatch.setattr(
        cargo_repository,
        "get_by_id",
        lambda cargo_id: cargo_by_id.get(str(cargo_id)),
    )
    monkeypatch.setattr(
        backend_cargo_repository,
        "get_by_id",
        lambda cargo_id: cargo_by_id.get(str(cargo_id)),
    )
    context = {
        "user_a": user_a,
        "user_b": user_b,
        "cargo_a": cargo_a,
        "cargo_b": cargo_b,
        "token_a": supabase_test_token(
            TEST_SECRET, {"sub": user_a["auth_user_id"], "email": user_a["email"]}
        ),
        "token_b": supabase_test_token(
            TEST_SECRET, {"sub": user_b["auth_user_id"], "email": user_b["email"]}
        ),
    }
    yield context
    user_repository.clear_mock_profiles()


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(
    ("user_key", "cargo_key"),
    [("token_a", "cargo_a"), ("token_b", "cargo_b")],
)
def test_users_can_retrieve_their_own_cargo(two_user_context, user_key, cargo_key):
    response = client.get(
        f"/api/v1/cargo-requests/{two_user_context[cargo_key]['cargo_request_id']}",
        headers=_headers(two_user_context[user_key]),
    )
    assert response.status_code == 200, response.text
    assert response.json()["cargo_request_id"] == two_user_context[cargo_key]["cargo_request_id"]


@pytest.mark.parametrize(
    ("user_key", "other_cargo_key"),
    [("token_a", "cargo_b"), ("token_b", "cargo_a")],
)
def test_users_cannot_retrieve_another_users_cargo(
    two_user_context, user_key, other_cargo_key
):
    response = client.get(
        f"/api/v1/cargo-requests/{two_user_context[other_cargo_key]['cargo_request_id']}",
        headers=_headers(two_user_context[user_key]),
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "operation",
    ["forecast", "cost", "scenario-canonical", "scenario-evaluate", "recommendation"],
)
@pytest.mark.parametrize(
    ("user_key", "other_cargo_key"),
    [("token_a", "cargo_b"), ("token_b", "cargo_a")],
)
def test_cargo_scoped_decision_operations_reject_cross_user_cargo(
    two_user_context, operation, user_key, other_cargo_key
):
    cargo_id = two_user_context[other_cargo_key]["cargo_request_id"]
    forecast_id = str(uuid4())
    if operation == "forecast":
        path, method, body = "/api/v1/forecast", "post", {
            "cargo_request_id": cargo_id,
            "route_id": "NEWCASTLE_PARADIP_THERMAL",
            "vessel_class_id": "PANAMAX",
            "freight_unit": "USD_PER_MT",
            "horizon": 7,
        }
    elif operation == "cost":
        path, method, body = "/api/v1/cost", "post", {
            "cargo_request_id": cargo_id,
            "forecast_run_id": forecast_id,
        }
    elif operation == "scenario-canonical":
        path, method, body = "/api/v1/scenarios/run-canonical", "post", {
            "cargo_request_id": cargo_id,
            "forecast_run_id": forecast_id,
        }
    elif operation == "scenario-evaluate":
        path, method, body = "/api/v1/scenarios/evaluate", "post", {
            "cargo_request_id": cargo_id,
            "forecast_run_id": forecast_id,
            "freight_change_pct": 1,
            "fuel_change_pct": 1,
            "delay_hours": 1,
            "congestion_level": "LOW",
        }
    else:
        path, method, body = "/api/v1/recommendations", "post", {
            "cargo_request_id": cargo_id,
        }

    response = client.request(
        method,
        path,
        json=body,
        headers=_headers(two_user_context[user_key]),
    )
    assert response.status_code == 404, (operation, response.status_code, response.text)


@pytest.mark.parametrize("role", ["MANAGER", "ADMINISTRATOR"])
def test_elevated_role_can_retrieve_other_users_cargo(
    two_user_context, monkeypatch, role
):
    elevated_profile = _profile(role)
    user_repository.add_mock_profile(elevated_profile)
    token = supabase_test_token(
        TEST_SECRET,
        {"sub": elevated_profile["auth_user_id"], "email": elevated_profile["email"]},
    )
    response = client.get(
        f"/api/v1/cargo-requests/{two_user_context['cargo_a']['cargo_request_id']}",
        headers=_headers(token),
    )
    assert response.status_code == 200, response.text
    assert response.json()["cargo_request_id"] == two_user_context["cargo_a"]["cargo_request_id"]


def test_unauthenticated_cross_user_operations_are_rejected(two_user_context):
    cargo_id = two_user_context["cargo_b"]["cargo_request_id"]
    response = client.get(f"/api/v1/cargo-requests/{cargo_id}")
    assert response.status_code == 401

    response = client.post(
        "/api/v1/recommendations",
        json={"cargo_request_id": cargo_id},
    )
    assert response.status_code == 401
