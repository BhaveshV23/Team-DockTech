from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user_profile
from main import app


client = TestClient(app)


def test_provenance_requires_authentication():
    app.dependency_overrides.pop(get_current_user_profile, None)
    response = client.get("/api/v1/provenance")
    assert response.status_code == 401


def test_provenance_exposes_existing_seed_metadata():
    app.dependency_overrides[get_current_user_profile] = lambda: {
        "user_id": "11111111-1111-4111-8111-111111111111",
        "auth_user_id": "22222222-2222-4222-8222-222222222222",
        "display_name": "Test User",
        "email": "test@example.com",
        "role": "VIEWER",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    try:
        response = client.get("/api/v1/provenance")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["generator_name"] == "DockTech Synthetic Generator"
    assert data["history_start_date"] == "2024-01-01"
    assert data["history_end_date"] == "2025-12-31"
    datasets = {dataset["dataset"]: dataset for dataset in data["datasets"]}
    assert len(datasets) == 9
    freight = datasets["freight_rates"]
    assert freight["provenance"] == [
        {"source": "SYNTHETIC_GENERATOR_V1", "data_type": "SYNTHETIC"}
    ]
    assert freight["date_start"] == "2024-01-01"
    assert freight["date_end"] == "2025-12-31"
    assert freight["units"] == ["USD_PER_DAY", "USD_PER_MT"]
    assert datasets["vessel_classes"]["provenance"] == [
        {"source": "SYNTHETIC_GENERATOR_V1", "data_type": "SYNTHETIC"}
    ]
