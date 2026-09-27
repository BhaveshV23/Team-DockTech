"""Scenario orchestration service for DockTech V1.

Coordinates baseline decision inputs with canonical scenario defaults,
computes parameter shocks, and produces structured scenario comparison results.
"""

import datetime
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID

from fastapi import HTTPException, status

from backend.app.domain.constants import Commodity, CongestionLevel, ContractHorizon, ScenarioType
from backend.app.domain.entities import (
    Berth,
    CargoRequest,
    DecisionInputs,
    Route,
    ScenarioDefault,
    ScenarioResult,
    ScenarioResultSet,
    VesselClass,
)
from backend.app.domain.cost.models import FreightUnit
from backend.app.domain.scenario import (
    ScenarioComparison,
    ScenarioEngine,
    ScenarioParameterShock,
)
from backend.app.repositories.scenario_repository import (
    ScenarioPersistenceError,
    ScenarioRepository,
    ScenarioStorageUnavailable,
)
from backend.app.repositories.forecast_repository import (
    ForecastPersistenceError,
    forecast_repository,
)
from backend.app.repositories.reference_repository import (
    ReferenceDataUnavailableError,
    SupabaseCostReferenceRepository,
)
from backend.app.schemas.auth import UserProfileResponse


class ScenarioContextError(Exception):
    def __init__(self, message: str, code: str = "ERROR_SCENARIO_CONTEXT_INVALID", status_code: int = 422):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class ScenarioService:
    """Service layer orchestrating multi-scenario sensitivity and shock simulations."""

    def __init__(
        self,
        repository: Optional[ScenarioRepository] = None,
        cargo_access_service=None,
        forecast_repo=forecast_repository,
        reference_repository=None,
    ):
        self.repository = repository or ScenarioRepository()
        if cargo_access_service is None:
            from backend.app.services.cargo_service import cargo_service
            cargo_access_service = cargo_service
        self.cargo_access_service = cargo_access_service
        self.forecast_repo = forecast_repo
        self.reference_repository = reference_repository or SupabaseCostReferenceRepository()

    @classmethod
    def production(cls):
        return cls(repository=ScenarioRepository(), reference_repository=SupabaseCostReferenceRepository())

    def resolve_decision_inputs(
        self, cargo_request_id: UUID, forecast_run_id: UUID, user_profile: UserProfileResponse
    ) -> DecisionInputs:
        """Build domain inputs only from owner-checked persisted application records."""
        cargo = self.cargo_access_service.get_cargo_request(cargo_request_id, user_profile)
        try:
            forecast = self.forecast_repo.get_forecast_run(forecast_run_id)
            if forecast is None:
                raise ScenarioContextError("Forecast run not found", "ERROR_FORECAST_RUN_NOT_FOUND", 404)
            if str(forecast.get("cargo_request_id")) != str(cargo_request_id):
                raise ScenarioContextError("Forecast run does not belong to the cargo request")
            route_record = self.reference_repository.get_route(
                origin_port_id=cargo.origin_port_id,
                destination_port_id=cargo.destination_port_id,
                commodity=cargo.commodity,
            )
            if forecast.get("route_id") != route_record.route_id:
                raise ScenarioContextError("Forecast route does not match the cargo request")
            vessel_record = self.reference_repository.get_vessel_class(forecast["vessel_class_id"])
            freight_unit = FreightUnit.from_str(forecast["freight_unit"])
            reference_date = datetime.date.fromisoformat(str(forecast["training_data_end_date"]))
            points = self.forecast_repo.get_forecast_points(forecast_run_id)
            if not points:
                raise ScenarioContextError("Forecast run has no persisted forecast points", "ERROR_FORECAST_POINTS_NOT_FOUND")
            if any(
                point.get("unit") != freight_unit.value
                or str(point.get("forecast_run_id")) != str(forecast_run_id)
                for point in points
            ):
                raise ScenarioContextError("Forecast point linkage or unit does not match the forecast run")
            # ForecastRepository returns points in canonical forecast_date order.
            freight_rate = Decimal(str(points[0]["central_value"]))
            spread_pct = max(
                ((Decimal(str(point["upper_value"])) - Decimal(str(point["lower_value"])))
                 / Decimal(str(point["central_value"])) * Decimal("100"))
                for point in points
            )
            origin_berth_record = self.reference_repository.get_compatible_berth(
                cargo.origin_port_id, cargo.commodity, vessel_record
            )
            destination_berth_record = self.reference_repository.get_compatible_berth(
                cargo.destination_port_id, cargo.commodity, vessel_record
            )
            origin_waiting = self.reference_repository.get_latest_port_waiting_hours(
                cargo.origin_port_id, reference_date
            )
            destination_waiting = self.reference_repository.get_latest_port_waiting_hours(
                cargo.destination_port_id, reference_date
            )
            fuel_price = self.reference_repository.get_latest_vlsfo_price(reference_date)
        except (ForecastPersistenceError, ReferenceDataUnavailableError) as exc:
            raise ScenarioStorageUnavailable(str(exc)) from exc
        except ScenarioContextError:
            raise
        except HTTPException:
            raise
        except Exception as exc:
            raise ScenarioContextError(str(exc)) from exc

        cargo_entity = CargoRequest(
            cargo_request_id=cargo.cargo_request_id,
            user_id=cargo.user_id,
            commodity=Commodity(cargo.commodity),
            cargo_volume_mt=cargo.cargo_volume_mt,
            origin_port_id=cargo.origin_port_id,
            destination_port_id=cargo.destination_port_id,
            laycan_start_date=cargo.earliest_delivery_date,
            laycan_end_date=cargo.latest_delivery_date,
            contract_horizon=ContractHorizon(cargo.contract_horizon),
            created_at=cargo.created_at,
        )
        vessel = VesselClass(
            vessel_class_id=vessel_record.vessel_class_id,
            vessel_class_name=vessel_record.vessel_class_name,
            dwt_min_mt=float(vessel_record.dwt_min_mt), dwt_max_mt=float(vessel_record.dwt_max_mt),
            loa_m=float(vessel_record.loa_m), beam_m=float(vessel_record.beam_m), draft_m=float(vessel_record.draft_m),
            speed_knots=float(vessel_record.speed_knots), cargo_capacity_mt=float(vessel_record.cargo_capacity_mt),
            fuel_consumption_mt_day=float(vessel_record.fuel_consumption_mt_day),
            source=vessel_record.source, data_type=vessel_record.data_type,
        )
        def to_berth(record):
            return Berth(
                berth_id=record.berth_id, port_id=record.port_id, berth_name=record.berth_name,
                commodity=record.commodity, max_loa_m=float(record.max_loa_m),
                max_beam_m=float(record.max_beam_m), max_draft_m=float(record.max_draft_m),
                handling_rate_tpd=float(record.handling_rate_tpd), source=record.source, data_type=record.data_type,
            )
        route = Route(
            route_id=route_record.route_id, origin_port_id=route_record.origin_port_id,
            destination_port_id=route_record.destination_port_id, commodity=route_record.commodity,
            distance_nm=float(route_record.distance_nm), typical_sailing_days=float(route_record.typical_sailing_days),
            source=route_record.source, data_type=route_record.data_type,
        )
        return DecisionInputs(
            cargo_request=cargo_entity, vessel_class=vessel,
            origin_berth=to_berth(origin_berth_record),
            destination_berth=to_berth(destination_berth_record), route=route,
            base_freight_rate=float(freight_rate), freight_unit=freight_unit,
            base_vlsfo_price_usd_mt=float(fuel_price),
            origin_waiting_hours=float(origin_waiting), destination_waiting_hours=float(destination_waiting),
            cost_reference_date=reference_date, forecast_spread_pct=float(spread_pct),
        )

    def run_canonical_for_cargo(self, cargo_request_id, forecast_run_id, user_profile):
        inputs = self.resolve_decision_inputs(cargo_request_id, forecast_run_id, user_profile)
        return self.run_scenarios(inputs, persist=True)

    def evaluate_canonical_for_cargo(self, cargo_request_id, forecast_run_id, user_profile, shock):
        inputs = self.resolve_decision_inputs(cargo_request_id, forecast_run_id, user_profile)
        return self.evaluate_custom_scenario(inputs, shock, scenario_type=ScenarioType.ADVERSE, persist=True)

    def get_scenario_defaults(self) -> List[ScenarioDefault]:
        """Loads canonical scenario presets (BASELINE, ADVERSE, FAVORABLE)."""
        return self.repository.get_scenario_defaults()

    def run_scenarios(
        self, base_inputs: DecisionInputs, persist: bool = True
    ) -> ScenarioResultSet:
        """Runs the three canonical scenarios (BASELINE, ADVERSE, FAVORABLE) for a chartering decision.
        
        Guarantees:
        - Exactly three scenario results returned.
        - Canonical default values used.
        - Results persisted to database if persist=True.
        """
        defaults = {d.scenario_id: d for d in self.get_scenario_defaults()}

        # 1. BASELINE
        baseline_def = defaults[ScenarioType.BASELINE]
        baseline_shock = ScenarioParameterShock(
            freight_change_pct=baseline_def.freight_change_pct,
            fuel_change_pct=baseline_def.fuel_change_pct,
            delay_hours=baseline_def.delay_hours,
            congestion_level=baseline_def.port_congestion_level,
        )
        baseline_result = ScenarioEngine.apply_scenario(
            base_inputs=base_inputs,
            scenario_type=ScenarioType.BASELINE,
            shock=baseline_shock,
        )

        # 2. ADVERSE
        adverse_def = defaults[ScenarioType.ADVERSE]
        adverse_shock = ScenarioParameterShock(
            freight_change_pct=adverse_def.freight_change_pct,
            fuel_change_pct=adverse_def.fuel_change_pct,
            delay_hours=adverse_def.delay_hours,
            congestion_level=adverse_def.port_congestion_level,
        )
        adverse_result = ScenarioEngine.apply_scenario(
            base_inputs=base_inputs,
            scenario_type=ScenarioType.ADVERSE,
            shock=adverse_shock,
        )

        # 3. FAVORABLE
        favorable_def = defaults[ScenarioType.FAVORABLE]
        favorable_shock = ScenarioParameterShock(
            freight_change_pct=favorable_def.freight_change_pct,
            fuel_change_pct=favorable_def.fuel_change_pct,
            delay_hours=favorable_def.delay_hours,
            congestion_level=favorable_def.port_congestion_level,
        )
        favorable_result = ScenarioEngine.apply_scenario(
            base_inputs=base_inputs,
            scenario_type=ScenarioType.FAVORABLE,
            shock=favorable_shock,
        )

        if persist:
            self.repository.save_scenario_result(baseline_result)
            self.repository.save_scenario_result(adverse_result)
            self.repository.save_scenario_result(favorable_result)

        return ScenarioResultSet(
            baseline=baseline_result,
            adverse=adverse_result,
            favorable=favorable_result,
        )

    def evaluate_custom_scenario(
        self,
        base_inputs: DecisionInputs,
        shock: ScenarioParameterShock,
        scenario_type: ScenarioType = ScenarioType.ADVERSE,
        persist: bool = False,
    ) -> ScenarioComparison:
        """Evaluates a user-adjusted parameter shock and compares against baseline."""
        # Baseline
        baseline_def = self.repository.get_scenario_default_by_type(ScenarioType.BASELINE)
        baseline_shock = ScenarioParameterShock(
            freight_change_pct=baseline_def.freight_change_pct,
            fuel_change_pct=baseline_def.fuel_change_pct,
            delay_hours=baseline_def.delay_hours,
            congestion_level=baseline_def.port_congestion_level,
        )
        baseline_result = ScenarioEngine.apply_scenario(
            base_inputs=base_inputs,
            scenario_type=ScenarioType.BASELINE,
            shock=baseline_shock,
        )

        # Custom scenario
        custom_result = ScenarioEngine.apply_scenario(
            base_inputs=base_inputs,
            scenario_type=scenario_type,
            shock=shock,
        )

        if persist:
            self.repository.save_scenario_result(custom_result)

        return ScenarioEngine.compare_scenarios(
            baseline=baseline_result, scenario=custom_result
        )

    def get_saved_scenarios(self, cargo_request_id: UUID) -> List[dict[str, Any]]:
        """Retrieves stored scenario results for a cargo request."""
        return self.repository.get_scenarios_by_cargo_request(cargo_request_id)
