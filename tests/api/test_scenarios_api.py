"""API tests for DockTech V1 scenario endpoints."""

from uuid import uuid4
from fastapi.testclient import TestClient
import pytest

from backend.app.main import app

client = TestClient(app)


def test_api_get_scenario_defaults():
    """GET /api/v1/scenarios/defaults returns 200 OK and 3 canonical presets."""
    response = client.get("/api/v1/scenarios/defaults")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    presets = data["data"]
    assert len(presets) == 3
    ids = [p["scenario_id"] for p in presets]
    assert "BASELINE" in ids
    assert "ADVERSE" in ids
    assert "FAVORABLE" in ids


def test_api_run_canonical_scenarios():
    """POST /api/v1/scenarios/run-canonical returns BASELINE, ADVERSE, FAVORABLE."""
    payload = {
        "cargo_request_id": str(uuid4()),
        "commodity": "THERMAL_COAL",
        "cargo_volume_mt": 75000.0,
        "vessel_class_id": "PANAMAX",
        "speed_knots": 13.0,
        "cargo_capacity_mt": 75000.0,
        "fuel_consumption_mt_day": 28.0,
        "origin_berth_handling_rate_tpd": 50000.0,
        "destination_berth_handling_rate_tpd": 30000.0,
        "distance_nm": 5600.0,
        "base_freight_rate": 18.50,
        "freight_unit": "USD_PER_MT",
        "base_vlsfo_price_usd_mt": 620.0,
        "origin_waiting_hours": 12.0,
        "destination_waiting_hours": 36.0,
        "forecast_spread_pct": 8.0,
    }
    response = client.post("/api/v1/scenarios/run-canonical", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    sc_set = data["data"]
    assert sc_set["baseline"]["scenario_type"] == "BASELINE"
    assert sc_set["adverse"]["scenario_type"] == "ADVERSE"
    assert sc_set["favorable"]["scenario_type"] == "FAVORABLE"
    assert sc_set["adverse"]["freight_change_pct"] == 25.0
    assert sc_set["adverse"]["delay_hours"] == 48.0


def test_api_evaluate_custom_scenario():
    """POST /api/v1/scenarios/evaluate returns comparison with baseline."""
    payload = {
        "cargo_request_id": str(uuid4()),
        "commodity": "THERMAL_COAL",
        "cargo_volume_mt": 75000.0,
        "vessel_class_id": "PANAMAX",
        "speed_knots": 13.0,
        "cargo_capacity_mt": 75000.0,
        "fuel_consumption_mt_day": 28.0,
        "origin_berth_handling_rate_tpd": 50000.0,
        "destination_berth_handling_rate_tpd": 30000.0,
        "distance_nm": 5600.0,
        "base_freight_rate": 18.50,
        "freight_unit": "USD_PER_MT",
        "base_vlsfo_price_usd_mt": 620.0,
        "origin_waiting_hours": 12.0,
        "destination_waiting_hours": 36.0,
        "freight_change_pct": 20.0,
        "fuel_change_pct": 10.0,
        "delay_hours": 24.0,
        "congestion_level": "HIGH",
        "forecast_spread_pct": 15.0,
    }
    response = client.post("/api/v1/scenarios/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    comparison = data["data"]
    assert comparison["delta_cost_usd"] > 0
    assert comparison["delta_turnaround_hours"] == 24.0
    assert comparison["scenario_result"]["risk_level"] == "HIGH"


def test_api_invalid_request_returns_422():
    """POST /api/v1/scenarios/evaluate with invalid cargo volume returns 422."""
    payload = {
        "cargo_request_id": str(uuid4()),
        "commodity": "THERMAL_COAL",
        "cargo_volume_mt": -500.0,  # Invalid negative volume
        "vessel_class_id": "PANAMAX",
        "speed_knots": 13.0,
        "cargo_capacity_mt": 75000.0,
        "fuel_consumption_mt_day": 28.0,
        "origin_berth_handling_rate_tpd": 50000.0,
        "destination_berth_handling_rate_tpd": 30000.0,
        "distance_nm": 5600.0,
        "base_freight_rate": 18.50,
        "freight_unit": "USD_PER_MT",
        "base_vlsfo_price_usd_mt": 620.0,
        "origin_waiting_hours": 12.0,
        "destination_waiting_hours": 36.0,
    }
    response = client.post("/api/v1/scenarios/evaluate", json=payload)
    assert response.status_code == 422
