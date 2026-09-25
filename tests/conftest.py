"""
DockTech V1 — Test Fixtures & Shared Helpers
Provides in-memory test data from the canonical CSV datasets (no external DB required).
All fixtures are derived from data/reference/*.csv — never hardcoded synthetic replacements.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

import pytest

from backend.app.domain.entities import Berth, Port, VesselClass, Route


# ---------------------------------------------------------------------------
# Project root & data directory resolution
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"


# ---------------------------------------------------------------------------
# CSV Loaders
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Session-scoped fixtures (load once, reused across all tests)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Convenience fixtures for specific entities used across tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def supramax(all_vessel_classes) -> VesselClass:
    """Supramax: loa=190m, beam=32.2m, draft=12.2m, cargo_capacity=53000 MT"""
    return all_vessel_classes["SUPRAMAX"]


@pytest.fixture(scope="session")
def capesize(all_vessel_classes) -> VesselClass:
    """Capesize: loa=292m, beam=45m, draft=18.2m, cargo_capacity=170000 MT — rejected at shallow ports"""
    return all_vessel_classes["CAPESIZE"]


@pytest.fixture(scope="session")
def panamax(all_vessel_classes) -> VesselClass:
    """Panamax: loa=225m, beam=32.3m, draft=14.2m, cargo_capacity=72000 MT"""
    return all_vessel_classes["PANAMAX"]


@pytest.fixture(scope="session")
def handysize(all_vessel_classes) -> VesselClass:
    """Handysize: loa=180m, beam=28.4m, draft=10.2m, cargo_capacity=32000 MT"""
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
    """Baltimore has NO THERMAL_COAL berth — used for INSUFFICIENT_FEASIBILITY_DATA tests."""
    return all_ports["BALTIMORE"]


@pytest.fixture(scope="session")
def taboneo_port(all_ports) -> Port:
    """Taboneo has NO COKING_COAL berth — used for INSUFFICIENT_FEASIBILITY_DATA tests."""
    return all_ports["TABONEO"]


@pytest.fixture(scope="session")
def sagar_sandheads_port(all_ports) -> Port:
    """Sagar-Sandheads: very shallow (11.5m draft) — rejects deep-drafted vessels."""
    return all_ports["SAGAR_SANDHEADS"]
