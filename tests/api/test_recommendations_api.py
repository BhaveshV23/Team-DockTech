"""HTTP contract tests for the recommendation endpoint."""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
from uuid import uuid4

from fastapi.testclient import TestClient

backend_path = str(Path(__file__).resolve().parents[2] / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from backend.app.core.dependencies import get_current_user_profile
from backend.app.domain.constants import ContractStrategy, MarketEntryAction, RiskLevel
from backend.app.domain.recommendation.errors import NoFeasibleVesselError
from backend.app.domain.recommendation.models import RecommendationConfidence, RecommendationResult
from backend.app.main import app
from backend.app.schemas.auth import UserProfileResponse
from backend.app.api.v1.recommendations import get_recommendation_service

client = TestClient(app)


def _profile(role="PLANNER"):
    return UserProfileResponse(
        user_id=uuid4(), auth_user_id=uuid4(), display_name="Planner",
        email="planner@example.test", role=role,
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
    )


def _result(cargo_id):
    return RecommendationResult(
        recommendation_id=uuid4(), cargo_request_id=cargo_id, forecast_run_id=uuid4(),
        recommended_vessel_class_id="PANAMAX", market_entry_action=MarketEntryAction.FIX_NOW,
        contract_strategy=ContractStrategy.SPOT, expected_freight_cost=Decimal("1200.25"),
        expected_total_cost=Decimal("1500.50"), estimated_turnaround_hours=Decimal("72"),
        risk_level=RiskLevel.MEDIUM, confidence=RecommendationConfidence.HIGH,
        rationale="Lowest cost per MT with acceptable risk.", assumptions="Canonical forecast evidence.",
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc), trend="FLAT",
        forecast_uncertainty=(Decimal("1"), Decimal("2"), Decimal("3")), required_voyages=1,
    )


class ServiceDouble:
    def __init__(self, *, failure=None):
        self.failure = failure
        self.calls = []

    def recommend(self, **kwargs):
        self.calls.append(kwargs)
        if self.failure:
            raise self.failure
        return _result(kwargs["cargo_request_id"])


def _set_overrides(profile=None, service=None):
    app.dependency_overrides.clear()
    if profile is not None:
        app.dependency_overrides[get_current_user_profile] = lambda: profile
    if service is not None:
        app.dependency_overrides[get_recommendation_service] = lambda: service


def test_post_recommendation_returns_all_frozen_fields_and_delegates():
    profile = _profile()
    service = ServiceDouble()
    _set_overrides(profile, service)
    cargo_id = uuid4()
    try:
        response = client.post("/api/v1/recommendations", json={"cargo_request_id": str(cargo_id)})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()["data"]
    assert set(data) == {
        "recommendation_id", "cargo_request_id", "forecast_run_id", "recommended_vessel_class_id",
        "market_entry_action", "contract_strategy", "expected_freight_cost", "expected_total_cost",
        "estimated_turnaround_hours", "risk_level", "confidence", "rationale", "assumptions", "created_at",
    }
    assert data["market_entry_action"] == "FIX_NOW"
    assert data["contract_strategy"] == "SPOT"
    assert data["cargo_request_id"] == str(cargo_id)
    assert service.calls[0]["user_profile"] == profile


def test_post_recommendation_requires_authentication():
    _set_overrides()
    try:
        response = client.post("/api/v1/recommendations", json={"cargo_request_id": str(uuid4())})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401


def test_post_recommendation_rejects_unauthorized_role():
    service = ServiceDouble()
    _set_overrides(_profile("VIEWER"), service)
    try:
        response = client.post("/api/v1/recommendations", json={"cargo_request_id": str(uuid4())})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 403
    assert not service.calls


def test_post_recommendation_rejects_invalid_request():
    _set_overrides(_profile(), ServiceDouble())
    try:
        response = client.post("/api/v1/recommendations", json={
            "cargo_request_id": "not-a-uuid", "unexpected": True,
        })
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422


def test_post_recommendation_maps_service_domain_failure():
    _set_overrides(_profile(), ServiceDouble(failure=NoFeasibleVesselError("No feasible vessel")))
    try:
        response = client.post("/api/v1/recommendations", json={"cargo_request_id": str(uuid4())})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "ERROR_RECOMMENDATION_INVALID"
