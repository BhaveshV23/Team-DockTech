"""Unit tests for DockTech V1 Voyage Cost and Turnaround Calculation Engine."""

import pytest
from backend.app.domain.constants import Commodity, FreightUnit
from backend.app.domain.entities import Berth, Route, VesselClass
from backend.app.domain.voyage_cost import VoyageCostEngine


def test_sailing_days_calculation():
    """Verify sailing_days = distance_nm / (speed_knots * 24)."""
    # 5600 nm at 13 knots: 5600 / (13 * 24) = 5600 / 312 = 17.9487 days
    days = VoyageCostEngine.calculate_sailing_days(5600.0, 13.0)
    assert round(days, 4) == 17.9487


def test_required_voyages_calculation():
    """Verify ceil(cargo_volume / vessel_capacity)."""
    assert VoyageCostEngine.calculate_required_voyages(75000.0, 75000.0) == 1
    assert VoyageCostEngine.calculate_required_voyages(75001.0, 75000.0) == 2
    assert VoyageCostEngine.calculate_required_voyages(150000.0, 75000.0) == 2
    assert VoyageCostEngine.calculate_required_voyages(160000.0, 75000.0) == 3


def test_multi_voyage_cost_and_turnaround_scaling(
    sample_vessels, sample_berths, sample_route
):
    """Verify multi-voyage turnaround and delay scaling."""
    # 150,000 MT on a 75,000 MT Panamax requires 2 voyages
    cost = VoyageCostEngine.calculate_voyage_cost(
        cargo_volume_mt=150000.0,
        vessel_class=sample_vessels["panamax"],
        origin_berth=sample_berths["origin"],       # 50,000 tpd -> (150000/50000)*24 = 72h
        destination_berth=sample_berths["destination"], # 30,000 tpd -> (150000/30000)*24 = 120h
        route=sample_route,
        freight_rate=20.0,
        freight_unit=FreightUnit.USD_PER_MT,
        vlsfo_price_usd_mt=600.0,
        origin_waiting_hours=12.0,                  # (12 + 24) * 2 = 72h total waiting
        destination_waiting_hours=24.0,
        scenario_delay_hours=10.0,                  # 10 * 2 = 20h total scenario delay
    )

    assert cost.required_voyages == 2
    assert cost.origin_handling_hours_total == 72.0
    assert cost.destination_handling_hours_total == 120.0
    assert cost.waiting_hours_total == 72.0
    assert cost.scenario_delay_total == 20.0
    # Total turnaround = 72 + 120 + 72 + 20 = 284h
    assert cost.estimated_turnaround_hours == 284.0
    assert cost.turnaround_hours_per_voyage == 142.0

    # Total fuel cost for 2 voyages = 2 * (sailing_days * 28 * 600)
    sailing_days = 5600.0 / (13.0 * 24.0)
    expected_fuel = sailing_days * 28.0 * 600.0 * 2
    assert round(cost.total_fuel_cost_usd, 2) == round(expected_fuel, 2)

    # Expected freight cost = 150000 * 20 = 3,000,000 USD
    assert cost.expected_freight_cost == 3000000.0
    assert cost.expected_total_cost == round(3000000.0 + expected_fuel, 2)


def test_usd_per_mt_zero_arbitrary_demurrage(
    sample_vessels, sample_berths, sample_route
):
    """Verify that for USD_PER_MT, no arbitrary idle/demurrage monetary charge is added."""
    cost_no_delay = VoyageCostEngine.calculate_voyage_cost(
        cargo_volume_mt=75000.0,
        vessel_class=sample_vessels["panamax"],
        origin_berth=sample_berths["origin"],
        destination_berth=sample_berths["destination"],
        route=sample_route,
        freight_rate=18.0,
        freight_unit=FreightUnit.USD_PER_MT,
        vlsfo_price_usd_mt=600.0,
        origin_waiting_hours=0.0,
        destination_waiting_hours=0.0,
        scenario_delay_hours=0.0,
    )

    cost_with_delay = VoyageCostEngine.calculate_voyage_cost(
        cargo_volume_mt=75000.0,
        vessel_class=sample_vessels["panamax"],
        origin_berth=sample_berths["origin"],
        destination_berth=sample_berths["destination"],
        route=sample_route,
        freight_rate=18.0,
        freight_unit=FreightUnit.USD_PER_MT,
        vlsfo_price_usd_mt=600.0,
        origin_waiting_hours=48.0,
        destination_waiting_hours=48.0,
        scenario_delay_hours=48.0,
    )

    # Freight cost and sea fuel cost must remain identical for USD_PER_MT (only turnaround changes)
    assert cost_with_delay.expected_freight_cost == cost_no_delay.expected_freight_cost
    assert cost_with_delay.total_fuel_cost_usd == cost_no_delay.total_fuel_cost_usd
    assert cost_with_delay.expected_total_cost == cost_no_delay.expected_total_cost
    assert cost_with_delay.estimated_turnaround_hours > cost_no_delay.estimated_turnaround_hours


def test_usd_per_day_monetizes_port_days(
    sample_vessels, sample_berths, sample_route
):
    """Verify that for USD_PER_DAY, port waiting and delay expand vessel-days and charter hire."""
    cost_low_delay = VoyageCostEngine.calculate_voyage_cost(
        cargo_volume_mt=75000.0,
        vessel_class=sample_vessels["panamax"],
        origin_berth=sample_berths["origin"],
        destination_berth=sample_berths["destination"],
        route=sample_route,
        freight_rate=20000.0,  # 20k/day
        freight_unit=FreightUnit.USD_PER_DAY,
        vlsfo_price_usd_mt=600.0,
        origin_waiting_hours=0.0,
        destination_waiting_hours=0.0,
        scenario_delay_hours=0.0,
    )

    cost_high_delay = VoyageCostEngine.calculate_voyage_cost(
        cargo_volume_mt=75000.0,
        vessel_class=sample_vessels["panamax"],
        origin_berth=sample_berths["origin"],
        destination_berth=sample_berths["destination"],
        route=sample_route,
        freight_rate=20000.0,
        freight_unit=FreightUnit.USD_PER_DAY,
        vlsfo_price_usd_mt=600.0,
        origin_waiting_hours=24.0,
        destination_waiting_hours=24.0,
        scenario_delay_hours=48.0,  # 96h extra = 4 extra port days
    )

    extra_port_days = (96.0) / 24.0  # 4.0 days
    expected_extra_hire = extra_port_days * 20000.0  # $80,000
    actual_extra_hire = cost_high_delay.expected_freight_cost - cost_low_delay.expected_freight_cost
    assert round(actual_extra_hire, 2) == round(expected_extra_hire, 2)


def test_invalid_parameters_raise_value_error(
    sample_vessels, sample_berths, sample_route
):
    """Verify negative or zero inputs raise descriptive ValueError."""
    with pytest.raises(ValueError, match="strictly positive"):
        VoyageCostEngine.calculate_sailing_days(5000.0, 0.0)

    with pytest.raises(ValueError, match="strictly positive"):
        VoyageCostEngine.calculate_required_voyages(0.0, 75000.0)

    with pytest.raises(ValueError, match="strictly positive"):
        VoyageCostEngine.calculate_voyage_cost(
            cargo_volume_mt=75000.0,
            vessel_class=sample_vessels["panamax"],
            origin_berth=sample_berths["origin"],
            destination_berth=sample_berths["destination"],
            route=sample_route,
            freight_rate=-5.0,  # Invalid
            freight_unit=FreightUnit.USD_PER_MT,
            vlsfo_price_usd_mt=600.0,
            origin_waiting_hours=0.0,
            destination_waiting_hours=0.0,
        )
