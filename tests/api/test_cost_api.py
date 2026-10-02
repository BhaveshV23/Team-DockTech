from datetime import date, datetime, timezone
from decimal import Decimal
import os
import sys
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from fastapi import HTTPException

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.core.config import settings
from app.repositories.user_repository import user_repository
from main import app
from backend.app.domain.cost.errors import InsufficientFuelPriceDataError
from backend.app.domain.cost.models import FreightUnit
from backend.app.repositories.reference_repository import SupabaseCostReferenceRepository
from tests.auth_test_utils import TEST_SUPABASE_URL, supabase_test_token


TEST_JWT_SECRET = "docktech-test-jwt-secret-key-32-bytes-long"
settings.SUPABASE_JWT_SECRET = TEST_JWT_SECRET
settings.SUPABASE_URL = TEST_SUPABASE_URL
client = TestClient(app)


def _authenticated_headers():
    user_id = uuid4()
    auth_user_id = uuid4()
    now = datetime.now(timezone.utc).isoformat()
    profile = {
        "user_id": str(user_id),
        "auth_user_id": str(auth_user_id),
        "display_name": "Cost Test User",
        "email": "cost_user@docktech.com",
        "role": "PLANNER",
        "created_at": now,
        "updated_at": now,
    }
    user_repository.add_mock_profile(profile)
    token = supabase_test_token(
        TEST_JWT_SECRET, {"sub": str(auth_user_id), "email": profile["email"]}
    )
    return {"Authorization": f"Bearer {token}"}, profile


def _payload(cargo_id=None, forecast_id=None):
    return {
        "cargo_request_id": str(cargo_id or uuid4()),
        "forecast_run_id": str(forecast_id or uuid4()),
        "scenario_delay_hours": "0",
        "freight_adjustment_pct": "0",
        "fuel_adjustment_pct": "0",
        "port_costs_usd": "0",
    }


def _cost_result(reference_date=date(2025, 12, 31)):
    return SimpleNamespace(
        required_voyages=2,
        sailing_days_per_voyage=Decimal("3"),
        origin_handling_hours_total=Decimal("10"),
        dest_handling_hours_total=Decimal("12"),
        waiting_hours_total=Decimal("4"),
        scenario_delay_hours_total=Decimal("0"),
        estimated_turnaround_hours=Decimal("26"),
        port_days_per_voyage=Decimal("0.5"),
        vessel_days_per_voyage=Decimal("3.5"),
        vlsfo_price_used=Decimal("600"),
        total_fuel_consumption_mt=Decimal("10"),
        total_fuel_cost_usd=Decimal("6000"),
        freight_rate_used=Decimal("20"),
        freight_unit=FreightUnit.USD_PER_MT,
        expected_freight_cost=Decimal("1000000"),
        port_costs_usd=Decimal("0"),
        expected_total_cost=Decimal("1006000"),
        effective_cost_per_mt=Decimal("20.12"),
        cost_reference_date=reference_date,
        assumptions=("canonical test assumptions",),
    )


class _FakeEngine:
    def __init__(self, result=None, error=None):
        self.repository = SimpleNamespace(
            get_route=lambda **kwargs: SimpleNamespace(route_id="ROUTE_NCL_PAR")
        )
        self.result = result or _cost_result()
        self.error = error
        self.call = None

    def calculate(self, **kwargs):
        self.call = kwargs
        if self.error:
            raise self.error
        return self.result


def _configure_context(cost_api, profile, *, linked_cargo=True, route_matches=True, engine=None):
    cargo_id = uuid4()
    forecast_id = uuid4()
    cost_api.cost_service.cargo_access_service = SimpleNamespace(
        get_cargo_request=lambda _id, _profile: SimpleNamespace(
            cargo_request_id=cargo_id,
            user_id=profile["user_id"],
            cargo_volume_mt=75000,
            origin_port_id="NEWCASTLE",
            destination_port_id="PARADIP",
            commodity="THERMAL_COAL",
        )
    )
    cost_api.cost_service.forecast_repo = SimpleNamespace(
        get_forecast_run=lambda _id: {
            "forecast_run_id": str(forecast_id),
            "cargo_request_id": str(cargo_id if linked_cargo else uuid4()),
            "route_id": "ROUTE_NCL_PAR" if route_matches else "OTHER_ROUTE",
            "vessel_class_id": "PANAMAX",
            "freight_unit": "USD_PER_MT",
            "training_data_end_date": "2025-12-31",
        }
    )
    cost_api.cost_service.engine = engine or _FakeEngine()
    return cargo_id, forecast_id


def test_cost_api_requires_authentication():
    response = client.post("/api/v1/cost", json=_payload())
    assert response.status_code == 401


def test_cost_api_rejects_client_supplied_reference_date():
    headers, _ = _authenticated_headers()
    try:
        response = client.post(
            "/api/v1/cost",
            json={**_payload(), "cost_reference_date": "2000-01-01"},
            headers=headers,
        )
        assert response.status_code == 422
    finally:
        user_repository.clear_mock_profiles()


def test_cost_api_derives_date_and_inputs_from_cargo_and_forecast():
    headers, profile = _authenticated_headers()
    import app.api.v1.cost as cost_api

    try:
        cargo_id, forecast_id = _configure_context(cost_api, profile)
        response = client.post(
            "/api/v1/cost", json=_payload(cargo_id, forecast_id), headers=headers
        )
        assert response.status_code == 200
        assert response.json()["cost_reference_date"] == "2025-12-31"
        call = cost_api.cost_service.engine.call
        assert call["cargo_volume_mt"] == Decimal("75000")
        assert call["origin_port_id"] == "NEWCASTLE"
        assert call["destination_port_id"] == "PARADIP"
        assert call["vessel_class_id"] == "PANAMAX"
        assert call["freight_unit"] is FreightUnit.USD_PER_MT
        assert call["cost_reference_date"] == date(2025, 12, 31)
    finally:
        user_repository.clear_mock_profiles()


def test_cost_api_uses_first_chronological_forecast_rate_server_side():
    headers, profile = _authenticated_headers()
    import app.api.v1.cost as cost_api

    try:
        cargo_id, forecast_id = _configure_context(cost_api, profile)
        cost_api.cost_service.forecast_repo.get_forecast_points = lambda _id: [
            {"forecast_date": "2026-02-01", "central_value": "17.5", "unit": "USD_PER_MT"},
            {"forecast_date": "2026-01-01", "central_value": "15.25", "unit": "USD_PER_MT"},
        ]
        response = client.post(
            "/api/v1/cost",
            json={**_payload(cargo_id, forecast_id), "use_forecast_central_rate": True},
            headers=headers,
        )
        assert response.status_code == 200
        assert cost_api.cost_service.engine.call["freight_rate_override"] == Decimal("15.25")
    finally:
        user_repository.clear_mock_profiles()


def test_cost_api_rejects_forecast_for_different_cargo_or_route():
    headers, profile = _authenticated_headers()
    import app.api.v1.cost as cost_api

    try:
        cargo_id, forecast_id = _configure_context(cost_api, profile, linked_cargo=False)
        response = client.post(
            "/api/v1/cost", json=_payload(cargo_id, forecast_id), headers=headers
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "ERROR_COST_CONTEXT_INVALID"

        cargo_id, forecast_id = _configure_context(cost_api, profile, route_matches=False)
        response = client.post(
            "/api/v1/cost", json=_payload(cargo_id, forecast_id), headers=headers
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "ERROR_COST_CONTEXT_INVALID"
    finally:
        user_repository.clear_mock_profiles()


def test_cost_api_maps_missing_reference_data_to_structured_error():
    headers, profile = _authenticated_headers()
    import app.api.v1.cost as cost_api

    try:
        cargo_id, forecast_id = _configure_context(
            cost_api,
            profile,
            engine=_FakeEngine(error=InsufficientFuelPriceDataError("no price")),
        )
        response = client.post(
            "/api/v1/cost", json=_payload(cargo_id, forecast_id), headers=headers
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "ERROR_INSUFFICIENT_FUEL_PRICE_DATA"
        assert isinstance(cost_api.cost_reference_repository, SupabaseCostReferenceRepository)
    finally:
        user_repository.clear_mock_profiles()


def test_cost_api_maps_cargo_storage_failure_to_structured_503():
    headers, profile = _authenticated_headers()
    import app.api.v1.cost as cost_api

    def fail_cargo_lookup(_cargo_id, _profile):
        raise HTTPException(
            status_code=503,
            detail="Cargo request storage is unavailable",
        )

    try:
        cost_api.cost_service.cargo_access_service = SimpleNamespace(
            get_cargo_request=fail_cargo_lookup
        )
        response = client.post("/api/v1/cost", json=_payload(), headers=headers)
        assert response.status_code == 503
        assert response.json()["detail"] == {
            "code": "ERROR_COST_DATA_UNAVAILABLE",
            "message": "Cost data is unavailable",
        }
    finally:
        user_repository.clear_mock_profiles()
