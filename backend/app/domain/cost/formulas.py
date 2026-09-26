"""DockTech V1 — Pure Cost Engine Formulas."""

from __future__ import annotations

from decimal import Decimal, ROUND_CEILING


def calculate_required_voyages(
    cargo_volume_mt: Decimal,
    vessel_cargo_capacity_mt: Decimal,
) -> int:
    """Required voyages = ceil(cargo_volume_mt / vessel_cargo_capacity_mt)."""
    if cargo_volume_mt <= Decimal("0"):
        raise ValueError(f"cargo_volume_mt must be strictly positive, got {cargo_volume_mt}.")
    if vessel_cargo_capacity_mt <= Decimal("0"):
        raise ValueError(
            f"vessel_cargo_capacity_mt must be strictly positive, got {vessel_cargo_capacity_mt}."
        )
    ratio = cargo_volume_mt / vessel_cargo_capacity_mt
    return int(ratio.to_integral_value(rounding=ROUND_CEILING))


def calculate_sailing_days(
    distance_nm: Decimal,
    vessel_speed_knots: Decimal,
) -> Decimal:
    """One-way sailing duration in days."""
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
    """Total port handling duration in hours for the full parcel."""
    return (cargo_volume_mt / handling_rate_tpd) * Decimal("24")


def calculate_waiting_hours_total(
    origin_waiting_hours: Decimal,
    dest_waiting_hours: Decimal,
    required_voyages: int,
) -> Decimal:
    """Total waiting hours across all voyage calls."""
    return (origin_waiting_hours + dest_waiting_hours) * Decimal(str(required_voyages))


def calculate_scenario_delay_hours_total(
    scenario_delay_hours: Decimal,
    required_voyages: int,
) -> Decimal:
    """Total scenario-induced delay across all planned voyage calls."""
    return scenario_delay_hours * Decimal(str(required_voyages))


def calculate_estimated_turnaround_hours(
    origin_handling_hours_total: Decimal,
    dest_handling_hours_total: Decimal,
    waiting_hours_total: Decimal,
    scenario_delay_hours_total: Decimal,
) -> Decimal:
    """Total shipment turnaround duration in hours."""
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
    """Port stay days allocated per single voyage call."""
    return (estimated_turnaround_hours / Decimal(str(required_voyages))) / Decimal("24")


def calculate_vessel_days_per_voyage(
    sailing_days_per_voyage: Decimal,
    port_days_per_voyage: Decimal,
) -> Decimal:
    """Total operational days per single voyage call."""
    return sailing_days_per_voyage + port_days_per_voyage


def apply_percentage_adjustment(
    base_value: Decimal,
    adjustment_pct: Decimal,
) -> Decimal:
    """Apply a percentage adjustment to a base value."""
    factor = Decimal("1") + (adjustment_pct / Decimal("100"))
    return base_value * factor


def calculate_total_fuel_consumption_mt(
    sailing_days_per_voyage: Decimal,
    vessel_fuel_consumption_tpd: Decimal,
    required_voyages: int,
) -> Decimal:
    """Total sea-going VLSFO fuel consumption in metric tonnes."""
    return sailing_days_per_voyage * vessel_fuel_consumption_tpd * Decimal(str(required_voyages))


def calculate_total_fuel_cost(
    total_fuel_consumption_mt: Decimal,
    vlsfo_price_used: Decimal,
) -> Decimal:
    """Total bunker fuel cost in USD."""
    return total_fuel_consumption_mt * vlsfo_price_used


def calculate_freight_cost_usd_per_mt(
    cargo_volume_mt: Decimal,
    adjusted_freight_rate: Decimal,
) -> Decimal:
    """Freight component under Voyage Charter (USD_PER_MT)."""
    return cargo_volume_mt * adjusted_freight_rate


def calculate_freight_cost_usd_per_day(
    vessel_days_per_voyage: Decimal,
    adjusted_freight_rate: Decimal,
    required_voyages: int,
) -> Decimal:
    """Freight component under Time Charter (USD_PER_DAY)."""
    return vessel_days_per_voyage * adjusted_freight_rate * Decimal(str(required_voyages))


def calculate_expected_total_cost(
    expected_freight_cost: Decimal,
    total_fuel_cost_usd: Decimal,
    port_costs_usd: Decimal = Decimal("0.0"),
) -> Decimal:
    """Expected total voyage / procurement cost."""
    return expected_freight_cost + total_fuel_cost_usd + port_costs_usd


def calculate_effective_cost_per_mt(
    expected_total_cost: Decimal,
    cargo_volume_mt: Decimal,
) -> Decimal:
    """Unit cost per metric tonne of cargo."""
    return expected_total_cost / cargo_volume_mt


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
