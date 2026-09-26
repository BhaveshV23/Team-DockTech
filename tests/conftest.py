"""Pytest configuration and canonical domain fixtures for DockTech V1 testing."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Dict, List
from uuid import uuid4

import pytest

from backend.app.domain.constants import Commodity, ContractHorizon, FreightUnit
from backend.app.domain.entities import Berth, CargoRequest, DecisionInputs, Port, Route, VesselClass


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"


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
        commodity=Commodity.THERMAL_COAL.value,
        max_loa_m=300.0,
        max_beam_m=50.0,
        max_draft_m=17.0,
        handling_rate_tpd=50000.0,
    )
    dest_berth = Berth(
        berth_id="B_PRT_COAL_01",
        port_id="IN_PRT",
        berth_name="Paradip Mechanised Coal Berth 1",
        commodity=Commodity.THERMAL_COAL.value,
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
        commodity=Commodity.THERMAL_COAL.value,
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
def sample_decision_inputs(sample_cargo_request, sample_vessels, sample_berths, sample_route):
    """Canonical base decision inputs for scenario analysis."""
    return DecisionInputs(
        cargo_request=sample_cargo_request,
        vessel_class=sample_vessels["panamax"],
        origin_berth=sample_berths["origin"],
        destination_berth=sample_berths["destination"],
        route=sample_route,
        base_freight_rate=18.50,
        freight_unit=FreightUnit.USD_PER_MT,
        base_vlsfo_price_usd_mt=620.0,
        origin_waiting_hours=12.0,
        destination_waiting_hours=36.0,
        cost_reference_date=date(2026, 9, 20),
        forecast_spread_pct=8.0,
    )


def _load_ports() -> Dict[str, Port]:
    ports = {}
    with open(DATA_REFERENCE_DIR / "ports.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = row["port_id"].strip()
            ports[pid] = Port(
                port_id=pid,
                port_name=row["port_name"].strip(),
                country=row["country"].strip(),
                max_loa_m=float(row["max_loa_m"]),
                max_beam_m=float(row["max_beam_m"]),
                max_draft_m=float(row["max_draft_m"]),
                handling_rate_tpd=float(row["handling_rate_tpd"]),
                typical_turnaround_hours=float(row["typical_turnaround_hours"]),
                source=row["source"].strip(),
                data_type=row["data_type"].strip(),
            )
    return ports


def _load_berths() -> Dict[str, Berth]:
    berths = {}
    with open(DATA_REFERENCE_DIR / "berths.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            bid = row["berth_id"].strip()
            berths[bid] = Berth(
                berth_id=bid,
                port_id=row["port_id"].strip(),
                berth_name=row["berth_name"].strip(),
                commodity=row["commodity"].strip(),
                max_loa_m=float(row["max_loa_m"]),
                max_beam_m=float(row["max_beam_m"]),
                max_draft_m=float(row["max_draft_m"]),
                handling_rate_tpd=float(row["handling_rate_tpd"]),
                source=row["source"].strip(),
                data_type=row["data_type"].strip(),
            )
    return berths


def _load_vessel_classes() -> Dict[str, VesselClass]:
    vessels = {}
    with open(DATA_REFERENCE_DIR / "vessel_classes.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            vc_id = row["vessel_class_id"].strip()
            vessels[vc_id] = VesselClass(
                vessel_class_id=vc_id,
                vessel_class_name=row["vessel_class_name"].strip(),
                dwt_min_mt=float(row["dwt_min_mt"]),
                dwt_max_mt=float(row["dwt_max_mt"]),
                loa_m=float(row["loa_m"]),
                beam_m=float(row["beam_m"]),
                draft_m=float(row["draft_m"]),
                speed_knots=float(row["speed_knots"]),
                cargo_capacity_mt=float(row["cargo_capacity_mt"]),
                fuel_consumption_mt_day=float(row["fuel_consumption_mt_day"]),
                source=row["source"].strip(),
                data_type=row["data_type"].strip(),
            )
    return vessels


def _load_routes() -> Dict[str, Route]:
    routes = {}
    with open(DATA_REFERENCE_DIR / "routes.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rid = row["route_id"].strip()
            routes[rid] = Route(
                route_id=rid,
                origin_port_id=row["origin_port_id"].strip(),
                destination_port_id=row["destination_port_id"].strip(),
                commodity=row["commodity"].strip(),
                distance_nm=float(row["distance_nm"]),
                typical_sailing_days=float(row["typical_sailing_days"]),
                source=row["source"].strip(),
                data_type=row["data_type"].strip(),
            )
    return routes


@pytest.fixture(scope="session")
def all_ports() -> Dict[str, Port]:
    return _load_ports()


@pytest.fixture(scope="session")
def all_berths() -> Dict[str, Berth]:
    return _load_berths()


@pytest.fixture(scope="session")
def all_vessel_classes() -> Dict[str, VesselClass]:
    return _load_vessel_classes()


@pytest.fixture(scope="session")
def all_routes() -> Dict[str, Route]:
    return _load_routes()


@pytest.fixture(scope="session")
def all_berths_list(all_berths) -> List[Berth]:
    return list(all_berths.values())


@pytest.fixture(scope="session")
def data_dir() -> Path:
    return DATA_REFERENCE_DIR


@pytest.fixture(scope="session")
def supramax(all_vessel_classes) -> VesselClass:
    """Supramax: loa=190m, beam=32.2m, draft=12.2m, cargo_capacity=53000 MT."""
    return all_vessel_classes["SUPRAMAX"]


@pytest.fixture(scope="session")
def capesize(all_vessel_classes) -> VesselClass:
    """Capesize: loa=292m, beam=45m, draft=18.2m, cargo_capacity=170000 MT."""
    return all_vessel_classes["CAPESIZE"]


@pytest.fixture(scope="session")
def panamax(all_vessel_classes) -> VesselClass:
    """Panamax: loa=225m, beam=32.3m, draft=14.2m, cargo_capacity=72000 MT."""
    return all_vessel_classes["PANAMAX"]


@pytest.fixture(scope="session")
def handysize(all_vessel_classes) -> VesselClass:
    """Handysize: loa=180m, beam=28.4m, draft=10.2m, cargo_capacity=32000 MT."""
    return all_vessel_classes["HANDYSIZE"]


@pytest.fixture(scope="session")
def newcastle_port(all_ports) -> Port:
    return all_ports["NEWCASTLE"]


@pytest.fixture(scope="session")
def paradip_port(all_ports) -> Port:
    return all_ports["PARADIP"]


@pytest.fixture(scope="session")
def haldia_port(all_ports) -> Port:
    return all_ports["HALDIA"]


@pytest.fixture(scope="session")
def gangavaram_port(all_ports) -> Port:
    return all_ports["GANGAVARAM"]


@pytest.fixture(scope="session")
def baltimore_port(all_ports) -> Port:
    """Baltimore has NO THERMAL_COAL berth."""
    return all_ports["BALTIMORE"]


@pytest.fixture(scope="session")
def taboneo_port(all_ports) -> Port:
    """Taboneo has NO COKING_COAL berth."""
    return all_ports["TABONEO"]


@pytest.fixture(scope="session")
def sagar_sandheads_port(all_ports) -> Port:
    """Sagar-Sandheads: very shallow with deep-draft rejection cases."""
    return all_ports["SAGAR_SANDHEADS"]
