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
from decimal import Decimal
from typing import Optional

from backend.app.domain.cost.models import CostInputs, FreightUnit
from backend.app.repositories.reference_repository import ReferenceRepositoryProtocol


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
