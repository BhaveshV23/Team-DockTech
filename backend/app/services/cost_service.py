"""
DockTech V1 — Cost Engine Service (Application / Orchestration Layer)
======================================================================
Thin application service coordinating:
  Repository → CostInputResolver → pure Cost Engine → CostResult.

Authoritative Source-of-Truth Documents:
  1. PRD.md
  2. DATA_DICTIONARY.md (Frozen Canonical Formulas)
  3. ARCHITECTURE.md (Service Layer Coordination, Repository Isolation)
  4. C1 Cost Engine Contract

Guarantees:
  - Orchestration only — zero new formulas, zero fallback/invented values.
  - All domain errors from C2/C3/C4 propagate transparently to the caller.
  - Deterministic results anchored by cost_reference_date.
  - Supports forecast freight override via the approved C4 mechanism.
  - Passes scenario adjustments through without implementing scenario-selection logic.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from backend.app.domain.cost.engine import calculate_cost
from backend.app.domain.cost.errors import CostDomainError
from backend.app.domain.cost.models import CostInputs, CostResult, FreightUnit
from backend.app.domain.cost.resolver import CostInputResolver, ResolvedCostContext
from backend.app.repositories.forecast_repository import forecast_repository
from backend.app.repositories.reference_repository import ReferenceRepositoryProtocol
from backend.app.schemas.auth import UserProfileResponse


class CostEngineService:
    """
    Application-layer orchestrator for the DockTech V1 Cost Engine.

    Coordinates reference data resolution (C4), pure cost calculation (C3),
    and returns a fully structured CostResult value object.

    This service is intentionally thin:
      - No FastAPI dependencies.
      - No database session management.
      - No scenario/risk/recommendation logic.
      - No new calculation formulas.
    """

    def __init__(self, repository: ReferenceRepositoryProtocol) -> None:
        self.repository = repository
        self._resolver = CostInputResolver(repository=repository)

    def calculate(
        self,
        cargo_volume_mt: Decimal,
        origin_port_id: str,
        destination_port_id: str,
        commodity: str,
        vessel_class_id: str,
        freight_unit: FreightUnit | str,
        cost_reference_date: datetime.date,
        freight_rate_override: Optional[Decimal] = None,
        scenario_delay_hours: Decimal = Decimal("0.0"),
        freight_adjustment_pct: Decimal = Decimal("0.0"),
        fuel_adjustment_pct: Decimal = Decimal("0.0"),
        port_costs_usd: Decimal = Decimal("0.0"),
    ) -> CostResult:
        """
        Execute the full Cost Engine pipeline for a single cargo/route/vessel combination.

        Steps:
          1. Resolve canonical reference data into CostInputs via C4 CostInputResolver.
          2. Pass CostInputs to C3 pure Cost Engine (calculate_cost).
          3. Return the resulting CostResult.

        Parameters:
          cargo_volume_mt: Total parcel volume in metric tonnes.
          origin_port_id: Canonical origin loading port identifier.
          destination_port_id: Canonical destination discharge port identifier.
          commodity: Controlled commodity value (e.g. 'THERMAL_COAL').
          vessel_class_id: Controlled vessel class identifier (e.g. 'PANAMAX').
          freight_unit: 'USD_PER_MT' or 'USD_PER_DAY'.
          cost_reference_date: Authoritative anchor date for deterministic lookups.
          freight_rate_override: Optional forecast central value or explicit user override.
          scenario_delay_hours: Additional scenario-induced delay hours per voyage.
          freight_adjustment_pct: Freight rate shock percentage (face value, e.g. 10.0 = +10%).
          fuel_adjustment_pct: Bunker fuel shock percentage (face value).
          port_costs_usd: Explicit port fees/costs in USD.

        Returns:
          CostResult immutable value object with full cost/duration breakdown.

        Raises:
          RouteNotFoundError: No canonical route matches the origin/destination/commodity.
          VesselClassNotFoundError: Vessel class identifier not found in catalog.
          InsufficientFeasibilityDataError: No compatible berth at origin or destination.
          InsufficientFuelPriceDataError: No VLSFO price on or before cost_reference_date.
          InsufficientPortActivityDataError: No port activity on or before cost_reference_date.
          InsufficientFreightDataError: No freight rate on or before cost_reference_date
              (when freight_rate_override is not supplied).
          InvalidCargoVolumeError: Cargo volume is non-positive.
          InvalidFreightUnitError: Freight unit is not a valid controlled value.
        """
        # Step 1: Resolve reference data → CostInputs (C4)
        cost_inputs: CostInputs = self._resolver.resolve_cost_inputs(
            cargo_volume_mt=cargo_volume_mt,
            origin_port_id=origin_port_id,
            destination_port_id=destination_port_id,
            commodity=commodity,
            vessel_class_id=vessel_class_id,
            freight_unit=freight_unit,
            cost_reference_date=cost_reference_date,
            freight_rate_override=freight_rate_override,
            scenario_delay_hours=scenario_delay_hours,
            freight_adjustment_pct=freight_adjustment_pct,
            fuel_adjustment_pct=fuel_adjustment_pct,
            port_costs_usd=port_costs_usd,
        )

        # Step 2: Execute pure Cost Engine (C3) → CostResult
        return self.calculate_resolved(cost_inputs, cost_reference_date)

    def calculate_with_context(
        self,
        cargo_volume_mt: Decimal,
        origin_port_id: str,
        destination_port_id: str,
        commodity: str,
        vessel_class_id: str,
        freight_unit: FreightUnit | str,
        cost_reference_date: datetime.date,
        freight_rate_override: Optional[Decimal] = None,
    ) -> tuple[CostResult, ResolvedCostContext]:
        """Calculate cost and retain the resolved records for Scenario reuse."""
        context = self._resolver.resolve_cost_context(
            cargo_volume_mt=cargo_volume_mt,
            origin_port_id=origin_port_id,
            destination_port_id=destination_port_id,
            commodity=commodity,
            vessel_class_id=vessel_class_id,
            freight_unit=freight_unit,
            cost_reference_date=cost_reference_date,
            freight_rate_override=freight_rate_override,
        )
        return self.calculate_resolved(context.cost_inputs, cost_reference_date), context

    @staticmethod
    def calculate_resolved(inputs: CostInputs, cost_reference_date: datetime.date) -> CostResult:
        """Run the unchanged pure cost engine over already-resolved inputs."""
        return calculate_cost(inputs=inputs, cost_reference_date=cost_reference_date)


class CostContextError(CostDomainError):
    """Raised when cargo and forecast records do not form a valid cost context."""

    def __init__(self, message: str, code: str = "ERROR_COST_CONTEXT_INVALID") -> None:
        super().__init__(message, code=code)


class CostApplicationService:
    """Resolve the authorized cargo and forecast context before costing it."""

    def __init__(
        self,
        engine: CostEngineService,
        cargo_access_service=None,
        forecast_repo=forecast_repository,
    ) -> None:
        self.engine = engine
        if cargo_access_service is None:
            from backend.app.services.cargo_service import cargo_service

            cargo_access_service = cargo_service
        self.cargo_access_service = cargo_access_service
        self.forecast_repo = forecast_repo

    def calculate_for_forecast(
        self,
        cargo_request_id: UUID,
        forecast_run_id: UUID,
        user_profile: UserProfileResponse,
        freight_rate_override: Optional[Decimal] = None,
        use_forecast_central_rate: bool = False,
        scenario_delay_hours: Decimal = Decimal("0.0"),
        freight_adjustment_pct: Decimal = Decimal("0.0"),
        fuel_adjustment_pct: Decimal = Decimal("0.0"),
        port_costs_usd: Decimal = Decimal("0.0"),
    ) -> CostResult:
        cargo = self.cargo_access_service.get_cargo_request(
            cargo_request_id, user_profile
        )

        forecast = self.forecast_repo.get_forecast_run(forecast_run_id)
        if not forecast:
            raise CostContextError("Forecast run not found", "ERROR_FORECAST_RUN_NOT_FOUND")
        if str(forecast.get("cargo_request_id")) != str(cargo_request_id):
            raise CostContextError("Forecast run does not belong to the cargo request")

        route = self.engine.repository.get_route(
            origin_port_id=cargo.origin_port_id,
            destination_port_id=cargo.destination_port_id,
            commodity=cargo.commodity,
        )
        if forecast.get("route_id") != route.route_id:
            raise CostContextError("Forecast route does not match the cargo request")

        try:
            reference_date = datetime.date.fromisoformat(
                str(forecast["training_data_end_date"])
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise CostContextError("Forecast run has no valid training data end date") from exc

        if use_forecast_central_rate and freight_rate_override is not None:
            raise CostContextError(
                "A freight rate override cannot be combined with the forecast central rate"
            )

        if use_forecast_central_rate:
            points = self.forecast_repo.get_forecast_points(forecast_run_id)
            try:
                points = sorted(points, key=lambda row: str(row["forecast_date"]))
                if not points:
                    raise ValueError("Forecast run has no points")
                if any(row.get("unit") != forecast.get("freight_unit") for row in points):
                    raise ValueError("Forecast point unit differs from forecast run")
                freight_rate_override = Decimal(str(points[0]["central_value"]))
                if freight_rate_override <= 0:
                    raise ValueError("Forecast central rate must be positive")
            except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
                raise CostContextError(
                    "Unable to resolve the forecast central freight rate"
                ) from exc

        return self.engine.calculate(
            cargo_volume_mt=Decimal(str(cargo.cargo_volume_mt)),
            origin_port_id=cargo.origin_port_id,
            destination_port_id=cargo.destination_port_id,
            commodity=cargo.commodity,
            vessel_class_id=forecast["vessel_class_id"],
            freight_unit=FreightUnit.from_str(forecast["freight_unit"]),
            cost_reference_date=reference_date,
            freight_rate_override=freight_rate_override,
            scenario_delay_hours=scenario_delay_hours,
            freight_adjustment_pct=freight_adjustment_pct,
            fuel_adjustment_pct=fuel_adjustment_pct,
            port_costs_usd=port_costs_usd,
        )
