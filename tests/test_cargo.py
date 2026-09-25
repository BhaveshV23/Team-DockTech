from datetime import datetime, timezone
import os
import sys
from uuid import uuid4

# Ensure backend directory is in sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from fastapi.testclient import TestClient
import jwt
from app.core.config import settings
from app.repositories.cargo_repository import cargo_repository
from app.repositories.user_repository import user_repository
from main import app

TEST_JWT_SECRET = "docktech-test-jwt-secret-key-32-bytes-long"
settings.SUPABASE_JWT_SECRET = TEST_JWT_SECRET

client = TestClient(app)


def helper_create_test_user(display_name: str = "Test User", role: str = "PLANNER"):
    user_id = uuid4()
    auth_user_id = uuid4()
    now = datetime.now(timezone.utc).isoformat()

    profile = {
        "user_id": str(user_id),
        "auth_user_id": str(auth_user_id),
        "display_name": display_name,
        "email": f"{str(user_id)[:8]}@docktech.com",
        "role": role,
        "created_at": now,
        "updated_at": now,
    }
    user_repository.add_mock_profile(profile)
    token = jwt.encode(
        {"sub": str(auth_user_id), "email": profile["email"]},
        TEST_JWT_SECRET,
        algorithm="HS256",
    )
    return token, profile


def test_unauthenticated_cargo_request_create_returns_401():
    """Verify unauthenticated request to POST /api/v1/cargo-requests returns 401."""
    payload = {
        "commodity": "THERMAL_COAL",
        "cargo_volume_mt": 75000.0,
        "origin_port_id": "NEWCASTLE",
        "destination_port_id": "PARADIP",
        "earliest_delivery_date": "2026-10-01",
        "latest_delivery_date": "2026-10-15",
        "contract_horizon": "SPOT",
    }
    response = client.post("/api/v1/cargo-requests", json=payload)
    assert response.status_code == 401
    assert "Missing authorization token" in response.json()["detail"]


def test_invalid_cargo_input_negative_volume():
    """Verify negative volume triggers validation error (422)."""
    token, _ = helper_create_test_user()
    payload = {
        "commodity": "THERMAL_COAL",
        "cargo_volume_mt": -1000.0,
        "origin_port_id": "NEWCASTLE",
        "destination_port_id": "PARADIP",
        "earliest_delivery_date": "2026-10-01",
        "latest_delivery_date": "2026-10-15",
        "contract_horizon": "SPOT",
    }
    try:
        response = client.post(
            "/api/v1/cargo-requests",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        assert response.status_code == 422
    finally:
        user_repository.clear_mock_profiles()


def test_invalid_cargo_input_dates_order():
    """Verify latest delivery date before earliest delivery date triggers validation error (422)."""
    token, _ = helper_create_test_user()
    payload = {
        "commodity": "THERMAL_COAL",
        "cargo_volume_mt": 75000.0,
        "origin_port_id": "NEWCASTLE",
        "destination_port_id": "PARADIP",
        "earliest_delivery_date": "2026-10-20",
        "latest_delivery_date": "2026-10-10",
        "contract_horizon": "SPOT",
    }
    try:
        response = client.post(
            "/api/v1/cargo-requests",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        assert response.status_code == 422
    finally:
        user_repository.clear_mock_profiles()


def test_invalid_cargo_input_same_origin_and_destination():
    """Verify same origin and destination port triggers validation error (422)."""
    token, _ = helper_create_test_user()
    payload = {
        "commodity": "THERMAL_COAL",
        "cargo_volume_mt": 75000.0,
        "origin_port_id": "NEWCASTLE",
        "destination_port_id": "NEWCASTLE",
        "earliest_delivery_date": "2026-10-01",
        "latest_delivery_date": "2026-10-15",
        "contract_horizon": "SPOT",
    }
    try:
        response = client.post(
            "/api/v1/cargo-requests",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        assert response.status_code == 422
    finally:
        user_repository.clear_mock_profiles()


def test_invalid_cargo_input_nonexistent_port():
    """Verify referencing a non-existent port triggers 422 error."""
    token, _ = helper_create_test_user()
    payload = {
        "commodity": "THERMAL_COAL",
        "cargo_volume_mt": 75000.0,
        "origin_port_id": "NON_EXISTENT_PORT_123",
        "destination_port_id": "PARADIP",
        "earliest_delivery_date": "2026-10-01",
        "latest_delivery_date": "2026-10-15",
        "contract_horizon": "SPOT",
    }
    try:
        response = client.post(
            "/api/v1/cargo-requests",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        assert response.status_code == 422
        assert "invalid or not found" in response.json()["detail"].lower()
    finally:
        user_repository.clear_mock_profiles()


def test_valid_cargo_request_create_and_identity_derivation():
    """Verify creating a valid cargo request derives user_id from auth token and ignores client user_id override."""
    token, profile = helper_create_test_user()
    fake_user_id = str(uuid4())

    payload = {
        "user_id": fake_user_id,  # Attempting to override user_id
        "commodity": "THERMAL_COAL",
        "quantity_tonnes": 75000.0,  # Using quantity_tonnes alias
        "origin_port_id": "NEWCASTLE",
        "destination_port_id": "PARADIP",
        "delivery_start": "2026-10-01",  # Using delivery_start alias
        "delivery_end": "2026-10-15",    # Using delivery_end alias
        "contract_horizon": "SPOT",
    }
    try:
        response = client.post(
            "/api/v1/cargo-requests",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["cargo_request_id"] is not None
        # Confirms client user_id override attempt was IGNORED and derived from auth profile
        assert data["user_id"] == profile["user_id"]
        assert data["user_id"] != fake_user_id
        assert data["commodity"] == "THERMAL_COAL"
        assert data["cargo_volume_mt"] == 75000.0
        assert data["origin_port_id"] == "NEWCASTLE"
        assert data["destination_port_id"] == "PARADIP"
        assert data["contract_horizon"] == "SPOT"
    finally:
        cargo_repository.clear_mock_requests()
        user_repository.clear_mock_profiles()


def test_retrieve_existing_cargo_request_success():
    """Verify owner can successfully retrieve existing cargo request by ID."""
    token, profile = helper_create_test_user()
    payload = {
        "commodity": "COKING_COAL",
        "cargo_volume_mt": 120000.0,
        "origin_port_id": "GLADSTONE",
        "destination_port_id": "VISAKHAPATNAM",
        "earliest_delivery_date": "2026-11-01",
        "latest_delivery_date": "2026-11-20",
        "contract_horizon": "SHORT_TERM",
    }
    try:
        create_resp = client.post(
            "/api/v1/cargo-requests",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        assert create_resp.status_code == 201
        created_id = create_resp.json()["cargo_request_id"]

        get_resp = client.get(
            f"/api/v1/cargo-requests/{created_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_resp.status_code == 200
        retrieved_data = get_resp.json()
        assert retrieved_data["cargo_request_id"] == created_id
        assert retrieved_data["user_id"] == profile["user_id"]
        assert retrieved_data["commodity"] == "COKING_COAL"
        assert retrieved_data["cargo_volume_mt"] == 120000.0
    finally:
        cargo_repository.clear_mock_requests()
        user_repository.clear_mock_profiles()


def test_retrieve_unauthorized_cargo_request_returns_404():
    """Verify non-owner non-manager user receiving another user's cargo_request_id gets 404."""
    token_owner, _ = helper_create_test_user("Owner User", "PLANNER")
    token_other, _ = helper_create_test_user("Other User", "PLANNER")

    payload = {
        "commodity": "THERMAL_COAL",
        "cargo_volume_mt": 50000.0,
        "origin_port_id": "BALTIMORE",
        "destination_port_id": "HALDIA",
        "earliest_delivery_date": "2026-12-01",
        "latest_delivery_date": "2026-12-10",
        "contract_horizon": "FLEXIBLE",
    }
    try:
        create_resp = client.post(
            "/api/v1/cargo-requests",
            headers={"Authorization": f"Bearer {token_owner}"},
            json=payload,
        )
        assert create_resp.status_code == 201
        created_id = create_resp.json()["cargo_request_id"]

        # Other user tries to access owner's request
        get_resp = client.get(
            f"/api/v1/cargo-requests/{created_id}",
            headers={"Authorization": f"Bearer {token_other}"},
        )
        assert get_resp.status_code == 404
        assert "not found" in get_resp.json()["detail"].lower()
    finally:
        cargo_repository.clear_mock_requests()
        user_repository.clear_mock_profiles()


def test_retrieve_nonexistent_cargo_request_returns_404():
    """Verify requesting non-existent UUID returns 404."""
    token, _ = helper_create_test_user()
    non_existent_id = str(uuid4())
    try:
        response = client.get(
            f"/api/v1/cargo-requests/{non_existent_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    finally:
        user_repository.clear_mock_profiles()
