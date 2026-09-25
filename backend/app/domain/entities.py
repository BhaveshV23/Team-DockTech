"""
DockTech V1 — Domain Entities
Framework-independent dataclasses representing canonical domain objects.
Sources: DATA_DICTIONARY.md, ARCHITECTURE.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Port:
    """Port domain entity representing macro-level planning envelope."""
    port_id: str
    port_name: str
    country: str
    max_loa_m: float
    max_beam_m: float
    max_draft_m: float
    handling_rate_tpd: float
    typical_turnaround_hours: float
    source: str = "SYNTHETIC_GENERATOR_V1"
    data_type: str = "SYNTHETIC"


@dataclass(frozen=True)
class Berth:
    """Berth domain entity representing authoritative terminal operational constraints."""
    berth_id: str
    port_id: str
    berth_name: str
    commodity: str
    max_loa_m: float
    max_beam_m: float
    max_draft_m: float
    handling_rate_tpd: float
    source: str = "SYNTHETIC_GENERATOR_V1"
    data_type: str = "SYNTHETIC"


@dataclass(frozen=True)
class VesselClass:
    """Vessel class domain entity representing physical dimensions and payload capacity."""
    vessel_class_id: str
    vessel_class_name: str
    dwt_min_mt: float
    dwt_max_mt: float
    loa_m: float
    beam_m: float
    draft_m: float
    speed_knots: float
    cargo_capacity_mt: float
    fuel_consumption_mt_day: float
    source: str = "SYNTHETIC_GENERATOR_V1"
    data_type: str = "SYNTHETIC"


@dataclass(frozen=True)
class Route:
    """Route domain entity representing origin-destination trade lane."""
    route_id: str
    origin_port_id: str
    destination_port_id: str
    commodity: str
    distance_nm: float
    typical_sailing_days: float
    source: str = "SYNTHETIC_GENERATOR_V1"
    data_type: str = "SYNTHETIC"
