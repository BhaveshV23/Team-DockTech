"""
DockTech V1 — Pure Cost Engine Unit Tests
==========================================
Comprehensive unit tests verifying exact mathematical formulas, multi-voyage
parcel handling, USD_PER_MT vs USD_PER_DAY behavior, fuel burn, turnaround,
and decimal precision in the Cost Engine.

Authoritative Source-of-Truth Documents:
  1. PRD.md
  2. DATA_DICTIONARY.md (Lines 170-335)
  3. ARCHITECTURE.md
"""

from __future__ import annotations

import datetime
from decimal import Decimal
import pytest

from backend.app.domain.cost import (
    CostInputs,
    CostResult,
    FreightUnit,
    calculate_cost,
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
    apply_percentage_adjustment,
    InvalidCargoVolumeError,
    InvalidFreightUnitError,
)


# ==============================================================================
# 1. FORMULA-LEVEL PURE UNIT TESTS
# ==============================================================================

def test_required_voyages_exact_and_ceil():
    # Exactly 1 voyage
    assert calculate_required_voyages(Decimal("75000"), Decimal("75000")) == 1
    # Underutilization (1 voyage)
    assert calculate_required_voyages(Decimal("40000"), Decimal("75000")) == 1
    # Just over 1 capacity (requires 2 voyages)
    assert calculate_required_voyages(Decimal("75001"), Decimal("75000")) == 2
    # Exact multiple (requires 2 voyages)
    assert calculate_required_voyages(Decimal("150000"), Decimal("75000")) == 2
    # Large parcel requiring 3 voyages
    assert calculate_required_voyages(Decimal("160000"), Decimal("75000")) == 3


def test_sailing_days_precision():
    # Newcastle to Paradip thermal route: 5200 nm at 14.0 knots
    # 5200 / (14 * 24) = 5200 / 336 = 15.47619047619047619047619048...
    distance = Decimal("5200.0")
    speed = Decimal("14.0")
    sailing = calculate_sailing_days(distance, speed)
    expected = Decimal("5200") / Decimal("336")
    assert sailing == expected
    assert sailing > Decimal("15.476")
    assert sailing < Decimal("15.477")


def test_handling_hours_total():
    # 75,000 MT at 25,000 MT/day -> 3.0 days -> 72.0 hours
    vol = Decimal("75000.0")
    rate = Decimal("25000.0")
    assert calculate_handling_hours_total(vol, rate) == Decimal("72.0")

    # 75,000 MT at 20,000 MT/day -> 3.75 days -> 90.0 hours
    rate_dest = Decimal("20000.0")
    assert calculate_handling_hours_total(vol, rate_dest) == Decimal("90.0")


def test_waiting_and_turnaround_multi_voyage():
    # Single voyage: (36 + 24) * 1 = 60.0h
    assert calculate_waiting_hours_total(Decimal("36.0"), Decimal("24.0"), 1) == Decimal("60.0")
    # 2 voyages: (36 + 24) * 2 = 120.0h
    assert calculate_waiting_hours_total(Decimal("36.0"), Decimal("24.0"), 2) == Decimal("120.0")

    # Turnaround total for 2 voyages:
    # Handling: 144.0 (origin 150k @ 25k) + 180.0 (dest 150k @ 20k) = 324.0h
    # Waiting: 120.0h
    # Delay: 0.0h
    # Total: 444.0h
    tot_turnaround = calculate_estimated_turnaround_hours(
        origin_handling_hours_total=Decimal("144.0"),
        dest_handling_hours_total=Decimal("180.0"),
        waiting_hours_total=Decimal("120.0"),
        scenario_delay_hours_total=Decimal("0.0"),
    )
    assert tot_turnaround == Decimal("444.0")

    # Port days per voyage: (444.0 / 2) / 24 = 222.0 / 24 = 9.25 days
    port_days = calculate_port_days_per_voyage(tot_turnaround, 2)
    assert port_days == Decimal("9.25")

    # Vessel days per voyage with 15.476 days sailing: 15.476 + 9.25 = 24.726 days
    vessel_days = calculate_vessel_days_per_voyage(Decimal("15.476"), port_days)
    assert vessel_days == Decimal("24.726")


def test_percentage_adjustment():
    base = Decimal("100.0")
    assert apply_percentage_adjustment(base, Decimal("10.0")) == Decimal("110.0")
    assert apply_percentage_adjustment(base, Decimal("-15.0")) == Decimal("85.0")
    assert apply_percentage_adjustment(base, Decimal("0.0")) == Decimal("100.0")


# ==============================================================================
# 2. END-TO-END COST ENGINE EXECUTION TESTS
# ==============================================================================

@pytest.fixture
def baseline_inputs_usd_per_mt() -> CostInputs:
    return CostInputs(
        cargo_volume_mt=Decimal("75000.0"),
        distance_nm=Decimal("5200.0"),
        vessel_cargo_capacity_mt=Decimal("75000.0"),
        vessel_speed_knots=Decimal("14.0"),
        vessel_fuel_consumption_tpd=Decimal("35.0"),
        freight_rate_value=Decimal("14.50"),
        freight_unit=FreightUnit.USD_PER_MT,
        vlsfo_price_usd_per_mt=Decimal("580.0"),
        origin_handling_rate_tpd=Decimal("25000.0"),
        dest_handling_rate_tpd=Decimal("20000.0"),
        origin_waiting_hours=Decimal("36.0"),
        dest_waiting_hours=Decimal("24.0"),
        scenario_delay_hours=Decimal("0.0"),
        freight_adjustment_pct=Decimal("0.0"),
        fuel_adjustment_pct=Decimal("0.0"),
        port_costs_usd=Decimal("0.0"),
    )


def test_calculate_cost_usd_per_mt_single_voyage(baseline_inputs_usd_per_mt):
    ref_date = datetime.date(2025, 12, 31)
    res = calculate_cost(baseline_inputs_usd_per_mt, ref_date)

    # 1. Operational checks
    assert res.required_voyages == 1
    assert res.origin_handling_hours_total == Decimal("72.0")
    assert res.dest_handling_hours_total == Decimal("90.0")
    assert res.waiting_hours_total == Decimal("60.0")
    assert res.scenario_delay_hours_total == Decimal("0.0")
    assert res.estimated_turnaround_hours == Decimal("222.0")
    assert res.port_days_per_voyage == Decimal("9.25")

    # 2. Fuel checks (5200 / 336 sailing days * 35 tpd * 580 $/MT)
    sailing_days = Decimal("5200") / Decimal("336")
    expected_fuel_burn = sailing_days * Decimal("35")
    assert res.total_fuel_consumption_mt == expected_fuel_burn
    expected_fuel_cost = expected_fuel_burn * Decimal("580")
    assert res.total_fuel_cost_usd == expected_fuel_cost

    # 3. Freight checks ($14.50 * 75,000 MT)
    expected_freight = Decimal("14.50") * Decimal("75000")
    assert res.expected_freight_cost == expected_freight
    assert res.expected_freight_cost == Decimal("1087500.0")

    # 4. Total Cost & Effective $/MT
    expected_total = expected_freight + expected_fuel_cost
    assert res.expected_total_cost == expected_total
    assert res.effective_cost_per_mt == expected_total / Decimal("75000")
    assert res.cost_reference_date == ref_date


def test_calculate_cost_usd_per_day_time_charter():
    inputs = CostInputs(
        cargo_volume_mt=Decimal("75000.0"),
        distance_nm=Decimal("5200.0"),
        vessel_cargo_capacity_mt=Decimal("75000.0"),
        vessel_speed_knots=Decimal("14.0"),
        vessel_fuel_consumption_tpd=Decimal("35.0"),
        freight_rate_value=Decimal("18000.0"),  # $18,000 / day
        freight_unit=FreightUnit.USD_PER_DAY,
        vlsfo_price_usd_per_mt=Decimal("580.0"),
        origin_handling_rate_tpd=Decimal("25000.0"),
        dest_handling_rate_tpd=Decimal("20000.0"),
        origin_waiting_hours=Decimal("36.0"),
        dest_waiting_hours=Decimal("24.0"),
    )
    ref_date = datetime.date(2025, 12, 31)
    res = calculate_cost(inputs, ref_date)

    # In USD_PER_DAY, vessel_days = sailing_days + port_days
    # sailing_days = 5200 / 336 = 15.47619...
    # port_days = 222 / 24 = 9.25
    # vessel_days = 15.47619... + 9.25 = 24.72619...
    sailing_days = Decimal("5200") / Decimal("336")
    vessel_days = sailing_days + Decimal("9.25")
    assert res.vessel_days_per_voyage == vessel_days

    # Hire Freight = vessel_days * 18,000 * 1 voyage
    expected_hire_freight = vessel_days * Decimal("18000.0")
    assert res.expected_freight_cost == expected_hire_freight

    # Fuel cost is additional in Time Charter (voyage expense borne by charterer)
    expected_fuel_cost = sailing_days * Decimal("35.0") * Decimal("580.0")
    assert res.total_fuel_cost_usd == expected_fuel_cost

    assert res.expected_total_cost == expected_hire_freight + expected_fuel_cost


def test_calculate_cost_multi_voyage_with_shocks():
    # 150,000 MT on 75,000 MT Panamax -> 2 voyages
    inputs = CostInputs(
        cargo_volume_mt=Decimal("150000.0"),
        distance_nm=Decimal("5200.0"),
        vessel_cargo_capacity_mt=Decimal("75000.0"),
        vessel_speed_knots=Decimal("14.0"),
        vessel_fuel_consumption_tpd=Decimal("35.0"),
        freight_rate_value=Decimal("14.50"),
        freight_unit=FreightUnit.USD_PER_MT,
        vlsfo_price_usd_per_mt=Decimal("500.0"),
        origin_handling_rate_tpd=Decimal("25000.0"),
        dest_handling_rate_tpd=Decimal("20000.0"),
        origin_waiting_hours=Decimal("36.0"),
        dest_waiting_hours=Decimal("24.0"),
        scenario_delay_hours=Decimal("12.0"),  # +12h delay per voyage
        freight_adjustment_pct=Decimal("10.0"), # +10% freight shock
        fuel_adjustment_pct=Decimal("20.0"),    # +20% fuel shock
        port_costs_usd=Decimal("50000.0"),     # explicit port costs
    )
    ref_date = datetime.date(2025, 12, 31)
    res = calculate_cost(inputs, ref_date)

    assert res.required_voyages == 2

    # Adjusted rates:
    # Freight: 14.50 * 1.10 = 15.95
    assert res.freight_rate_used == Decimal("15.95")
    # Fuel Price: 500 * 1.20 = 600
    assert res.vlsfo_price_used == Decimal("600.0")

    # Waiting & Scenario Delays scaled by 2:
    assert res.waiting_hours_total == (Decimal("36.0") + Decimal("24.0")) * 2  # 120.0h
    assert res.scenario_delay_hours_total == Decimal("12.0") * 2               # 24.0h

    # Total Fuel Burn across 2 voyages:
    sailing_days_1_voyage = Decimal("5200") / Decimal("336")
    assert res.total_fuel_consumption_mt == sailing_days_1_voyage * Decimal("35.0") * 2
    assert res.total_fuel_cost_usd == res.total_fuel_consumption_mt * Decimal("600.0")

    # Freight cost: 150,000 MT * 15.95 = 2,392,500
    assert res.expected_freight_cost == Decimal("150000.0") * Decimal("15.95")

    # Expected total cost:
    assert res.expected_total_cost == (
        res.expected_freight_cost + res.total_fuel_cost_usd + Decimal("50000.0")
    )


# ==============================================================================
# 3. BOUNDARY & ERROR VALIDATION TESTS
# ==============================================================================

def test_invalid_cargo_volume():
    with pytest.raises(InvalidCargoVolumeError):
        CostInputs(
            cargo_volume_mt=Decimal("0.0"),
            distance_nm=Decimal("5200.0"),
            vessel_cargo_capacity_mt=Decimal("75000.0"),
            vessel_speed_knots=Decimal("14.0"),
            vessel_fuel_consumption_tpd=Decimal("35.0"),
            freight_rate_value=Decimal("14.50"),
            freight_unit=FreightUnit.USD_PER_MT,
            vlsfo_price_usd_per_mt=Decimal("580.0"),
            origin_handling_rate_tpd=Decimal("25000.0"),
            dest_handling_rate_tpd=Decimal("20000.0"),
            origin_waiting_hours=Decimal("36.0"),
            dest_waiting_hours=Decimal("24.0"),
        )


def test_invalid_negative_waiting():
    with pytest.raises(ValueError, match="origin_waiting_hours must be non-negative"):
        CostInputs(
            cargo_volume_mt=Decimal("75000.0"),
            distance_nm=Decimal("5200.0"),
            vessel_cargo_capacity_mt=Decimal("75000.0"),
            vessel_speed_knots=Decimal("14.0"),
            vessel_fuel_consumption_tpd=Decimal("35.0"),
            freight_rate_value=Decimal("14.50"),
            freight_unit=FreightUnit.USD_PER_MT,
            vlsfo_price_usd_per_mt=Decimal("580.0"),
            origin_handling_rate_tpd=Decimal("25000.0"),
            dest_handling_rate_tpd=Decimal("20000.0"),
            origin_waiting_hours=Decimal("-5.0"),
            dest_waiting_hours=Decimal("24.0"),
        )
