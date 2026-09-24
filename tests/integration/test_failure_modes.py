"""Negative and edge-case failure mode tests for DockTech V1 QA."""

from datetime import date
from uuid import uuid4
import pytest

from backend.app.domain.constants import Commodity, CongestionLevel, ContractHorizon, FreightUnit, RiskLevel
from backend.app.domain.entities import Berth, CargoRequest, DecisionInputs, Route, VesselClass
from backend.app.domain.voyage_cost import VoyageCostEngine
from backend.app.services.scenario_service import ScenarioService


def test_zero_cargo_volume_fails_safely():
    """Zero cargo volume must raise ValueError."""
    with pytest.raises(ValueError, match="strictly positive"):
        VoyageCostEngine.calculate_required_voyages(0.0, 75000.0)


def test_negative_cargo_volume_fails_safely():
    """Negative cargo volume must raise ValueError."""
    with pytest.raises(ValueError, match="strictly positive"):
        VoyageCostEngine.calculate_required_voyages(-50000.0, 75000.0)


def test_zero_vessel_speed_fails_safely():
    """Zero vessel speed must raise ValueError."""
    with pytest.raises(ValueError, match="strictly positive"):
        VoyageCostEngine.calculate_sailing_days(5600.0, 0.0)


def test_negative_waiting_hours_fails_safely(sample_vessels, sample_berths, sample_route):
    """Negative waiting hours must raise ValueError."""
    with pytest.raises(ValueError, match="cannot be negative"):
        VoyageCostEngine.calculate_voyage_cost(
            cargo_volume_mt=75000.0,
            vessel_class=sample_vessels["panamax"],
            origin_berth=sample_berths["origin"],
            destination_berth=sample_berths["destination"],
            route=sample_route,
            freight_rate=18.50,
            freight_unit=FreightUnit.USD_PER_MT,
            vlsfo_price_usd_mt=620.0,
            origin_waiting_hours=-10.0,
            destination_waiting_hours=20.0,
        )


def test_very_large_cargo_volume_multi_voyage_accuracy(
    sample_vessels, sample_berths, sample_route
):
    """Large cargo parcel (250,000 MT on 75,000 MT Panamax) requires 4 voyages."""
    req_voyages = VoyageCostEngine.calculate_required_voyages(250000.0, 75000.0)
    assert req_voyages == 4

    cost = VoyageCostEngine.calculate_voyage_cost(
        cargo_volume_mt=250000.0,
        vessel_class=sample_vessels["panamax"],
        origin_berth=sample_berths["origin"],
        destination_berth=sample_berths["destination"],
        route=sample_route,
        freight_rate=18.0,
        freight_unit=FreightUnit.USD_PER_MT,
        vlsfo_price_usd_mt=600.0,
        origin_waiting_hours=12.0,
        destination_waiting_hours=24.0,
        scenario_delay_hours=24.0,
    )

    assert cost.required_voyages == 4
    # Total waiting hours = (12 + 24) * 4 = 144h
    assert cost.waiting_hours_total == 144.0
    # Total scenario delay = 24 * 4 = 96h
    assert cost.scenario_delay_total == 96.0
    assert cost.expected_freight_cost == 250000.0 * 18.0
