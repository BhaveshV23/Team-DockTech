"""Pytest configuration and canonical domain fixtures for DockTech V1 testing."""

from datetime import date, datetime
from uuid import uuid4
import pytest

from backend.app.domain.constants import (
    Commodity,
    CongestionLevel,
    ContractHorizon,
    FreightUnit,
    ScenarioType,
)
from backend.app.domain.entities import (
    Berth,
    CargoRequest,
    DecisionInputs,
    Port,
    Route,
    ScenarioDefault,
    VesselClass,
)


@pytest.fixture
def sample_ports():
    """Canonical test ports."""
    origin = Port(
        port_id="AU_NCL",
        port_name="Port of Newcastle",
        country="Australia",
        max_loa_m=300.0,
        max_beam_m=50.0,
        max_draft_m=17.5,
        handling_rate_tpd=45000.0,
        typical_turnaround_hours=48.0,
    )
    destination = Port(
        port_id="IN_PRT",
        port_name="Paradip Port",
        country="India",
        max_loa_m=280.0,
        max_beam_m=45.0,
        max_draft_m=16.0,
        handling_rate_tpd=35000.0,
        typical_turnaround_hours=72.0,
    )
    return {"origin": origin, "destination": destination}


@pytest.fixture
def sample_berths():
    """Canonical test berths with commodity specialization."""
    origin_berth = Berth(
        berth_id="B_NCL_COAL_01",
        port_id="AU_NCL",
        berth_name="Kooragang Coal Terminal 1",
        commodity=Commodity.THERMAL_COAL,
        max_loa_m=300.0,
        max_beam_m=50.0,
        max_draft_m=17.0,
        handling_rate_tpd=50000.0,
    )
    dest_berth = Berth(
        berth_id="B_PRT_COAL_01",
        port_id="IN_PRT",
        berth_name="Paradip Mechanised Coal Berth 1",
        commodity=Commodity.THERMAL_COAL,
        max_loa_m=260.0,
        max_beam_m=43.0,
        max_draft_m=15.0,
        handling_rate_tpd=30000.0,
    )
    return {"origin": origin_berth, "destination": dest_berth}


@pytest.fixture
def sample_vessels():
    """Canonical vessel classes for bulk coal trade."""
    panamax = VesselClass(
        vessel_class_id="PANAMAX",
        vessel_class_name="Panamax / Kamsarmax",
        dwt_min_mt=70000.0,
        dwt_max_mt=85000.0,
        loa_m=225.0,
        beam_m=32.26,
        draft_m=14.2,
        speed_knots=13.0,
        cargo_capacity_mt=75000.0,
        fuel_consumption_mt_day=28.0,
    )
    capesize = VesselClass(
        vessel_class_id="CAPESIZE",
        vessel_class_name="Capesize",
        dwt_min_mt=160000.0,
        dwt_max_mt=210000.0,
        loa_m=292.0,
        beam_m=45.0,
        draft_m=18.0,
        speed_knots=14.0,
        cargo_capacity_mt=170000.0,
        fuel_consumption_mt_day=45.0,
    )
    return {"panamax": panamax, "capesize": capesize}


@pytest.fixture
def sample_route():
    """Canonical representative route: Newcastle to Paradip."""
    return Route(
        route_id="R_NCL_PRT_TC",
        origin_port_id="AU_NCL",
        destination_port_id="IN_PRT",
        commodity=Commodity.THERMAL_COAL,
        distance_nm=5600.0,
        typical_sailing_days=17.95,
    )


@pytest.fixture
def sample_cargo_request():
    """Canonical cargo request (75,000 MT Thermal Coal)."""
    return CargoRequest(
        cargo_request_id=uuid4(),
        user_id=uuid4(),
        commodity=Commodity.THERMAL_COAL,
        cargo_volume_mt=75000.0,
        origin_port_id="AU_NCL",
        destination_port_id="IN_PRT",
        laycan_start_date=date(2026, 10, 1),
        laycan_end_date=date(2026, 10, 31),
        contract_horizon=ContractHorizon.SPOT,
    )


@pytest.fixture
def sample_decision_inputs(
    sample_cargo_request, sample_vessels, sample_berths, sample_route
):
    """Canonical base decision inputs for scenario analysis."""
    return DecisionInputs(
        cargo_request=sample_cargo_request,
        vessel_class=sample_vessels["panamax"],
        origin_berth=sample_berths["origin"],
        destination_berth=sample_berths["destination"],
        route=sample_route,
        base_freight_rate=18.50,  # USD/MT
        freight_unit=FreightUnit.USD_PER_MT,
        base_vlsfo_price_usd_mt=620.0,
        origin_waiting_hours=12.0,
        destination_waiting_hours=36.0,
        cost_reference_date=date(2026, 9, 20),
        forecast_spread_pct=8.0,
    )
