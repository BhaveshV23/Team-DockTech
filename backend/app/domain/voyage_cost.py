"""Frozen V1 Voyage Cost and Turnaround Calculation Engine.

Implements exact mathematical formulas specified in DATA_DICTIONARY.md (Lines 234-334)
and ARCHITECTURE.md (Lines 166-185).
"""

import math
from typing import Optional

from backend.app.domain.constants import FreightUnit
from backend.app.domain.entities import (
    Berth,
    CargoRequest,
    Route,
    VesselClass,
    VoyageCostBreakdown,
)


class VoyageCostEngine:
    """Authoritative V1 calculation engine for bulk voyage cost and operational turnaround."""

    @staticmethod
    def calculate_sailing_days(distance_nm: float, speed_knots: float) -> float:
        """Calculates one-way laden sailing days.
        
        Formula: sailing_days = distance_nm / (speed_knots * 24)
        """
        if speed_knots <= 0:
            raise ValueError("Vessel speed must be strictly positive.")
        if distance_nm < 0:
            raise ValueError("Route distance cannot be negative.")
        return distance_nm / (speed_knots * 24.0)

    @staticmethod
    def calculate_required_voyages(cargo_volume_mt: float, vessel_capacity_mt: float) -> int:
        """Calculates required voyages for the cargo volume parcel.
        
        Formula: required_voyages = ceil(cargo_volume_mt / cargo_capacity_mt)
        """
        if cargo_volume_mt <= 0:
            raise ValueError("Cargo volume must be strictly positive.")
        if vessel_capacity_mt <= 0:
            raise ValueError("Vessel capacity must be strictly positive.")
        return math.ceil(cargo_volume_mt / vessel_capacity_mt)

    @classmethod
    def calculate_voyage_cost(
        cls,
        cargo_volume_mt: float,
        vessel_class: VesselClass,
        origin_berth: Berth,
        destination_berth: Berth,
        route: Route,
        freight_rate: float,
        freight_unit: FreightUnit,
        vlsfo_price_usd_mt: float,
        origin_waiting_hours: float,
        destination_waiting_hours: float,
        scenario_delay_hours: float = 0.0,
        port_allowance_usd: float = 0.0,
    ) -> VoyageCostBreakdown:
        """Computes comprehensive cost breakdown and turnaround duration adhering to frozen V1 rules.
        
        Strict V1 rules enforced:
        - Multi-voyage scaling for handling and turnaround.
        - VLSFO is the exclusive sea-going fuel (MGO excluded).
        - For USD_PER_MT, waiting time affects turnaround/risk only, zero fabricated demurrage.
        - For USD_PER_DAY, waiting and handling time expand vessel-days and charter hire.
        """
        if freight_rate <= 0:
            raise ValueError("Freight rate must be strictly positive.")
        if vlsfo_price_usd_mt <= 0:
            raise ValueError("VLSFO bunker fuel price must be strictly positive.")
        if origin_berth.handling_rate_tpd <= 0 or destination_berth.handling_rate_tpd <= 0:
            raise ValueError("Berth handling rates must be strictly positive.")
        if origin_waiting_hours < 0 or destination_waiting_hours < 0 or scenario_delay_hours < 0:
            raise ValueError("Waiting and delay hours cannot be negative.")

        sailing_days = cls.calculate_sailing_days(route.distance_nm, vessel_class.speed_knots)
        required_voyages = cls.calculate_required_voyages(cargo_volume_mt, vessel_class.cargo_capacity_mt)

        # 1. Handling hours total (across total cargo volume)
        origin_handling_hours_total = (cargo_volume_mt / origin_berth.handling_rate_tpd) * 24.0
        destination_handling_hours_total = (cargo_volume_mt / destination_berth.handling_rate_tpd) * 24.0

        # 2. Port waiting and scenario delay totals (occur on every voyage call)
        waiting_hours_total = (origin_waiting_hours + destination_waiting_hours) * required_voyages
        scenario_delay_total = scenario_delay_hours * required_voyages

        # 3. Total shipment turnaround
        estimated_turnaround_hours = (
            origin_handling_hours_total
            + destination_handling_hours_total
            + waiting_hours_total
            + scenario_delay_total
        )

        # 4. Per-voyage metrics
        turnaround_hours_per_voyage = estimated_turnaround_hours / required_voyages
        port_days_per_voyage = turnaround_hours_per_voyage / 24.0
        vessel_days_per_voyage = sailing_days + port_days_per_voyage

        # 5. Sea fuel cost (VLSFO only for transit)
        voyage_fuel_cost_usd = (
            sailing_days * vessel_class.fuel_consumption_mt_day * vlsfo_price_usd_mt
        )
        total_fuel_cost_usd = voyage_fuel_cost_usd * required_voyages

        # 6. Freight component
        if freight_unit == FreightUnit.USD_PER_MT:
            expected_freight_cost = cargo_volume_mt * freight_rate
        elif freight_unit == FreightUnit.USD_PER_DAY:
            expected_freight_cost = (
                vessel_days_per_voyage * freight_rate * required_voyages
            )
        else:
            raise ValueError(f"Unsupported freight unit: {freight_unit}")

        # 7. Total expected cost
        expected_total_cost = expected_freight_cost + total_fuel_cost_usd + port_allowance_usd
        effective_cost_per_mt = expected_total_cost / cargo_volume_mt

        return VoyageCostBreakdown(
            sailing_days=round(sailing_days, 4),
            required_voyages=required_voyages,
            origin_handling_hours_total=round(origin_handling_hours_total, 2),
            destination_handling_hours_total=round(destination_handling_hours_total, 2),
            waiting_hours_total=round(waiting_hours_total, 2),
            scenario_delay_total=round(scenario_delay_total, 2),
            estimated_turnaround_hours=round(estimated_turnaround_hours, 2),
            turnaround_hours_per_voyage=round(turnaround_hours_per_voyage, 2),
            port_days_per_voyage=round(port_days_per_voyage, 4),
            vessel_days_per_voyage=round(vessel_days_per_voyage, 4),
            total_fuel_cost_usd=round(total_fuel_cost_usd, 2),
            expected_freight_cost=round(expected_freight_cost, 2),
            expected_total_cost=round(expected_total_cost, 2),
            effective_cost_per_mt=round(effective_cost_per_mt, 4),
        )
