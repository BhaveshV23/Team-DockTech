from datetime import date, datetime, timezone
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import sys
from types import SimpleNamespace
from uuid import UUID

import pytest

backend_path = str(Path(__file__).resolve().parents[1] / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from backend.app.domain.constants import (
    Commodity,
    FeasibilityStatus,
    RiskLevel,
    ScenarioType,
)
from backend.app.domain.entities import Route, VesselClass
from backend.app.domain.recommendation.errors import (
    InconsistentRecommendationEvidenceError,
    MissingRecommendationEvidenceError,
    NoFeasibleVesselError,
)
from backend.app.domain.recommendation.models import RecommendationConfidence
from backend.app.domain.recommendation.engine import RecommendationEngine
from backend.app.domain.cost.models import FreightUnit
from backend.app.schemas.auth import UserProfileResponse
from backend.app.services.recommendation_service import RecommendationService
from backend.app.repositories.recommendation_repository import RecommendationPersistenceError


def uid(value: int) -> UUID:
    return UUID(int=value)


def make_cargo():
    return SimpleNamespace(
        cargo_request_id=uid(1),
        user_id=uid(2),
        commodity="THERMAL_COAL",
        cargo_volume_mt=150.0,
        origin_port_id="P1",
        destination_port_id="P2",
        earliest_delivery_date=date(2026, 1, 1),
        latest_delivery_date=date(2026, 1, 12),
        contract_horizon="SPOT",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def make_vessel(vessel_id: str, capacity: float):
    return VesselClass(
        vessel_class_id=vessel_id,
        vessel_class_name=vessel_id,
        dwt_min_mt=100,
        dwt_max_mt=1000,
        loa_m=100,
        beam_m=20,
        draft_m=10,
        speed_knots=12,
        cargo_capacity_mt=capacity,
        fuel_consumption_mt_day=20,
    )


class CargoAccess:
    def get_cargo_request(self, cargo_id, user_profile):
        assert cargo_id == uid(1)
        assert user_profile.user_id == uid(2)
        return make_cargo()


class Routes:
    def get_by_origin_dest_commodity(self, origin, destination, commodity):
        assert (origin, destination, commodity) == ("P1", "P2", "THERMAL_COAL")
        return Route("R1", origin, destination, commodity, 1200, 4)


class Vessels:
    def __init__(self, vessels=None):
        self.vessels = vessels or [make_vessel("V1", 100), make_vessel("V2", 200)]

    def get_all(self):
        return list(self.vessels)


class Feasibility:
    def __init__(self, rejected=()):
        self.rejected = set(rejected)
        self.calls = []

    def check_feasibility_multiple(self, **kwargs):
        self.calls.append(kwargs)
        return [
            SimpleNamespace(
                vessel_class_id=vessel_id,
                status=(FeasibilityStatus.INFEASIBLE if vessel_id in self.rejected else FeasibilityStatus.FEASIBLE),
                is_feasible=vessel_id not in self.rejected,
                origin_port_id=kwargs["origin_port_id"],
                destination_port_id=kwargs["destination_port_id"],
                commodity=kwargs["commodity"],
                cargo_volume_mt=kwargs["cargo_volume_mt"],
                required_voyages=(None if vessel_id in self.rejected else (2 if vessel_id == "V1" else 1)),
            )
            for vessel_id in kwargs["vessel_class_ids"]
        ]


class Forecasts:
    def __init__(self, *, missing_for=(), mismatch_for=None):
        self.missing_for = set(missing_for)
        self.mismatch_for = mismatch_for
        self.calls = []
        self.results_by_vessel = {}

    def create_forecast(self, **kwargs):
        self.calls.append(kwargs)
        vessel_id = kwargs["vessel_class_id"]
        if vessel_id in self.missing_for:
            return {"forecast_run": {}, "forecast_points": []}
        run_id = uid(10 + sum(vessel_id.encode()))
        run = {
            "forecast_run_id": str(run_id),
            "cargo_request_id": str(uid(999) if self.mismatch_for == "cargo" else kwargs["cargo_request_id"]),
            "route_id": "OTHER" if self.mismatch_for == "route" and vessel_id == "V1" else kwargs["route_id"],
            "vessel_class_id": "OTHER" if self.mismatch_for == "vessel" and vessel_id == "V1" else vessel_id,
            "freight_unit": kwargs["freight_unit"],
            "training_data_end_date": "2025-12-31",
        }
        result = {
            "forecast_run": run,
            # Deliberately descending; service normalizes to chronological order.
            "forecast_points": [
                {
                    "forecast_run_id": str(run_id),
                    "forecast_date": "2026-01-02",
                    "lower_value": 11,
                    "central_value": 12,
                    "upper_value": 13,
                    "unit": kwargs["freight_unit"],
                },
                {
                    "forecast_run_id": str(run_id),
                    "forecast_date": "2026-01-01",
                    "lower_value": 9,
                    "central_value": 10,
                    "upper_value": 11,
                    "unit": kwargs["freight_unit"],
                },
            ],
        }
        self.results_by_vessel[vessel_id] = result
        return result


class Costs:
    def __init__(self, *, missing=False, mismatch_unit=False):
        self.missing = missing
        self.mismatch_unit = mismatch_unit
        self.calls = []

    def calculate(self, **kwargs):
        self.calls.append(kwargs)
        if self.missing:
            return None
        return SimpleNamespace(
            freight_unit=(FreightUnit.USD_PER_DAY if self.mismatch_unit else kwargs["freight_unit"]),
            freight_rate_used=kwargs["freight_rate_override"],
            cost_reference_date=kwargs["cost_reference_date"],
            expected_freight_cost=Decimal("400"),
            expected_total_cost=Decimal("500"),
            effective_cost_per_mt=Decimal("3" if kwargs["vessel_class_id"] == "V2" else "4"),
            estimated_turnaround_hours=Decimal("48"),
            sailing_days_per_voyage=Decimal("4"),
            required_voyages=(2 if kwargs["vessel_class_id"] == "V1" else 1),
        )

    def calculate_with_context(self, **kwargs):
        result = self.calculate(**kwargs)
        context = SimpleNamespace(
            vessel_class_id=kwargs["vessel_class_id"],
            cost_reference_date=kwargs["cost_reference_date"],
            freight_rate=kwargs["freight_rate_override"],
        )
        return result, context


class Scenarios:
    def __init__(self, *, missing=False, mismatch=False):
        self.missing = missing
        self.mismatch = mismatch
        self.calls = []

    def run_canonical_for_cargo(
        self, cargo_id, forecast_run_id, user_profile, *, forecast_run, forecast_points, cost_context
    ):
        self.calls.append((cargo_id, forecast_run_id, user_profile, forecast_run, forecast_points, cost_context))
        if self.missing:
            return None
        results = [
            SimpleNamespace(
                scenario_type=scenario,
                risk_level=RiskLevel.LOW,
                cargo_request_id=uid(999) if self.mismatch else cargo_id,
            )
            for scenario in (ScenarioType.BASELINE, ScenarioType.ADVERSE, ScenarioType.FAVORABLE)
        ]
        return SimpleNamespace(baseline=results[0], adverse=results[1], favorable=results[2])


@pytest.fixture
def user_profile():
    return UserProfileResponse(
        user_id=uid(2),
        auth_user_id=uid(3),
        display_name="Planner",
        email="planner@example.test",
        role="PLANNER",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


class RecommendationStore:
    def __init__(self, *, fail=False, transform=None):
        self.fail = fail
        self.transform = transform
        self.calls = []

    def create(self, result):
        self.calls.append(result)
        if self.fail:
            raise RecommendationPersistenceError("storage failed")
        row = {
            "recommendation_id": str(result.recommendation_id),
            "cargo_request_id": str(result.cargo_request_id),
            "forecast_run_id": str(result.forecast_run_id),
            "recommended_vessel_class_id": result.recommended_vessel_class_id,
            "market_entry_action": result.market_entry_action.value,
            "contract_strategy": result.contract_strategy.value,
            "expected_freight_cost": str(result.expected_freight_cost),
            "expected_total_cost": str(result.expected_total_cost),
            "estimated_turnaround_hours": str(result.estimated_turnaround_hours),
            "risk_level": result.risk_level.value,
            "confidence": result.confidence.value,
            "rationale": result.rationale,
            "assumptions": result.assumptions,
            "created_at": result.created_at.isoformat(),
        }
        return self.transform(row) if self.transform else row


def make_service(*, rejected=(), missing_forecast=(), missing_cost=False,
                 missing_scenario=False, forecast_mismatch=None, cost_mismatch=False,
                 scenario_mismatch=False, vessel_list=None, repository=None, engine=RecommendationEngine):
    feasibility = Feasibility(rejected=rejected)
    forecasts = Forecasts(missing_for=missing_forecast, mismatch_for=forecast_mismatch)
    costs = Costs(missing=missing_cost, mismatch_unit=cost_mismatch)
    scenarios = Scenarios(missing=missing_scenario, mismatch=scenario_mismatch)
    service = RecommendationService(
        cargo_access_service=CargoAccess(),
        route_repository=Routes(),
        vessel_repository=Vessels(vessel_list),
        feasibility_service=feasibility,
        forecast_service=forecasts,
        cost_engine=costs,
        scenario_service=scenarios,
        recommendation_repository=repository or RecommendationStore(),
        recommendation_engine=engine,
    )
    return service, feasibility, forecasts, costs, scenarios


def test_recommendation_is_persisted_after_success_and_returned_from_saved_row(user_profile):
    store = RecommendationStore()
    service, _, _, _, _ = make_service(repository=store)
    result = recommend(service, user_profile)
    assert len(store.calls) == 1
    assert result == store.calls[0]
    assert result.recommended_vessel_class_id == "V2"
    assert result.forecast_run_id == uid(10 + sum(b"V2"))


def test_repository_failure_propagates(user_profile):
    store = RecommendationStore(fail=True)
    service, _, _, _, _ = make_service(repository=store)
    with pytest.raises(RecommendationPersistenceError):
        recommend(service, user_profile)
    assert len(store.calls) == 1


def test_engine_or_validation_failure_does_not_persist(user_profile):
    store = RecommendationStore()

    class InvalidEngine:
        @staticmethod
        def recommend(request):
            result = RecommendationEngine.recommend(request)
            return replace(result, forecast_run_id=uid(888))

    service, _, _, _, _ = make_service(repository=store, engine=InvalidEngine)
    with pytest.raises(InconsistentRecommendationEvidenceError):
        recommend(service, user_profile)
    assert not store.calls


def recommend(service, user_profile):
    return service.recommend(
        uid(1), user_profile, forecast_horizon=30, freight_unit=FreightUnit.USD_PER_MT
    )


def test_successful_orchestration_resolves_inputs_and_returns_engine_result(user_profile):
    service, feasibility, forecasts, costs, scenarios = make_service()
    result = recommend(service, user_profile)
    assert result.recommended_vessel_class_id == "V2"
    assert result.forecast_run_id == uid(10 + sum(b"V2"))
    assert result.confidence == RecommendationConfidence.HIGH
    assert len(feasibility.calls) == 1
    assert len(forecasts.calls) == len(costs.calls) == len(scenarios.calls) == 2
    assert [call["vessel_class_id"] for call in forecasts.calls] == ["V1", "V2"]
    assert all(call["freight_rate_override"] == Decimal("10") for call in costs.calls)
    for cargo_id, run_id, profile, supplied_run, supplied_points, context in scenarios.calls:
        vessel_id = supplied_run["vessel_class_id"]
        created = forecasts.results_by_vessel[vessel_id]
        assert (cargo_id, run_id, profile) == (uid(1), UUID(created["forecast_run"]["forecast_run_id"]), user_profile)
        assert supplied_run == created["forecast_run"]
        assert supplied_points == created["forecast_points"]
        assert context.vessel_class_id == vessel_id
        assert context.freight_rate == Decimal("10")


def test_infeasible_candidate_skips_forecast_cost_and_scenarios(user_profile):
    service, _, forecasts, costs, scenarios = make_service(rejected={"V1"})
    result = recommend(service, user_profile)
    assert result.recommended_vessel_class_id == "V2"
    assert [call["vessel_class_id"] for call in forecasts.calls] == ["V2"]
    assert [call["vessel_class_id"] for call in costs.calls] == ["V2"]
    assert len(scenarios.calls) == 1


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"missing_forecast": {"V1"}}, MissingRecommendationEvidenceError),
        ({"missing_cost": True}, MissingRecommendationEvidenceError),
        ({"missing_scenario": True}, MissingRecommendationEvidenceError),
        ({"forecast_mismatch": "route"}, InconsistentRecommendationEvidenceError),
        ({"forecast_mismatch": "cargo"}, InconsistentRecommendationEvidenceError),
        ({"forecast_mismatch": "vessel"}, InconsistentRecommendationEvidenceError),
        ({"cost_mismatch": True}, InconsistentRecommendationEvidenceError),
        ({"scenario_mismatch": True}, InconsistentRecommendationEvidenceError),
    ],
)
def test_missing_or_inconsistent_evidence_fails(user_profile, kwargs, error):
    service, _, _, _, _ = make_service(**kwargs)
    with pytest.raises(error):
        recommend(service, user_profile)


def test_no_eligible_vessel_fails_without_cost_or_scenarios(user_profile):
    service, _, forecasts, costs, scenarios = make_service(rejected={"V1", "V2"})
    with pytest.raises(NoFeasibleVesselError):
        recommend(service, user_profile)
    assert not forecasts.calls
    assert not costs.calls
    assert not scenarios.calls


def test_unit_mismatch_in_forecast_points_fails(user_profile):
    service, _, forecasts, _, _ = make_service()
    original = forecasts.create_forecast

    def mismatched(**kwargs):
        response = original(**kwargs)
        response["forecast_points"][0]["unit"] = FreightUnit.USD_PER_DAY.value
        return response

    forecasts.create_forecast = mismatched
    with pytest.raises(InconsistentRecommendationEvidenceError):
        recommend(service, user_profile)
