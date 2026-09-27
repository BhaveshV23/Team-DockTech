from datetime import datetime, timezone
import os
import sys
from unittest.mock import patch
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.core.config import settings
from app.repositories.user_repository import user_repository
from main import app


TEST_JWT_SECRET = "docktech-test-jwt-secret-key-32-bytes-long"
settings.SUPABASE_JWT_SECRET = TEST_JWT_SECRET
client = TestClient(app)


def _authenticated_headers():
    user_id = uuid4()
    auth_user_id = uuid4()
    now = datetime.now(timezone.utc).isoformat()
    profile = {
        "user_id": str(user_id),
        "auth_user_id": str(auth_user_id),
        "display_name": "Feasibility Test User",
        "email": "feasibility_user@docktech.com",
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
    return {"Authorization": f"Bearer {token}"}


def _result(*, feasible: bool, voyages: int | None):
    return type(
        "Result",
        (),
        {
            "is_feasible": feasible,
            "status": "FEASIBLE" if feasible else "INFEASIBLE",
            "required_voyages": voyages,
            "rejection_codes": [] if feasible else ["REJECTED_TEST"],
            "rejection_reasons": [] if feasible else ["Test rejection"],
        },
    )()


def _payload():
    return {
        "origin_port_id": "NEWCASTLE",
        "destination_port_id": "PARADIP",
        "commodity": "THERMAL_COAL",
        "vessel_class_id": "SUPRAMAX",
        "cargo_volume_mt": 50000,
    }


def test_feasibility_route_requires_authentication():
    response = client.post("/api/v1/feasibility", json=_payload())
    assert response.status_code == 401


def test_authenticated_feasibility_route_returns_result():
    headers = _authenticated_headers()
    try:
        with patch(
            "app.api.v1.feasibility.feasibility_service.check_feasibility",
            return_value=_result(feasible=True, voyages=1),
        ):
            response = client.post(
                "/api/v1/feasibility", json=_payload(), headers=headers
            )
        assert response.status_code == 200
        assert response.json()["is_feasible"] is True
        assert response.json()["required_voyages"] == 1
    finally:
        user_repository.clear_mock_profiles()


def test_insufficient_data_with_no_required_voyages_returns_structured_response():
    headers = _authenticated_headers()
    try:
        with patch(
            "app.api.v1.feasibility.feasibility_service.check_feasibility",
            return_value=type(
                "Result",
                (),
                {
                    "is_feasible": False,
                    "status": "INSUFFICIENT_DATA",
                    "required_voyages": None,
                    "rejection_codes": ["ERROR_ROUTE_NOT_FOUND"],
                    "rejection_reasons": ["No canonical route exists"],
                },
            )(),
        ):
            response = client.post(
                "/api/v1/feasibility", json=_payload(), headers=headers
            )
        assert response.status_code == 200
        assert response.json()["status"] == "INSUFFICIENT_DATA"
        assert response.json()["required_voyages"] is None
        assert response.json()["rejection_reason_code"] == "ERROR_ROUTE_NOT_FOUND"
    finally:
        user_repository.clear_mock_profiles()


def test_authenticated_feasibility_route_returns_infeasible_result():
    headers = _authenticated_headers()
    try:
        with patch(
            "app.api.v1.feasibility.feasibility_service.check_feasibility",
            return_value=_result(feasible=False, voyages=2),
        ):
            response = client.post(
                "/api/v1/feasibility", json=_payload(), headers=headers
            )
        assert response.status_code == 200
        assert response.json()["is_feasible"] is False
        assert response.json()["status"] == "INFEASIBLE"
        assert response.json()["rejection_reason_code"] == "REJECTED_TEST"
    finally:
        user_repository.clear_mock_profiles()
