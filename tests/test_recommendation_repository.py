from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from backend.app.domain.constants import ContractStrategy, MarketEntryAction, RiskLevel
from backend.app.domain.recommendation.models import RecommendationConfidence, RecommendationResult
from backend.app.repositories import recommendation_repository as repository_module
from backend.app.repositories.recommendation_repository import (
    InvalidRecommendationError,
    RecommendationPersistenceError,
    RecommendationProvenanceError,
    RecommendationRepository,
)


CARGO_ID = UUID("10000000-0000-0000-0000-000000000001")
FORECAST_ID = UUID("20000000-0000-0000-0000-000000000002")
RECOMMENDATION_ID = UUID("30000000-0000-0000-0000-000000000003")


def recommendation() -> RecommendationResult:
    return RecommendationResult(
        recommendation_id=RECOMMENDATION_ID,
        cargo_request_id=CARGO_ID,
        forecast_run_id=FORECAST_ID,
        recommended_vessel_class_id="PANAMAX",
        market_entry_action=MarketEntryAction.WAIT,
        contract_strategy=ContractStrategy.SHORT_TERM_MULTIPLE_VOYAGE,
        expected_freight_cost=Decimal("12345.6789001"),
        expected_total_cost=Decimal("98765.4321009"),
        estimated_turnaround_hours=Decimal("73.25"),
        risk_level=RiskLevel.HIGH,
        confidence=RecommendationConfidence.MEDIUM,
        rationale="Falling forecast with contained risk and delivery time.",
        assumptions="Canonical freight, fuel and port observations are used.",
        created_at=datetime(2026, 2, 3, 4, 5, 6, 123456, tzinfo=timezone.utc),
        trend="FALLING",
        forecast_uncertainty=(Decimal("10"), Decimal("12"), Decimal("14")),
        required_voyages=2,
    )


class Response:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.payload = payload

    def json(self):
        return self.payload


class FakeSupabaseClient:
    state = None

    def __init__(self, timeout=None):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, *, headers, params):
        table = url.rsplit("/", 1)[-1]
        self.state["gets"].append((table, params))
        if table == "cargo_requests":
            row = {
                "cargo_request_id": str(CARGO_ID),
                "origin_port_id": "NEWCASTLE",
                "destination_port_id": "PARADIP",
                "commodity": "THERMAL_COAL",
            }
        elif table == "forecast_runs":
            row = {
                "forecast_run_id": str(FORECAST_ID),
                "cargo_request_id": str(CARGO_ID),
                "route_id": "R1",
                "vessel_class_id": "PANAMAX",
            }
            if self.state.get("forecast_override"):
                row.update(self.state["forecast_override"])
        elif table == "routes":
            row = {
                "route_id": "R1",
                "origin_port_id": "NEWCASTLE",
                "destination_port_id": "PARADIP",
                "commodity": "THERMAL_COAL",
            }
            if self.state.get("route_override"):
                row.update(self.state["route_override"])
        else:
            return Response(404, {"message": "unknown table"})
        return Response(200, [row])

    def post(self, url, *, headers, json):
        self.state["posts"].append((url, headers, json))
        if self.state.get("post_status", 201) >= 300:
            return Response(self.state["post_status"], {"message": "insert failed"})
        if self.state.get("insert_response") is not None:
            return Response(201, self.state["insert_response"])
        return Response(201, [dict(json)])


@pytest.fixture
def configured_repository(monkeypatch):
    state = {"gets": [], "posts": []}
    FakeSupabaseClient.state = state
    monkeypatch.setattr(repository_module.httpx, "Client", FakeSupabaseClient)
    repo = RecommendationRepository()
    repo.supabase_url = "https://supabase.test"
    repo.service_role_key = "service-role-test"
    return repo, state


def test_successful_persistence_posts_every_frozen_field(configured_repository):
    repo, state = configured_repository
    saved = repo.create(recommendation())

    assert len(state["gets"]) == 3
    assert [table for table, _ in state["gets"]] == [
        "cargo_requests", "forecast_runs", "routes"
    ]
    assert len(state["posts"]) == 1
    url, headers, payload = state["posts"][0]
    assert url == "https://supabase.test/rest/v1/recommendations"
    assert headers["Prefer"] == "return=representation"
    assert set(payload) == set(repo.FROZEN_FIELDS)
    assert payload == {
        "recommendation_id": str(RECOMMENDATION_ID),
        "cargo_request_id": str(CARGO_ID),
        "forecast_run_id": str(FORECAST_ID),
        "recommended_vessel_class_id": "PANAMAX",
        "market_entry_action": "WAIT",
        "contract_strategy": "SHORT_TERM_MULTIPLE_VOYAGE",
        "expected_freight_cost": "12345.6789001",
        "expected_total_cost": "98765.4321009",
        "estimated_turnaround_hours": "73.25",
        "risk_level": "HIGH",
        "confidence": "MEDIUM",
        "rationale": "Falling forecast with contained risk and delivery time.",
        "assumptions": "Canonical freight, fuel and port observations are used.",
        "created_at": "2026-02-03T04:05:06.123456+00:00",
    }
    assert saved == payload


@pytest.mark.parametrize(
    "forecast_override",
    [
        {"cargo_request_id": str(UUID(int=55))},
        {"vessel_class_id": "CAPE"},
        {"route_id": "OTHER"},
    ],
)
def test_forecast_cargo_route_or_vessel_mismatch_rejected_before_insert(
    configured_repository, forecast_override
):
    repo, state = configured_repository
    state["forecast_override"] = forecast_override
    with pytest.raises(RecommendationProvenanceError):
        repo.create(recommendation())
    assert not state["posts"]


def test_resolved_route_must_match_cargo(configured_repository):
    repo, state = configured_repository
    state["route_override"] = {"destination_port_id": "VIZAG"}
    with pytest.raises(RecommendationProvenanceError):
        repo.create(recommendation())
    assert not state["posts"]


@pytest.mark.parametrize(
    "changes",
    [
        {"expected_total_cost": None},
        {"expected_freight_cost": Decimal("NaN")},
        {"estimated_turnaround_hours": Decimal("0")},
        {"rationale": "  "},
        {"assumptions": None},
        {"created_at": datetime(2026, 2, 3)},
        {"recommended_vessel_class_id": ""},
        {"market_entry_action": "WAIT"},
    ],
)
def test_invalid_or_missing_required_data_rejected_before_insert(configured_repository, changes):
    repo, state = configured_repository
    with pytest.raises(InvalidRecommendationError):
        repo.create(replace(recommendation(), **changes))
    assert not state["gets"]
    assert not state["posts"]


def test_persistence_failure_is_reported_without_success_result(configured_repository):
    repo, state = configured_repository
    state["post_status"] = 500
    with pytest.raises(RecommendationPersistenceError):
        repo.create(recommendation())
    assert len(state["posts"]) == 1


def test_incomplete_insert_confirmation_is_rejected(configured_repository):
    repo, state = configured_repository
    state["insert_response"] = []
    with pytest.raises(RecommendationPersistenceError):
        repo.create(recommendation())
