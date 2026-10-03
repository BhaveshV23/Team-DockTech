"""Application orchestration for end-to-end V1 recommendations."""

from __future__ import annotations

from datetime import date, datetime, timezone
from dataclasses import replace
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from backend.app.core.timing import timed_stage
from backend.app.domain.constants import (
    Commodity,
    ContractStrategy,
    ContractHorizon,
    FeasibilityStatus,
    FreightUnit as DomainFreightUnit,
    MarketEntryAction,
    RiskLevel,
    ScenarioType,
)
from backend.app.domain.cost.models import FreightUnit as CostFreightUnit
from backend.app.domain.entities import Route
from backend.app.domain.recommendation.engine import RecommendationEngine
from backend.app.domain.recommendation.errors import (
    InconsistentRecommendationEvidenceError,
    MissingRecommendationEvidenceError,
)
from backend.app.domain.recommendation.models import (
    CandidateComparison,
    CandidateEvidence,
    CostEvidence,
    ForecastPointEvidence,
    ForecastRunEvidence,
    RecommendationInput,
    RecommendationConfidence,
    RecommendationResult,
    ScenarioRiskEvidence,
)
from backend.app.domain.recommendation.rules import worst_risk
from backend.app.repositories.reference_repository import SupabaseCostReferenceRepository
from backend.app.repositories.route_repository import RouteRepository
from backend.app.repositories.vessel_repository import VesselRepository
from backend.app.repositories.recommendation_repository import (
    recommendation_repository as default_recommendation_repository,
)
from backend.app.schemas.auth import UserProfileResponse
from backend.app.services.cargo_service import cargo_service
from backend.app.services.cost_service import CostEngineService
from backend.app.services.feasibility_service import FeasibilityService
from backend.app.services.forecast_service import forecast_application_service
from backend.app.services.scenario_service import ScenarioService


class RecommendationService:
    """Resolve canonical evidence, then delegate all decisions to the domain engine."""

    def __init__(
        self,
        cargo_access_service=None,
        route_repository=None,
        vessel_repository=None,
        feasibility_service=None,
        forecast_service=None,
        cost_engine=None,
        scenario_service=None,
        recommendation_engine=RecommendationEngine,
        recommendation_repository=None,
    ) -> None:
        self.cargo_access_service = cargo_access_service or cargo_service
        self.route_repository = route_repository or RouteRepository()
        self.vessel_repository = vessel_repository or VesselRepository()
        self.feasibility_service = feasibility_service or FeasibilityService()
        self.forecast_service = forecast_service or forecast_application_service
        self.cost_engine = cost_engine or CostEngineService(
            repository=SupabaseCostReferenceRepository()
        )
        self.scenario_service = scenario_service or ScenarioService()
        self.recommendation_engine = recommendation_engine
        self.recommendation_repository = recommendation_repository or default_recommendation_repository

    def recommend(
        self,
        cargo_request_id: UUID,
        user_profile: UserProfileResponse,
        *,
        forecast_horizon: int,
        freight_unit: CostFreightUnit | str,
    ) -> RecommendationResult:
        """Build complete candidate evidence for authorized cargo and return a decision."""
        with timed_stage("recommendation.cargo_access"):
            cargo = self.cargo_access_service.get_cargo_request(cargo_request_id, user_profile)
        if UUID(str(cargo.cargo_request_id)) != cargo_request_id:
            raise InconsistentRecommendationEvidenceError(
                "Cargo service returned a different cargo request"
            )

        commodity = Commodity(cargo.commodity)
        horizon = ContractHorizon(cargo.contract_horizon)
        cargo_volume_mt = Decimal(str(cargo.cargo_volume_mt))
        with timed_stage("recommendation.route_lookup"):
            route = self.route_repository.get_by_origin_dest_commodity(
                cargo.origin_port_id,
                cargo.destination_port_id,
                commodity.value,
            )
        if route is None:
            raise MissingRecommendationEvidenceError("No canonical route matches the cargo request")
        self._validate_route(route, cargo.origin_port_id, cargo.destination_port_id, commodity)

        cost_unit = CostFreightUnit.from_str(
            freight_unit.value if isinstance(freight_unit, CostFreightUnit) else freight_unit
        )
        with timed_stage("recommendation.vessel_reference_lookup"):
            candidates = self.vessel_repository.get_all()
        with timed_stage("recommendation.feasibility_batch", vessel_count=len(candidates)):
            feasibility_results = self.feasibility_service.check_feasibility_multiple(
                origin_port_id=cargo.origin_port_id,
                destination_port_id=cargo.destination_port_id,
                commodity=commodity.value,
                cargo_volume_mt=float(cargo_volume_mt),
                vessel_class_ids=[vessel.vessel_class_id for vessel in candidates],
            )
        result_by_vessel = {}
        for result in feasibility_results:
            if result.vessel_class_id in result_by_vessel:
                raise InconsistentRecommendationEvidenceError(
                    f"Duplicate feasibility result for {result.vessel_class_id}"
                )
            self._validate_feasibility(result, cargo, cargo_request_id, commodity, cargo_volume_mt)
            result_by_vessel[result.vessel_class_id] = result
        if set(result_by_vessel) != {vessel.vessel_class_id for vessel in candidates}:
            raise MissingRecommendationEvidenceError(
                "Feasibility did not return a result for every candidate vessel"
            )

        evidence_candidates = []
        for vessel in candidates:
            with timed_stage("recommendation.candidate_processing", vessel_class_id=vessel.vessel_class_id):
                feasibility = result_by_vessel[vessel.vessel_class_id]
                marked_feasible = feasibility.status == FeasibilityStatus.FEASIBLE
                if marked_feasible != feasibility.is_feasible:
                    raise InconsistentRecommendationEvidenceError(
                        f"Contradictory feasibility result for {vessel.vessel_class_id}"
                    )
                # Infeasible candidates are retained in result_by_vessel for
                # validation, but do not need forecast, cost, or scenario evidence.
                if not marked_feasible:
                    continue

                with timed_stage("recommendation.candidate_forecast", vessel_class_id=vessel.vessel_class_id):
                    forecast_result = self.forecast_service.create_forecast(
                        cargo_request_id=cargo_request_id,
                        route_id=route.route_id,
                        vessel_class_id=vessel.vessel_class_id,
                        freight_unit=cost_unit.value,
                        horizon=forecast_horizon,
                        user_profile=user_profile,
                    )
                run, points, candidate_reference_date = self._forecast_evidence(
                    forecast_result,
                    cargo_request_id=cargo_request_id,
                    route=route,
                    vessel_class_id=vessel.vessel_class_id,
                    freight_unit=cost_unit,
                )
                expected_rate = points[0].central_value
                with timed_stage("recommendation.candidate_cost", vessel_class_id=vessel.vessel_class_id):
                    cost_result, cost_context = self.cost_engine.calculate_with_context(
                        cargo_volume_mt=cargo_volume_mt,
                        origin_port_id=cargo.origin_port_id,
                        destination_port_id=cargo.destination_port_id,
                        commodity=commodity.value,
                        vessel_class_id=vessel.vessel_class_id,
                        freight_unit=cost_unit,
                        cost_reference_date=candidate_reference_date,
                        freight_rate_override=expected_rate,
                    )
                cost_evidence = self._cost_evidence(
                    cost_result,
                    cargo_request_id=cargo_request_id,
                    route=route,
                    vessel_class_id=vessel.vessel_class_id,
                    forecast_run=run,
                    forecast_rate=expected_rate,
                    freight_unit=cost_unit,
                    reference_date=candidate_reference_date,
                )

                with timed_stage("recommendation.candidate_scenarios", vessel_class_id=vessel.vessel_class_id):
                    scenario_set = self.scenario_service.run_canonical_for_cargo(
                        cargo_request_id,
                        run.forecast_run_id,
                        user_profile,
                        forecast_run=forecast_result["forecast_run"],
                        forecast_points=forecast_result["forecast_points"],
                        cost_context=cost_context,
                    )
                scenario_evidence = self._scenario_evidence(
                    scenario_set,
                    cargo_request_id=cargo_request_id,
                    route=route,
                    vessel_class_id=vessel.vessel_class_id,
                    forecast_run=run,
                )
                evidence_candidates.append(CandidateEvidence(
                    vessel_class_id=vessel.vessel_class_id,
                    cargo_capacity_mt=Decimal(str(vessel.cargo_capacity_mt)),
                    feasibility_status=feasibility.status,
                    feasibility_is_feasible=feasibility.is_feasible,
                    feasibility_cargo_request_id=cargo_request_id,
                    feasibility_commodity=commodity,
                    feasibility_origin_port_id=cargo.origin_port_id,
                    feasibility_destination_port_id=cargo.destination_port_id,
                    feasibility_cargo_volume_mt=cargo_volume_mt,
                    feasibility_required_voyages=feasibility.required_voyages,
                    forecast_run=run,
                    cost=cost_evidence,
                    scenario_risks=scenario_evidence,
                ))

        request = RecommendationInput(
            recommendation_id=uuid4(),
            created_at=datetime.now(timezone.utc),
            cargo_request_id=cargo_request_id,
            commodity=commodity,
            cargo_volume_mt=cargo_volume_mt,
            origin_port_id=cargo.origin_port_id,
            destination_port_id=cargo.destination_port_id,
            route=route,
            laycan_start_date=cargo.earliest_delivery_date,
            laycan_end_date=cargo.latest_delivery_date,
            contract_horizon=horizon,
            candidates=tuple(evidence_candidates),
        )
        with timed_stage("recommendation.engine"):
            decision = self.recommendation_engine.recommend(request)
        self._validate_decision(decision, request)
        with timed_stage("recommendation.persistence"):
            persisted = self.recommendation_repository.create(decision)
        result = self._persisted_result(decision, persisted)
        comparisons = tuple(
            CandidateComparison(
                vessel_class_id=candidate.vessel_class_id,
                feasibility_status=candidate.feasibility_status,
                expected_freight_cost=candidate.cost.expected_freight_cost,
                expected_total_cost=candidate.cost.expected_total_cost,
                effective_cost_per_mt=candidate.cost.effective_cost_per_mt,
                estimated_turnaround_hours=candidate.cost.estimated_turnaround_hours,
                required_voyages=candidate.cost.required_voyages,
                risk_level=worst_risk(item.risk_level for item in candidate.scenario_risks),
            )
            for candidate in evidence_candidates
        )
        return replace(result, candidate_comparisons=comparisons)

    @staticmethod
    def _validate_decision(result: RecommendationResult, request: RecommendationInput) -> None:
        if not isinstance(result, RecommendationResult):
            raise MissingRecommendationEvidenceError("Recommendation engine returned an invalid result")
        if result.cargo_request_id != request.cargo_request_id or result.recommendation_id != request.recommendation_id:
            raise InconsistentRecommendationEvidenceError("Recommendation identifiers do not match the request")
        matching = [c for c in request.candidates if c.vessel_class_id == result.recommended_vessel_class_id]
        if len(matching) != 1:
            raise InconsistentRecommendationEvidenceError("Recommended vessel is not a unique candidate")
        candidate = matching[0]
        if candidate.feasibility_status != FeasibilityStatus.FEASIBLE or not candidate.feasibility_is_feasible:
            raise InconsistentRecommendationEvidenceError("Recommendation selected an infeasible vessel")
        if result.forecast_run_id != candidate.forecast_run.forecast_run_id:
            raise InconsistentRecommendationEvidenceError("Recommendation forecast run does not match selected vessel")
        if candidate.forecast_run.cargo_request_id != result.cargo_request_id or candidate.forecast_run.route_id != request.route.route_id:
            raise InconsistentRecommendationEvidenceError("Recommendation forecast provenance does not match cargo and route")

    @staticmethod
    def _persisted_result(result: RecommendationResult, row: Any) -> RecommendationResult:
        try:
            created_at = row["created_at"]
            if not isinstance(created_at, datetime):
                created_at = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
            values = {
                "recommendation_id": UUID(str(row["recommendation_id"])),
                "cargo_request_id": UUID(str(row["cargo_request_id"])),
                "forecast_run_id": UUID(str(row["forecast_run_id"])),
                "recommended_vessel_class_id": str(row["recommended_vessel_class_id"]),
                "market_entry_action": MarketEntryAction(row["market_entry_action"]),
                "contract_strategy": ContractStrategy(row["contract_strategy"]),
                "expected_freight_cost": Decimal(str(row["expected_freight_cost"])),
                "expected_total_cost": Decimal(str(row["expected_total_cost"])),
                "estimated_turnaround_hours": Decimal(str(row["estimated_turnaround_hours"])),
                "risk_level": RiskLevel(row["risk_level"]),
                "confidence": RecommendationConfidence(row["confidence"]),
                "rationale": row["rationale"],
                "assumptions": row["assumptions"],
                "created_at": created_at,
            }
            if any(getattr(result, field) != value for field, value in values.items()):
                raise InconsistentRecommendationEvidenceError("Persisted recommendation differs from decision")
            return replace(result, **values)
        except InconsistentRecommendationEvidenceError:
            raise
        except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
            raise MissingRecommendationEvidenceError("Repository returned an incomplete recommendation") from exc

    @staticmethod
    def _validate_route(route: Route, origin: str, destination: str, commodity: Commodity) -> None:
        if (route.origin_port_id, route.destination_port_id, route.commodity) != (
            origin, destination, commodity.value
        ):
            raise InconsistentRecommendationEvidenceError(
                "Resolved canonical route does not match cargo ports and commodity"
            )

    @staticmethod
    def _validate_feasibility(result, cargo, cargo_request_id, commodity, cargo_volume_mt) -> None:
        if (
            result.origin_port_id != cargo.origin_port_id
            or result.destination_port_id != cargo.destination_port_id
            or result.commodity != commodity.value
            or Decimal(str(result.cargo_volume_mt)) != cargo_volume_mt
        ):
            raise InconsistentRecommendationEvidenceError(
                f"Feasibility provenance does not match cargo for {result.vessel_class_id}"
            )

    @staticmethod
    def _date(value: Any) -> date:
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        try:
            return date.fromisoformat(str(value))
        except (TypeError, ValueError) as exc:
            raise MissingRecommendationEvidenceError("Forecast contains an invalid date") from exc

    @classmethod
    def _forecast_evidence(
        cls, response, *, cargo_request_id, route, vessel_class_id, freight_unit
    ) -> tuple[ForecastRunEvidence, tuple[ForecastPointEvidence, ...], date]:
        try:
            run_row = response["forecast_run"]
            run_id = UUID(str(run_row["forecast_run_id"]))
            if UUID(str(run_row["cargo_request_id"])) != cargo_request_id:
                raise InconsistentRecommendationEvidenceError("Forecast run cargo does not match request")
            if run_row["route_id"] != route.route_id:
                raise InconsistentRecommendationEvidenceError("Forecast run route does not match cargo route")
            if run_row["vessel_class_id"] != vessel_class_id:
                raise InconsistentRecommendationEvidenceError("Forecast run vessel does not match candidate")
            if run_row["freight_unit"] != freight_unit.value:
                raise InconsistentRecommendationEvidenceError("Forecast run unit does not match requested unit")
            reference_date = cls._date(run_row["training_data_end_date"])
            raw_points = response["forecast_points"]
            if not raw_points:
                raise MissingRecommendationEvidenceError("Forecast run has no points")
            parsed = []
            for row in raw_points:
                if UUID(str(row["forecast_run_id"])) != run_id:
                    raise InconsistentRecommendationEvidenceError("Forecast point belongs to another run")
                if row["unit"] != freight_unit.value:
                    raise InconsistentRecommendationEvidenceError("Forecast point unit differs from run")
                parsed.append(ForecastPointEvidence(
                    forecast_date=cls._date(row["forecast_date"]),
                    lower_value=Decimal(str(row["lower_value"])),
                    central_value=Decimal(str(row["central_value"])),
                    upper_value=Decimal(str(row["upper_value"])),
                    unit=DomainFreightUnit(freight_unit.value),
                ))
            parsed.sort(key=lambda point: point.forecast_date)
            evidence = ForecastRunEvidence(
                forecast_run_id=run_id,
                cargo_request_id=cargo_request_id,
                route_id=route.route_id,
                vessel_class_id=vessel_class_id,
                freight_unit=DomainFreightUnit(freight_unit.value),
                points=tuple(parsed),
            )
            return evidence, tuple(parsed), reference_date
        except (InconsistentRecommendationEvidenceError, MissingRecommendationEvidenceError):
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise MissingRecommendationEvidenceError("Forecast result is incomplete or invalid") from exc

    @staticmethod
    def _cost_evidence(
        result, *, cargo_request_id, route, vessel_class_id, forecast_run,
        forecast_rate, freight_unit, reference_date
    ) -> CostEvidence:
        if result is None:
            raise MissingRecommendationEvidenceError("Cost engine returned no result")
        try:
            if result.freight_unit.value != freight_unit.value:
                raise InconsistentRecommendationEvidenceError("Cost unit differs from forecast unit")
            if Decimal(str(result.freight_rate_used)) != forecast_rate:
                raise InconsistentRecommendationEvidenceError(
                    "Cost engine did not use the first forecast point central value"
                )
            if result.cost_reference_date != reference_date:
                raise InconsistentRecommendationEvidenceError(
                    "Cost reference date differs from forecast training-data end date"
                )
            return CostEvidence(
                cargo_request_id=cargo_request_id,
                route_id=route.route_id,
                vessel_class_id=vessel_class_id,
                forecast_run_id=forecast_run.forecast_run_id,
                freight_unit=DomainFreightUnit(freight_unit.value),
                freight_rate_used=Decimal(str(result.freight_rate_used)),
                expected_freight_cost=Decimal(str(result.expected_freight_cost)),
                expected_total_cost=Decimal(str(result.expected_total_cost)),
                effective_cost_per_mt=Decimal(str(result.effective_cost_per_mt)),
                estimated_turnaround_hours=Decimal(str(result.estimated_turnaround_hours)),
                sailing_days_per_voyage=Decimal(str(result.sailing_days_per_voyage)),
                required_voyages=int(result.required_voyages),
            )
        except (InconsistentRecommendationEvidenceError, MissingRecommendationEvidenceError):
            raise
        except (AttributeError, TypeError, ValueError) as exc:
            raise MissingRecommendationEvidenceError("Cost result is incomplete or invalid") from exc

    @staticmethod
    def _scenario_evidence(
        scenario_set, *, cargo_request_id, route, vessel_class_id, forecast_run
    ) -> tuple[ScenarioRiskEvidence, ...]:
        if scenario_set is None:
            raise MissingRecommendationEvidenceError("Scenario service returned no results")
        try:
            results = (scenario_set.baseline, scenario_set.adverse, scenario_set.favorable)
            evidence = []
            for result, expected_type in zip(results, ScenarioType):
                if result.scenario_type != expected_type:
                    raise InconsistentRecommendationEvidenceError(
                        "Scenario service returned an unexpected canonical scenario"
                    )
                if UUID(str(result.cargo_request_id)) != cargo_request_id:
                    raise InconsistentRecommendationEvidenceError("Scenario cargo does not match request")
                evidence.append(ScenarioRiskEvidence(
                    scenario_type=expected_type,
                    risk_level=result.risk_level,
                    cargo_request_id=cargo_request_id,
                    route_id=route.route_id,
                    vessel_class_id=vessel_class_id,
                    forecast_run_id=forecast_run.forecast_run_id,
                ))
            return tuple(evidence)
        except (InconsistentRecommendationEvidenceError, MissingRecommendationEvidenceError):
            raise
        except (AttributeError, TypeError, ValueError) as exc:
            raise MissingRecommendationEvidenceError("Scenario/risk results are incomplete or invalid") from exc
