from datetime import datetime, timezone
import os
import sys
from unittest.mock import patch
from uuid import uuid4

# Ensure backend directory is in sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from fastapi.testclient import TestClient
import jwt
from app.core.config import settings
from app.repositories.reference_repository import reference_repository
from app.repositories.user_repository import user_repository
from main import app

TEST_JWT_SECRET = "docktech-test-jwt-secret-key-32-bytes-long"
settings.SUPABASE_JWT_SECRET = TEST_JWT_SECRET

client = TestClient(app)


def helper_create_test_user():
    user_id = uuid4()
    auth_user_id = uuid4()
    now = datetime.now(timezone.utc).isoformat()

    profile = {
        "user_id": str(user_id),
        "auth_user_id": str(auth_user_id),
        "display_name": "Reference Test User",
        "email": "ref_user@docktech.com",
        "role": "VIEWER",
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


def test_unauthenticated_reference_requests_return_401():
    """Verify unauthenticated GET requests to /ports, /vessels, and /routes return 401."""
    assert client.get("/api/v1/ports").status_code == 401
    assert client.get("/api/v1/vessels").status_code == 401
    assert client.get("/api/v1/routes").status_code == 401


def test_authenticated_get_ports_success():
    """Verify authenticated GET /api/v1/ports returns 200 and canonical port fields."""
    token, _ = helper_create_test_user()
    try:
        response = client.get(
            "/api/v1/ports", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        ports = response.json()
        assert isinstance(ports, list)
        assert len(ports) > 0

        first = ports[0]
        # Verify exact field names matching Data Dictionary / Schema
        assert "port_id" in first
        assert "port_name" in first
        assert "country" in first
        assert "max_loa_m" in first
        assert "max_beam_m" in first
        assert "max_draft_m" in first
        assert "handling_rate_tpd" in first
        assert "typical_turnaround_hours" in first
        assert "source" in first
        assert "data_type" in first
    finally:
        user_repository.clear_mock_profiles()


def test_authenticated_get_vessels_success():
    """Verify authenticated GET /api/v1/vessels returns 200 and canonical vessel fields."""
    token, _ = helper_create_test_user()
    try:
        response = client.get(
            "/api/v1/vessels", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        vessels = response.json()
        assert isinstance(vessels, list)
        assert len(vessels) > 0

        first = vessels[0]
        # Verify exact field names matching Data Dictionary / Schema
        assert "vessel_class_id" in first
        assert "vessel_class_name" in first
        assert "dwt_min_mt" in first
        assert "dwt_max_mt" in first
        assert "loa_m" in first
        assert "beam_m" in first
        assert "draft_m" in first
        assert "speed_knots" in first
        assert "cargo_capacity_mt" in first
        assert "fuel_consumption_mt_day" in first
        assert "source" in first
        assert "data_type" in first
    finally:
        user_repository.clear_mock_profiles()


def test_authenticated_get_routes_success():
    """Verify authenticated GET /api/v1/routes returns 200 and canonical route fields."""
    token, _ = helper_create_test_user()
    try:
        response = client.get(
            "/api/v1/routes", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        routes = response.json()
        assert isinstance(routes, list)
        assert len(routes) > 0

        first = routes[0]
        # Verify exact field names matching Data Dictionary / Schema
        assert "route_id" in first
        assert "origin_port_id" in first
        assert "destination_port_id" in first
        assert "commodity" in first
        assert "distance_nm" in first
        assert "typical_sailing_days" in first
        assert "source" in first
        assert "data_type" in first
    finally:
        user_repository.clear_mock_profiles()


def test_empty_dataset_valid_response():
    """Verify an empty database response returns an empty list [], not fabricated records."""
    token, _ = helper_create_test_user()
    with patch.object(reference_repository, "get_ports", return_value=[]):
        try:
            response = client.get(
                "/api/v1/ports", headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
            assert response.json() == []
        finally:
            user_repository.clear_mock_profiles()


def test_repository_failure_returns_safe_500():
    """Verify database/repository failures raise safe 500 error without leaking credentials."""
    token, _ = helper_create_test_user()
    with patch.object(
        reference_repository,
        "get_ports",
        side_effect=Exception("Database connection secret_password_123 failed"),
    ):
        try:
            response = client.get(
                "/api/v1/ports", headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 500
            detail = response.json()["detail"]
            assert "secret_password_123" not in detail
            assert "Failed to retrieve reference ports" in detail
        finally:
            user_repository.clear_mock_profiles()
