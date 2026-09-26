"""
DockTech V1 — Cost Engine Core
================================
Authoritative pure calculation engine coordinating multi-voyage bulk freight,
turnaround, bunker fuel consumption, and total procurement cost estimation.

Authoritative Source-of-Truth Documents:
  1. PRD.md
  2. DATA_DICTIONARY.md (Frozen Canonical Formulas, Lines 170-335)
  3. ARCHITECTURE.md (Domain Layer Architecture)
  4. C1 Cost Engine Contract

Guarantees:
  - 100% Pure Python (Zero database, FastAPI, or network dependencies).
  - Deterministic execution using exact Decimal arithmetic.
  - Transparent explainability via generated assumptions narrative.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import List

from .errors import InvalidFreightUnitError
from .formulas import (
    apply_percentage_adjustment,
    calculate_effective_cost_per_mt,
    calculate_estimated_turnaround_hours,
    calculate_expected_total_cost,
    calculate_freight_cost_usd_per_day,
    calculate_freight_cost_usd_per_mt,
    calculate_handling_hours_total,
    calculate_port_days_per_voyage,
    calculate_required_voyages,
    calculate_sailing_days,
    calculate_scenario_delay_hours_total,
    calculate_total_fuel_consumption_mt,
    calculate_total_fuel_cost,
    calculate_vessel_days_per_voyage,
    calculate_waiting_hours_total,
)
from .models import CostInputs, CostResult, FreightUnit


def calculate_cost(
    inputs: CostInputs,
    cost_reference_date: datetime.date,
) -> CostResult:
    """
    Executes the pure deterministic Cost Engine calculation for a single parcel request
    and feasible vessel class option.

    Parameters:
      inputs: Validated CostInputs domain value object.
      cost_reference_date: Authoritative lookup anchor date (forecast_run.training_data_end_date).

    Returns:
      CostResult immutable value object containing complete cost, duration, and operational breakdown.
    """
    assumptions: List[str] = []

    # 1. Required Voyages
    required_voyages = calculate_required_voyages(
        cargo_volume_mt=inputs.cargo_volume_mt,
        vessel_cargo_capacity_mt=inputs.vessel_cargo_capacity_mt,
    )
    if required_voyages == 1:
        if inputs.cargo_volume_mt < inputs.vessel_cargo_capacity_mt:
            assumptions.append(
                f"Single voyage with parcel volume {inputs.cargo_volume_mt} MT utilizing "
                f"{(inputs.cargo_volume_mt / inputs.vessel_cargo_capacity_mt * Decimal('100')):.1f}% of "
                f"vessel payload capacity ({inputs.vessel_cargo_capacity_mt} MT)."
            )
        else:
            assumptions.append(
                f"Single voyage full parcel fixture ({inputs.cargo_volume_mt} MT)."
            )
    else:
        assumptions.append(
            f"Multi-voyage requirement: parcel volume of {inputs.cargo_volume_mt} MT requires "
            f"{required_voyages} consecutive voyages at {inputs.vessel_cargo_capacity_mt} MT capacity per lift."
        )

    # 2. Sailing Duration (per voyage)
    sailing_days_per_voyage = calculate_sailing_days(
        distance_nm=inputs.distance_nm,
        vessel_speed_knots=inputs.vessel_speed_knots,
    )

    # 3. Handling Hours (total parcel across berths)
    origin_handling_hours_total = calculate_handling_hours_total(
        cargo_volume_mt=inputs.cargo_volume_mt,
        handling_rate_tpd=inputs.origin_handling_rate_tpd,
    )
    dest_handling_hours_total = calculate_handling_hours_total(
        cargo_volume_mt=inputs.cargo_volume_mt,
        handling_rate_tpd=inputs.dest_handling_rate_tpd,
    )

    # 4. Waiting and Scenario Delays (scaled by required_voyages)
    waiting_hours_total = calculate_waiting_hours_total(
        origin_waiting_hours=inputs.origin_waiting_hours,
        dest_waiting_hours=inputs.dest_waiting_hours,
        required_voyages=required_voyages,
    )
    scenario_delay_hours_total = calculate_scenario_delay_hours_total(
        scenario_delay_hours=inputs.scenario_delay_hours,
        required_voyages=required_voyages,
    )

    # 5. Estimated Total Shipment Turnaround
    estimated_turnaround_hours = calculate_estimated_turnaround_hours(
        origin_handling_hours_total=origin_handling_hours_total,
        dest_handling_hours_total=dest_handling_hours_total,
        waiting_hours_total=waiting_hours_total,
        scenario_delay_hours_total=scenario_delay_hours_total,
    )

    # 6. Per-Voyage Port Days & Operating Vessel Days
    port_days_per_voyage = calculate_port_days_per_voyage(
        estimated_turnaround_hours=estimated_turnaround_hours,
        required_voyages=required_voyages,
    )
    vessel_days_per_voyage = calculate_vessel_days_per_voyage(
        sailing_days_per_voyage=sailing_days_per_voyage,
        port_days_per_voyage=port_days_per_voyage,
    )

    # 7. Fuel Price & Fuel Cost Calculations
    vlsfo_price_used = apply_percentage_adjustment(
        base_value=inputs.vlsfo_price_usd_per_mt,
        adjustment_pct=inputs.fuel_adjustment_pct,
    )
    if inputs.fuel_adjustment_pct != Decimal("0.0"):
        assumptions.append(
            f"VLSFO bunker benchmark adjusted by {inputs.fuel_adjustment_pct:+.2f}% "
            f"from {inputs.vlsfo_price_usd_per_mt} $/MT to {vlsfo_price_used} $/MT."
        )

    total_fuel_consumption_mt = calculate_total_fuel_consumption_mt(
        sailing_days_per_voyage=sailing_days_per_voyage,
        vessel_fuel_consumption_tpd=inputs.vessel_fuel_consumption_tpd,
        required_voyages=required_voyages,
    )
    total_fuel_cost_usd = calculate_total_fuel_cost(
        total_fuel_consumption_mt=total_fuel_consumption_mt,
        vlsfo_price_used=vlsfo_price_used,
    )

    # 8. Freight Rate Adjustment & Freight Cost
    freight_rate_used = apply_percentage_adjustment(
        base_value=inputs.freight_rate_value,
        adjustment_pct=inputs.freight_adjustment_pct,
    )
    if inputs.freight_adjustment_pct != Decimal("0.0"):
        assumptions.append(
            f"Freight rate adjusted by {inputs.freight_adjustment_pct:+.2f}% "
            f"from {inputs.freight_rate_value} to {freight_rate_used} ({inputs.freight_unit.value})."
        )

    if inputs.freight_unit == FreightUnit.USD_PER_MT:
        expected_freight_cost = calculate_freight_cost_usd_per_mt(
            cargo_volume_mt=inputs.cargo_volume_mt,
            adjusted_freight_rate=freight_rate_used,
        )
        assumptions.append(
            "Voyage Charter freight pricing ($/MT): waiting and turnaround times impact operational "
            "schedule duration and risk rating; zero separate idle demurrage monetary charge added."
        )
    elif inputs.freight_unit == FreightUnit.USD_PER_DAY:
        expected_freight_cost = calculate_freight_cost_usd_per_day(
            vessel_days_per_voyage=vessel_days_per_voyage,
            adjusted_freight_rate=freight_rate_used,
            required_voyages=required_voyages,
        )
        assumptions.append(
            "Time Charter hire pricing ($/day): port turnaround and waiting time directly expand charter "
            "vessel days and are fully accounted for within hire freight cost."
        )
    else:
        raise InvalidFreightUnitError(f"Unsupported freight unit: {inputs.freight_unit}")

    # 9. Grand Total Cost & Effective Cost per MT
    expected_total_cost = calculate_expected_total_cost(
        expected_freight_cost=expected_freight_cost,
        total_fuel_cost_usd=total_fuel_cost_usd,
        port_costs_usd=inputs.port_costs_usd,
    )
    effective_cost_per_mt = calculate_effective_cost_per_mt(
        expected_total_cost=expected_total_cost,
        cargo_volume_mt=inputs.cargo_volume_mt,
    )

    if inputs.port_costs_usd > Decimal("0.0"):
        assumptions.append(f"Explicit port costs included: ${inputs.port_costs_usd:,.2f} USD.")

    return CostResult(
        required_voyages=required_voyages,
        sailing_days_per_voyage=sailing_days_per_voyage,
        origin_handling_hours_total=origin_handling_hours_total,
        dest_handling_hours_total=dest_handling_hours_total,
        waiting_hours_total=waiting_hours_total,
        scenario_delay_hours_total=scenario_delay_hours_total,
        estimated_turnaround_hours=estimated_turnaround_hours,
        port_days_per_voyage=port_days_per_voyage,
        vessel_days_per_voyage=vessel_days_per_voyage,
        vlsfo_price_used=vlsfo_price_used,
        total_fuel_consumption_mt=total_fuel_consumption_mt,
        total_fuel_cost_usd=total_fuel_cost_usd,
        freight_rate_used=freight_rate_used,
        freight_unit=inputs.freight_unit,
        expected_freight_cost=expected_freight_cost,
        port_costs_usd=inputs.port_costs_usd,
        expected_total_cost=expected_total_cost,
        effective_cost_per_mt=effective_cost_per_mt,
        cost_reference_date=cost_reference_date,
        assumptions=tuple(assumptions),
    )
