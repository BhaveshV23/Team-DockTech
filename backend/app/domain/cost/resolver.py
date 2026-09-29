"""
DockTech V1 — Cost Input Resolver
==================================
Orchestrates the retrieval of canonical reference data from repositories
and builds fully validated CostInputs domain value objects for the pure Cost Engine.

Authoritative Source-of-Truth Documents:
  1. PRD.md
  2. DATA_DICTIONARY.md (Frozen Domain Rules, Lines 170-360)
  3. ARCHITECTURE.md (Service & Repository Coordination)
  4. C1 Cost Engine Contract

Guarantees:
  - Preserves separation of concerns: Repository lookups are decoupled from pure math.
  - Sourced with deterministic cost_reference_date filtering.
  - Strict domain validation and structured error handling.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

from backend.app.domain.cost.models import CostInputs, FreightUnit
from backend.app.domain.entities import Berth, Route, VesselClass
from backend.app.repositories.reference_repository import ReferenceRepositoryProtocol


@dataclass(frozen=True)
class ResolvedCostContext:
    """Canonical records resolved once for cost and scenario calculations."""

    cost_inputs: CostInputs
    route: Route
    vessel_class: VesselClass
    origin_berth: Berth
    destination_berth: Berth
    cost_reference_date: datetime.date


class CostInputResolver:
    """
    Coordinates reference data retrieval across routes, vessels, berths, fuel prices,
    port activities, and freight observations to construct validated CostInputs.
    """

    def __init__(self, repository: ReferenceRepositoryProtocol) -> None:
        self.repository = repository

    def resolve_cost_inputs(
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
    ) -> CostInputs:
        """
        Retrieves all canonical parameters and returns a validated CostInputs value object.

        Parameters:
          cargo_volume_mt: Parcel volume in MT.
          origin_port_id: Origin loading port (e.g. 'NEWCASTLE').
          destination_port_id: Destination discharge port (e.g. 'PARADIP').
          commodity: Controlled commodity (e.g. 'THERMAL_COAL').
          vessel_class_id: Controlled vessel class (e.g. 'PANAMAX').
          freight_unit: 'USD_PER_MT' or 'USD_PER_DAY'.
          cost_reference_date: Authoritative anchor date (e.g. training_data_end_date).
          freight_rate_override: Optional forecast central value or user override.
          scenario_delay_hours: Additional scenario delay in hours.
          freight_adjustment_pct: Freight shock %.
          fuel_adjustment_pct: Bunker fuel shock %.
          port_costs_usd: Explicit port fees.
        """
        unit = FreightUnit.from_str(freight_unit)

        # 1. Resolve Route (Origin + Destination + Commodity)
        route = self.repository.get_route(
            origin_port_id=origin_port_id,
            destination_port_id=destination_port_id,
            commodity=commodity,
        )

        # 2. Resolve Vessel Class
        vessel = self.repository.get_vessel_class(vessel_class_id=vessel_class_id)

        # 3. Resolve Compatible Berth Handling Rates (Two-ended feasibility check)
        origin_handling_rate = self.repository.get_compatible_berth_handling_rate(
            port_id=route.origin_port_id,
            commodity=commodity,
            vessel_class=vessel,
        )
        dest_handling_rate = self.repository.get_compatible_berth_handling_rate(
            port_id=route.destination_port_id,
            commodity=commodity,
            vessel_class=vessel,
        )

        # 4. Resolve Latest VLSFO Bunker Price on or before cost_reference_date
        vlsfo_price = self.repository.get_latest_vlsfo_price(
            cost_reference_date=cost_reference_date
        )

        # 5. Resolve Port Waiting Times on or before cost_reference_date
        origin_waiting_hours = self.repository.get_latest_port_waiting_hours(
            port_id=route.origin_port_id,
            cost_reference_date=cost_reference_date,
        )
        dest_waiting_hours = self.repository.get_latest_port_waiting_hours(
            port_id=route.destination_port_id,
            cost_reference_date=cost_reference_date,
        )

        # 6. Resolve Freight Rate (from override or historical observation)
        if freight_rate_override is not None:
            freight_rate_value = freight_rate_override
        else:
            freight_rate_value = self.repository.get_latest_freight_rate(
                route_id=route.route_id,
                vessel_class_id=vessel.vessel_class_id,
                freight_unit=unit,
                cost_reference_date=cost_reference_date,
            )

        # 7. Construct and Return Validated Domain Value Object
        return CostInputs(
            cargo_volume_mt=cargo_volume_mt,
            distance_nm=route.distance_nm,
            vessel_cargo_capacity_mt=vessel.cargo_capacity_mt,
            vessel_speed_knots=vessel.speed_knots,
            vessel_fuel_consumption_tpd=vessel.fuel_consumption_mt_day,
            freight_rate_value=freight_rate_value,
            freight_unit=unit,
            vlsfo_price_usd_per_mt=vlsfo_price,
            origin_handling_rate_tpd=origin_handling_rate,
            dest_handling_rate_tpd=dest_handling_rate,
            origin_waiting_hours=origin_waiting_hours,
            dest_waiting_hours=dest_waiting_hours,
            scenario_delay_hours=scenario_delay_hours,
            freight_adjustment_pct=freight_adjustment_pct,
            fuel_adjustment_pct=fuel_adjustment_pct,
            port_costs_usd=port_costs_usd,
        )

    def resolve_cost_context(
        self,
        cargo_volume_mt: Decimal,
        origin_port_id: str,
        destination_port_id: str,
        commodity: str,
        vessel_class_id: str,
        freight_unit: FreightUnit | str,
        cost_reference_date: datetime.date,
        freight_rate_override: Optional[Decimal] = None,
    ) -> ResolvedCostContext:
        """Resolve cost inputs and retain the canonical records Scenario also needs."""
        unit = FreightUnit.from_str(freight_unit)
        route_record = self.repository.get_route(
            origin_port_id=origin_port_id,
            destination_port_id=destination_port_id,
            commodity=commodity,
        )
        vessel_record = self.repository.get_vessel_class(vessel_class_id=vessel_class_id)
        origin_berth_record = self.repository.get_compatible_berth(
            route_record.origin_port_id, commodity, vessel_record
        )
        destination_berth_record = self.repository.get_compatible_berth(
            route_record.destination_port_id, commodity, vessel_record
        )
        fuel_price = self.repository.get_latest_vlsfo_price(cost_reference_date)
        origin_waiting = self.repository.get_latest_port_waiting_hours(
            route_record.origin_port_id, cost_reference_date
        )
        destination_waiting = self.repository.get_latest_port_waiting_hours(
            route_record.destination_port_id, cost_reference_date
        )
        freight_rate = freight_rate_override
        if freight_rate is None:
            freight_rate = self.repository.get_latest_freight_rate(
                route_record.route_id, vessel_record.vessel_class_id, unit, cost_reference_date
            )

        cost_inputs = CostInputs(
            cargo_volume_mt=cargo_volume_mt,
            distance_nm=route_record.distance_nm,
            vessel_cargo_capacity_mt=vessel_record.cargo_capacity_mt,
            vessel_speed_knots=vessel_record.speed_knots,
            vessel_fuel_consumption_tpd=vessel_record.fuel_consumption_mt_day,
            freight_rate_value=freight_rate,
            freight_unit=unit,
            vlsfo_price_usd_per_mt=fuel_price,
            origin_handling_rate_tpd=origin_berth_record.handling_rate_tpd,
            dest_handling_rate_tpd=destination_berth_record.handling_rate_tpd,
            origin_waiting_hours=origin_waiting,
            dest_waiting_hours=destination_waiting,
        )
        return ResolvedCostContext(
            cost_inputs=cost_inputs,
            route=self._route_entity(route_record),
            vessel_class=self._vessel_entity(vessel_record),
            origin_berth=self._berth_entity(origin_berth_record),
            destination_berth=self._berth_entity(destination_berth_record),
            cost_reference_date=cost_reference_date,
        )

    @staticmethod
    def _route_entity(record: Any) -> Route:
        return Route(
            route_id=record.route_id, origin_port_id=record.origin_port_id,
            destination_port_id=record.destination_port_id, commodity=record.commodity,
            distance_nm=float(record.distance_nm), typical_sailing_days=float(record.typical_sailing_days),
            source=record.source, data_type=record.data_type,
        )

    @staticmethod
    def _vessel_entity(record: Any) -> VesselClass:
        return VesselClass(
            vessel_class_id=record.vessel_class_id, vessel_class_name=record.vessel_class_name,
            dwt_min_mt=float(record.dwt_min_mt), dwt_max_mt=float(record.dwt_max_mt),
            loa_m=float(record.loa_m), beam_m=float(record.beam_m), draft_m=float(record.draft_m),
            speed_knots=float(record.speed_knots), cargo_capacity_mt=float(record.cargo_capacity_mt),
            fuel_consumption_mt_day=float(record.fuel_consumption_mt_day),
            source=record.source, data_type=record.data_type,
        )

    @staticmethod
    def _berth_entity(record: Any) -> Berth:
        return Berth(
            berth_id=record.berth_id, port_id=record.port_id, berth_name=record.berth_name,
            commodity=record.commodity, max_loa_m=float(record.max_loa_m),
            max_beam_m=float(record.max_beam_m), max_draft_m=float(record.max_draft_m),
            handling_rate_tpd=float(record.handling_rate_tpd), source=record.source,
            data_type=record.data_type,
        )
