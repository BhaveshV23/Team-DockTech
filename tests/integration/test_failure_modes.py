"""Negative and edge-case failure-mode tests for the canonical cost engine."""

from decimal import Decimal

import pytest

from backend.app.domain.cost import CostInputs, FreightUnit, calculate_required_voyages, calculate_sailing_days


def test_zero_cargo_volume_fails_safely():
    """Zero cargo volume must raise ValueError."""
    with pytest.raises(ValueError, match="strictly positive"):
        calculate_required_voyages(Decimal("0"), Decimal("75000"))


def test_negative_cargo_volume_fails_safely():
    """Negative cargo volume must raise ValueError."""
    with pytest.raises(ValueError, match="strictly positive"):
        calculate_required_voyages(Decimal("-50000"), Decimal("75000"))


def test_zero_vessel_speed_fails_safely():
    """Zero vessel speed must raise ValueError."""
    with pytest.raises(ValueError, match="strictly positive"):
        calculate_sailing_days(Decimal("5600"), Decimal("0"))


def test_negative_waiting_hours_fails_safely(sample_vessels, sample_berths, sample_route):
    """Negative waiting hours must raise ValueError."""
    with pytest.raises(ValueError, match="non-negative"):
        CostInputs(
            cargo_volume_mt=Decimal("75000"),
            distance_nm=Decimal(str(sample_route.distance_nm)),
            vessel_cargo_capacity_mt=Decimal(str(sample_vessels["panamax"].cargo_capacity_mt)),
            vessel_speed_knots=Decimal(str(sample_vessels["panamax"].speed_knots)),
            vessel_fuel_consumption_tpd=Decimal(str(sample_vessels["panamax"].fuel_consumption_mt_day)),
            freight_rate_value=Decimal("18.50"),
            freight_unit=FreightUnit.USD_PER_MT,
            vlsfo_price_usd_per_mt=Decimal("620.0"),
            origin_handling_rate_tpd=Decimal(str(sample_berths["origin"].handling_rate_tpd)),
            dest_handling_rate_tpd=Decimal(str(sample_berths["destination"].handling_rate_tpd)),
            origin_waiting_hours=Decimal("-10.0"),
            dest_waiting_hours=Decimal("20.0"),
        )


def test_very_large_cargo_volume_multi_voyage_accuracy(sample_vessels, sample_berths, sample_route):
    """Large cargo parcel (250,000 MT on 75,000 MT Panamax) requires 4 voyages."""
    req_voyages = calculate_required_voyages(Decimal("250000"), Decimal("75000"))
    assert req_voyages == 4

    inputs = CostInputs(
        cargo_volume_mt=Decimal("250000"),
        distance_nm=Decimal(str(sample_route.distance_nm)),
        vessel_cargo_capacity_mt=Decimal(str(sample_vessels["panamax"].cargo_capacity_mt)),
        vessel_speed_knots=Decimal(str(sample_vessels["panamax"].speed_knots)),
        vessel_fuel_consumption_tpd=Decimal(str(sample_vessels["panamax"].fuel_consumption_mt_day)),
        freight_rate_value=Decimal("18.0"),
        freight_unit=FreightUnit.USD_PER_MT,
        vlsfo_price_usd_per_mt=Decimal("600.0"),
        origin_handling_rate_tpd=Decimal(str(sample_berths["origin"].handling_rate_tpd)),
        dest_handling_rate_tpd=Decimal(str(sample_berths["destination"].handling_rate_tpd)),
        origin_waiting_hours=Decimal("12.0"),
        dest_waiting_hours=Decimal("24.0"),
        scenario_delay_hours=Decimal("24.0"),
    )

    result = __import__('backend.app.domain.cost.engine', fromlist=['calculate_cost']).calculate_cost(
        inputs, __import__('datetime').date(2025, 12, 31)
    )
    assert result.required_voyages == 4
    assert result.waiting_hours_total == Decimal("144.0")
    assert result.scenario_delay_hours_total == Decimal("96.0")
    assert result.expected_freight_cost == Decimal("250000.0") * Decimal("18.0")
