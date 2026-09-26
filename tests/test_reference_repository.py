"""
DockTech V1 — Cost Engine Repository & Lookup Unit Tests
=========================================================
Unit tests verifying canonical reference repository lookups, berth handling
rate determination, latest-valid VLSFO fuel price retrieval, port activity
waiting hour retrieval, freight rate lookup, and CostInputResolver construction.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path
import pytest

from backend.app.domain.cost import (
    CostInputResolver,
    CostInputs,
    FreightUnit,
    InsufficientFeasibilityDataError,
    InsufficientFreightDataError,
    InsufficientFuelPriceDataError,
    InsufficientPortActivityDataError,
    RouteNotFoundError,
    VesselClassNotFoundError,
    calculate_cost,
)
from backend.app.repositories.reference_repository import (
    BerthRecord,
    CSVReferenceRepository,
    FuelPriceRecord,
    PortActivityRecord,
    RouteRecord,
    VesselClassRecord,
)


@pytest.fixture
def reference_repo() -> CSVReferenceRepository:
    repo_root = Path(__file__).resolve().parent.parent
    data_dir = repo_root / "data" / "reference"
    return CSVReferenceRepository(data_dir=data_dir)


@pytest.fixture
def cost_resolver(reference_repo: CSVReferenceRepository) -> CostInputResolver:
    return CostInputResolver(repository=reference_repo)


# ==============================================================================
# 1. REFERENCE REPOSITORY BASIC LOOKUP TESTS
# ==============================================================================

def test_get_route_valid(reference_repo: CSVReferenceRepository):
    # Newcastle to Paradip thermal coal
    route = reference_repo.get_route(
        origin_port_id="NEWCASTLE",
        destination_port_id="PARADIP",
        commodity="THERMAL_COAL",
    )
    assert route.route_id == "NEWCASTLE_PARADIP_THERMAL"
    assert route.distance_nm == Decimal("5350.0")
    assert route.commodity == "THERMAL_COAL"


def test_get_route_invalid_fails(reference_repo: CSVReferenceRepository):
    with pytest.raises(RouteNotFoundError):
        reference_repo.get_route(
            origin_port_id="NON_EXISTENT",
            destination_port_id="PARADIP",
            commodity="THERMAL_COAL",
        )


def test_get_vessel_class_valid(reference_repo: CSVReferenceRepository):
    vessel = reference_repo.get_vessel_class("PANAMAX")
    assert vessel.vessel_class_id == "PANAMAX"
    assert vessel.cargo_capacity_mt == Decimal("72000.0")
    assert vessel.speed_knots == Decimal("14.0")
    assert vessel.fuel_consumption_mt_day == Decimal("34.0")


def test_get_vessel_class_invalid_fails(reference_repo: CSVReferenceRepository):
    with pytest.raises(VesselClassNotFoundError):
        reference_repo.get_vessel_class("UNKNOWN_VESSEL")


# ==============================================================================
# 2. BERTH COMPATIBILITY & HANDLING RATE TESTS
# ==============================================================================

def test_compatible_berth_handling_rate_panamax(reference_repo: CSVReferenceRepository):
    panamax = reference_repo.get_vessel_class("PANAMAX")
    # Paradip handling rate for thermal coal Panamax
    rate_dest = reference_repo.get_compatible_berth_handling_rate(
        port_id="PARADIP",
        commodity="THERMAL_COAL",
        vessel_class=panamax,
    )
    assert rate_dest > Decimal("0")
    assert rate_dest == Decimal("28000.0")

    # Newcastle handling rate for thermal coal Panamax
    rate_orig = reference_repo.get_compatible_berth_handling_rate(
        port_id="NEWCASTLE",
        commodity="THERMAL_COAL",
        vessel_class=panamax,
    )
    assert rate_orig == Decimal("40000.0")


def test_berth_incompatible_vessel_fails(reference_repo: CSVReferenceRepository):
    # Capesize draft (18.2m) exceeds Paradip thermal berth (14.0m)
    capesize = reference_repo.get_vessel_class("CAPESIZE")
    with pytest.raises(InsufficientFeasibilityDataError):
        reference_repo.get_compatible_berth_handling_rate(
            port_id="PARADIP",
            commodity="THERMAL_COAL",
            vessel_class=capesize,
        )


# ==============================================================================
# 3. DATE-AWARE TIME-SERIES LOOKUP TESTS
# ==============================================================================

def test_latest_vlsfo_price_lookup(reference_repo: CSVReferenceRepository):
    # Lookup on 2025-06-15
    ref_date = datetime.date(2025, 6, 15)
    price = reference_repo.get_latest_vlsfo_price(cost_reference_date=ref_date)
    assert price > Decimal("0")

    # Past cutoff before any observations (e.g. 2020-01-01) should fail
    past_date = datetime.date(2020, 1, 1)
    with pytest.raises(InsufficientFuelPriceDataError):
        reference_repo.get_latest_vlsfo_price(cost_reference_date=past_date)


def test_latest_port_waiting_hours_lookup(reference_repo: CSVReferenceRepository):
    ref_date = datetime.date(2025, 6, 15)
    waiting_orig = reference_repo.get_latest_port_waiting_hours(
        port_id="NEWCASTLE", cost_reference_date=ref_date
    )
    assert waiting_orig >= Decimal("0")

    waiting_dest = reference_repo.get_latest_port_waiting_hours(
        port_id="PARADIP", cost_reference_date=ref_date
    )
    assert waiting_dest >= Decimal("0")

    # Future/invalid port
    with pytest.raises(InsufficientPortActivityDataError):
        reference_repo.get_latest_port_waiting_hours(
            port_id="NON_EXISTENT", cost_reference_date=ref_date
        )


def test_latest_freight_rate_lookup(reference_repo: CSVReferenceRepository):
    ref_date = datetime.date(2025, 6, 15)
    rate_mt = reference_repo.get_latest_freight_rate(
        route_id="NEWCASTLE_PARADIP_THERMAL",
        vessel_class_id="PANAMAX",
        freight_unit=FreightUnit.USD_PER_MT,
        cost_reference_date=ref_date,
    )
    assert rate_mt > Decimal("0")

    rate_day = reference_repo.get_latest_freight_rate(
        route_id="NEWCASTLE_PARADIP_THERMAL",
        vessel_class_id="PANAMAX",
        freight_unit=FreightUnit.USD_PER_DAY,
        cost_reference_date=ref_date,
    )
    assert rate_day > Decimal("0")
    assert rate_day > rate_mt  # Day rate (e.g. ~$15,000) vs MT rate (e.g. ~$14)


# ==============================================================================
# 4. COST INPUT RESOLVER END-TO-END TESTS
# ==============================================================================

def test_cost_input_resolver_success(cost_resolver: CostInputResolver):
    ref_date = datetime.date(2025, 6, 15)
    inputs = cost_resolver.resolve_cost_inputs(
        cargo_volume_mt=Decimal("75000.0"),
        origin_port_id="NEWCASTLE",
        destination_port_id="PARADIP",
        commodity="THERMAL_COAL",
        vessel_class_id="PANAMAX",
        freight_unit="USD_PER_MT",
        cost_reference_date=ref_date,
    )

    assert isinstance(inputs, CostInputs)
    assert inputs.cargo_volume_mt == Decimal("75000.0")
    assert inputs.distance_nm == Decimal("5350.0")
    assert inputs.vessel_cargo_capacity_mt == Decimal("72000.0")
    assert inputs.origin_handling_rate_tpd == Decimal("40000.0")
    assert inputs.dest_handling_rate_tpd == Decimal("28000.0")
    assert inputs.vlsfo_price_usd_per_mt > Decimal("0")
    assert inputs.origin_waiting_hours >= Decimal("0")
    assert inputs.dest_waiting_hours >= Decimal("0")
    assert inputs.freight_rate_value > Decimal("0")

    # Run calculation through Cost Engine (75,000 MT on 72,000 MT Panamax = 2 voyages)
    result = calculate_cost(inputs, cost_reference_date=ref_date)
    assert result.required_voyages == 2
    assert result.expected_freight_cost > Decimal("0")
    assert result.total_fuel_cost_usd > Decimal("0")
    assert result.expected_total_cost > Decimal("0")
    assert result.effective_cost_per_mt > Decimal("0")


def test_cost_input_resolver_deterministic_repeated_calls(cost_resolver: CostInputResolver):
    ref_date = datetime.date(2025, 6, 15)
    inputs_1 = cost_resolver.resolve_cost_inputs(
        cargo_volume_mt=Decimal("75000.0"),
        origin_port_id="NEWCASTLE",
        destination_port_id="PARADIP",
        commodity="THERMAL_COAL",
        vessel_class_id="PANAMAX",
        freight_unit="USD_PER_MT",
        cost_reference_date=ref_date,
    )

    inputs_2 = cost_resolver.resolve_cost_inputs(
        cargo_volume_mt=Decimal("75000.0"),
        origin_port_id="NEWCASTLE",
        destination_port_id="PARADIP",
        commodity="THERMAL_COAL",
        vessel_class_id="PANAMAX",
        freight_unit="USD_PER_MT",
        cost_reference_date=ref_date,
    )

    assert inputs_1 == inputs_2
