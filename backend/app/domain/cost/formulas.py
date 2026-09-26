"""
DockTech V1 — Pure Cost Engine Formulas
========================================
Pure mathematical calculation functions for bulk maritime voyage estimation,
turnaround, fuel consumption, freight hire, and total procurement cost.

Authoritative Source-of-Truth Documents:
  1. PRD.md
  2. DATA_DICTIONARY.md (Frozen Canonical Formulas, Lines 170-335)
  3. ARCHITECTURE.md (Cost & Turnaround Architecture)
  4. C1 Cost Engine Contract

Guarantees:
  - 100% Pure Python (No SQL, FastAPI, or external network dependencies).
  - Exact Decimal arithmetic (no float precision loss).
  - Multi-voyage parcel accounting with non-duplicated waiting/delay time.
  - Distinct USD_PER_MT vs USD_PER_DAY calculation paths.
  - Zero fabricated demurrage or uncalibrated MGO transit costs.
"""

from __future__ import annotations

import math
from decimal import Decimal, ROUND_CEILING


def calculate_required_voyages(
    cargo_volume_mt: Decimal,
    vessel_cargo_capacity_mt: Decimal,
) -> int:
    """
    Computes the planning required voyages:
      required_voyages = ceil(cargo_volume_mt / vessel_cargo_capacity_mt)
    """
    if cargo_volume_mt <= Decimal("0"):
        raise ValueError(f"cargo_volume_mt must be strictly positive, got {cargo_volume_mt}.")
    if vessel_cargo_capacity_mt <= Decimal("0"):
        raise ValueError(
            f"vessel_cargo_capacity_mt must be strictly positive, got {vessel_cargo_capacity_mt}."
        )
    ratio = cargo_volume_mt / vessel_cargo_capacity_mt
    # Exact ceil using Decimal
    return int(ratio.to_integral_value(rounding=ROUND_CEILING))


def calculate_sailing_days(
    distance_nm: Decimal,
    vessel_speed_knots: Decimal,
) -> Decimal:
    """
    Computes vessel one-way laden sailing duration in days:
      sailing_days = distance_nm / (speed_knots * 24)
    """
    if distance_nm <= Decimal("0"):
        raise ValueError(f"distance_nm must be strictly positive, got {distance_nm}.")
    if vessel_speed_knots <= Decimal("0"):
        raise ValueError(
            f"vessel_speed_knots must be strictly positive, got {vessel_speed_knots}."
        )
    return distance_nm / (vessel_speed_knots * Decimal("24"))


def calculate_handling_hours_total(
    cargo_volume_mt: Decimal,
    handling_rate_tpd: Decimal,
) -> Decimal:
    """
    Computes total port handling duration in hours for the full parcel:
      handling_hours = (cargo_volume_mt / handling_rate_tpd) * 24
    """
    return (cargo_volume_mt / handling_rate_tpd) * Decimal("24")


def calculate_waiting_hours_total(
    origin_waiting_hours: Decimal,
    dest_waiting_hours: Decimal,
    required_voyages: int,
) -> Decimal:
    """
    Computes total waiting time across all required voyage calls:
      waiting_hours_total = (origin_waiting_hours + dest_waiting_hours) * required_voyages
    """
    return (origin_waiting_hours + dest_waiting_hours) * Decimal(str(required_voyages))


def calculate_scenario_delay_hours_total(
    scenario_delay_hours: Decimal,
    required_voyages: int,
) -> Decimal:
    """
    Computes total scenario-induced delay across all required voyage calls:
      scenario_delay_total = scenario_delay_hours * required_voyages
    """
    return scenario_delay_hours * Decimal(str(required_voyages))


def calculate_estimated_turnaround_hours(
    origin_handling_hours_total: Decimal,
    dest_handling_hours_total: Decimal,
    waiting_hours_total: Decimal,
    scenario_delay_hours_total: Decimal,
) -> Decimal:
    """
    Computes total shipment turnaround duration:
      turnaround_hours = origin_handling + dest_handling + waiting_total + scenario_delay_total
    """
    return (
        origin_handling_hours_total
        + dest_handling_hours_total
        + waiting_hours_total
        + scenario_delay_hours_total
    )


def calculate_port_days_per_voyage(
    estimated_turnaround_hours: Decimal,
    required_voyages: int,
) -> Decimal:
    """
    Computes port stay days allocated per single voyage call:
      port_days_per_voyage = (estimated_turnaround_hours / required_voyages) / 24
    """
    return (estimated_turnaround_hours / Decimal(str(required_voyages))) / Decimal("24")


def calculate_vessel_days_per_voyage(
    sailing_days_per_voyage: Decimal,
    port_days_per_voyage: Decimal,
) -> Decimal:
    """
    Computes total vessel operational days per single voyage call:
      vessel_days_per_voyage = sailing_days + port_days_per_voyage
    """
    return sailing_days_per_voyage + port_days_per_voyage


def apply_percentage_adjustment(
    base_value: Decimal,
    adjustment_pct: Decimal,
) -> Decimal:
    """
    Scales a base value by a percentage adjustment stored as face value:
      adjusted = base_value * (1 + adjustment_pct / 100)
    """
    factor = Decimal("1") + (adjustment_pct / Decimal("100"))
    return base_value * factor


def calculate_total_fuel_consumption_mt(
    sailing_days_per_voyage: Decimal,
    vessel_fuel_consumption_tpd: Decimal,
    required_voyages: int,
) -> Decimal:
    """
    Computes total sea-going VLSFO fuel consumption in MT across all voyages:
      total_fuel_mt = sailing_days * fuel_consumption_tpd * required_voyages
    """
    return sailing_days_per_voyage * vessel_fuel_consumption_tpd * Decimal(str(required_voyages))


def calculate_total_fuel_cost(
    total_fuel_consumption_mt: Decimal,
    vlsfo_price_used: Decimal,
) -> Decimal:
    """
    Computes total bunker fuel cost in USD:
      total_fuel_cost = total_fuel_consumption_mt * vlsfo_price_used
    """
    return total_fuel_consumption_mt * vlsfo_price_used


def calculate_freight_cost_usd_per_mt(
    cargo_volume_mt: Decimal,
    adjusted_freight_rate: Decimal,
) -> Decimal:
    """
    Computes freight component under Voyage Charter (USD_PER_MT):
      freight_cost = cargo_volume_mt * adjusted_freight_rate
    """
    return cargo_volume_mt * adjusted_freight_rate


def calculate_freight_cost_usd_per_day(
    vessel_days_per_voyage: Decimal,
    adjusted_freight_rate: Decimal,
    required_voyages: int,
) -> Decimal:
    """
    Computes charter hire freight component under Time Charter (USD_PER_DAY):
      freight_cost = vessel_days_per_voyage * adjusted_freight_rate * required_voyages
    """
    return vessel_days_per_voyage * adjusted_freight_rate * Decimal(str(required_voyages))


def calculate_expected_total_cost(
    expected_freight_cost: Decimal,
    total_fuel_cost_usd: Decimal,
    port_costs_usd: Decimal = Decimal("0.0"),
) -> Decimal:
    """
    Computes total voyage/procurement cost:
      expected_total_cost = freight_cost + fuel_cost + port_costs
    """
    return expected_freight_cost + total_fuel_cost_usd + port_costs_usd


def calculate_effective_cost_per_mt(
    expected_total_cost: Decimal,
    cargo_volume_mt: Decimal,
) -> Decimal:
    """
    Computes unit cost per metric tonne of cargo:
      effective_cost_per_mt = expected_total_cost / cargo_volume_mt
    """
    return expected_total_cost / cargo_volume_mt
