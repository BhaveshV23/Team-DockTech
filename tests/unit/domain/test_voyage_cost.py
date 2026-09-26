"""Canonical cost-engine regression tests for voyage math and turnaround behavior."""

from decimal import Decimal

import pytest

from backend.app.domain.cost import (
    CostInputs,
    FreightUnit,
    calculate_cost,
    calculate_required_voyages,
    calculate_sailing_days,
)


def test_sailing_days_calculation():
    """Verify sailing_days = distance_nm / (speed_knots * 24)."""
    days = calculate_sailing_days(Decimal("5600"), Decimal("13"))
    assert round(float(days), 4) == 17.9487


def test_required_voyages_calculation():
    """Verify ceil(cargo_volume / vessel_capacity)."""
    assert calculate_required_voyages(Decimal("75000"), Decimal("75000")) == 1
    assert calculate_required_voyages(Decimal("75001"), Decimal("75000")) == 2
    assert calculate_required_voyages(Decimal("150000"), Decimal("75000")) == 2
    assert calculate_required_voyages(Decimal("160000"), Decimal("75000")) == 3


def test_multi_voyage_cost_and_turnaround_scaling(sample_vessels, sample_berths, sample_route):
    """Verify multi-voyage turnaround and delay scaling using the canonical engine."""
    inputs = CostInputs(
        cargo_volume_mt=Decimal("150000"),
        distance_nm=Decimal(str(sample_route.distance_nm)),
        vessel_cargo_capacity_mt=Decimal(str(sample_vessels["panamax"].cargo_capacity_mt)),
        vessel_speed_knots=Decimal(str(sample_vessels["panamax"].speed_knots)),
        vessel_fuel_consumption_tpd=Decimal(str(sample_vessels["panamax"].fuel_consumption_mt_day)),
        freight_rate_value=Decimal("20.0"),
        freight_unit=FreightUnit.USD_PER_MT,
        vlsfo_price_usd_per_mt=Decimal("600.0"),
        origin_handling_rate_tpd=Decimal(str(sample_berths["origin"].handling_rate_tpd)),
        dest_handling_rate_tpd=Decimal(str(sample_berths["destination"].handling_rate_tpd)),
        origin_waiting_hours=Decimal("12.0"),
        dest_waiting_hours=Decimal("24.0"),
        scenario_delay_hours=Decimal("10.0"),
    )
    cost = calculate_cost(inputs, sample_route.data_type and __import__('datetime').date(2025, 12, 31))

    assert cost.required_voyages == 2
    assert cost.origin_handling_hours_total == Decimal("72.0")
    assert cost.dest_handling_hours_total == Decimal("120.0")
    assert cost.waiting_hours_total == Decimal("72.0")
    assert cost.scenario_delay_hours_total == Decimal("20.0")
    assert cost.estimated_turnaround_hours == Decimal("284.0")

    sailing_days = Decimal("5600") / (Decimal("13") * Decimal("24"))
    expected_fuel = sailing_days * Decimal("28.0") * Decimal("600.0") * Decimal("2")
    assert round(float(cost.total_fuel_cost_usd), 2) == round(float(expected_fuel), 2)
    assert cost.expected_freight_cost == Decimal("3000000.0")
    assert cost.expected_total_cost == Decimal("3000000.0") + expected_fuel


def test_usd_per_mt_zero_arbitrary_demurrage(sample_vessels, sample_berths, sample_route):
    """USD_PER_MT should not add arbitrary demurrage beyond operational turnaround."""
    base = CostInputs(
        cargo_volume_mt=Decimal("75000"),
        distance_nm=Decimal(str(sample_route.distance_nm)),
        vessel_cargo_capacity_mt=Decimal(str(sample_vessels["panamax"].cargo_capacity_mt)),
        vessel_speed_knots=Decimal(str(sample_vessels["panamax"].speed_knots)),
        vessel_fuel_consumption_tpd=Decimal(str(sample_vessels["panamax"].fuel_consumption_mt_day)),
        freight_rate_value=Decimal("18.0"),
        freight_unit=FreightUnit.USD_PER_MT,
        vlsfo_price_usd_per_mt=Decimal("600.0"),
        origin_handling_rate_tpd=Decimal(str(sample_berths["origin"].handling_rate_tpd)),
        dest_handling_rate_tpd=Decimal(str(sample_berths["destination"].handling_rate_tpd)),
        origin_waiting_hours=Decimal("0.0"),
        dest_waiting_hours=Decimal("0.0"),
        scenario_delay_hours=Decimal("0.0"),
    )
    delayed = CostInputs(
        cargo_volume_mt=Decimal("75000"),
        distance_nm=Decimal(str(sample_route.distance_nm)),
        vessel_cargo_capacity_mt=Decimal(str(sample_vessels["panamax"].cargo_capacity_mt)),
        vessel_speed_knots=Decimal(str(sample_vessels["panamax"].speed_knots)),
        vessel_fuel_consumption_tpd=Decimal(str(sample_vessels["panamax"].fuel_consumption_mt_day)),
        freight_rate_value=Decimal("18.0"),
        freight_unit=FreightUnit.USD_PER_MT,
        vlsfo_price_usd_per_mt=Decimal("600.0"),
        origin_handling_rate_tpd=Decimal(str(sample_berths["origin"].handling_rate_tpd)),
        dest_handling_rate_tpd=Decimal(str(sample_berths["destination"].handling_rate_tpd)),
        origin_waiting_hours=Decimal("48.0"),
        dest_waiting_hours=Decimal("48.0"),
        scenario_delay_hours=Decimal("48.0"),
    )

    cost_no_delay = calculate_cost(base, __import__('datetime').date(2025, 12, 31))
    cost_with_delay = calculate_cost(delayed, __import__('datetime').date(2025, 12, 31))

    assert cost_with_delay.expected_freight_cost == cost_no_delay.expected_freight_cost
    assert cost_with_delay.total_fuel_cost_usd == cost_no_delay.total_fuel_cost_usd
    assert cost_with_delay.expected_total_cost == cost_no_delay.expected_total_cost
    assert cost_with_delay.estimated_turnaround_hours > cost_no_delay.estimated_turnaround_hours


def test_usd_per_day_monetizes_port_days(sample_vessels, sample_berths, sample_route):
    """Verify that for USD_PER_DAY, port delay expands charter hire."""
    low = CostInputs(
        cargo_volume_mt=Decimal("75000"),
        distance_nm=Decimal(str(sample_route.distance_nm)),
        vessel_cargo_capacity_mt=Decimal(str(sample_vessels["panamax"].cargo_capacity_mt)),
        vessel_speed_knots=Decimal(str(sample_vessels["panamax"].speed_knots)),
        vessel_fuel_consumption_tpd=Decimal(str(sample_vessels["panamax"].fuel_consumption_mt_day)),
        freight_rate_value=Decimal("20000.0"),
        freight_unit=FreightUnit.USD_PER_DAY,
        vlsfo_price_usd_per_mt=Decimal("600.0"),
        origin_handling_rate_tpd=Decimal(str(sample_berths["origin"].handling_rate_tpd)),
        dest_handling_rate_tpd=Decimal(str(sample_berths["destination"].handling_rate_tpd)),
        origin_waiting_hours=Decimal("0.0"),
        dest_waiting_hours=Decimal("0.0"),
        scenario_delay_hours=Decimal("0.0"),
    )
    high = CostInputs(
        cargo_volume_mt=Decimal("75000"),
        distance_nm=Decimal(str(sample_route.distance_nm)),
        vessel_cargo_capacity_mt=Decimal(str(sample_vessels["panamax"].cargo_capacity_mt)),
        vessel_speed_knots=Decimal(str(sample_vessels["panamax"].speed_knots)),
        vessel_fuel_consumption_tpd=Decimal(str(sample_vessels["panamax"].fuel_consumption_mt_day)),
        freight_rate_value=Decimal("20000.0"),
        freight_unit=FreightUnit.USD_PER_DAY,
        vlsfo_price_usd_per_mt=Decimal("600.0"),
        origin_handling_rate_tpd=Decimal(str(sample_berths["origin"].handling_rate_tpd)),
        dest_handling_rate_tpd=Decimal(str(sample_berths["destination"].handling_rate_tpd)),
        origin_waiting_hours=Decimal("24.0"),
        dest_waiting_hours=Decimal("24.0"),
        scenario_delay_hours=Decimal("48.0"),
    )

    cost_low_delay = calculate_cost(low, __import__('datetime').date(2025, 12, 31))
    cost_high_delay = calculate_cost(high, __import__('datetime').date(2025, 12, 31))

    extra_port_days = Decimal("96") / Decimal("24")
    expected_extra_hire = extra_port_days * Decimal("20000.0")
    actual_extra_hire = cost_high_delay.expected_freight_cost - cost_low_delay.expected_freight_cost
    assert round(float(actual_extra_hire), 2) == round(float(expected_extra_hire), 2)


def test_invalid_parameters_raise_value_error(sample_vessels, sample_berths, sample_route):
    """Verify invalid numbers raise canonical validation errors."""
    with pytest.raises(ValueError, match="strictly positive"):
        calculate_sailing_days(Decimal("5000"), Decimal("0"))

    with pytest.raises(ValueError, match="strictly positive"):
        calculate_required_voyages(Decimal("0"), Decimal("75000"))

    with pytest.raises(ValueError, match="strictly greater than 0"):
        CostInputs(
            cargo_volume_mt=Decimal("75000"),
            distance_nm=Decimal(str(sample_route.distance_nm)),
            vessel_cargo_capacity_mt=Decimal(str(sample_vessels["panamax"].cargo_capacity_mt)),
            vessel_speed_knots=Decimal(str(sample_vessels["panamax"].speed_knots)),
            vessel_fuel_consumption_tpd=Decimal(str(sample_vessels["panamax"].fuel_consumption_mt_day)),
            freight_rate_value=Decimal("-5.0"),
            freight_unit=FreightUnit.USD_PER_MT,
            vlsfo_price_usd_per_mt=Decimal("600.0"),
            origin_handling_rate_tpd=Decimal(str(sample_berths["origin"].handling_rate_tpd)),
            dest_handling_rate_tpd=Decimal(str(sample_berths["destination"].handling_rate_tpd)),
            origin_waiting_hours=Decimal("0.0"),
            dest_waiting_hours=Decimal("0.0"),
        )
