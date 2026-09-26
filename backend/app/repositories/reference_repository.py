"""
DockTech V1 — Reference Data Repository Protocols & Concrete Implementations
==============================================================================
Provides strongly typed data access abstractions and memory/CSV/database-backed
implementations for retrieving canonical maritime reference data required by the
Cost Engine.

Authoritative Source-of-Truth Documents:
  1. PRD.md
  2. DATA_DICTIONARY.md (Frozen Canonical Contracts)
  3. ARCHITECTURE.md (Repository Layer Isolation)
  4. C1 Cost Engine Contract

Guarantees:
  - Strict Protocol definitions for swappable persistence (CSV seed, SQL, Mock).
  - Deterministic lookup semantics using exact cost reference date filtering.
  - Fail-safe structured domain errors (RouteNotFound, InsufficientFuel, etc.).
"""

from __future__ import annotations

import csv
import datetime
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Sequence

from backend.app.domain.cost.errors import (
    InsufficientFeasibilityDataError,
    InsufficientFreightDataError,
    InsufficientFuelPriceDataError,
    InsufficientPortActivityDataError,
    RouteNotFoundError,
    VesselClassNotFoundError,
)
from backend.app.domain.cost.models import FreightUnit


# ==============================================================================
# 1. REFERENCE RECORD DATA STRUCTURES
# ==============================================================================

@dataclass(frozen=True)
class PortRecord:
    port_id: str
    port_name: str
    country: str
    max_loa_m: Decimal
    max_beam_m: Decimal
    max_draft_m: Decimal
    handling_rate_tpd: Decimal
    typical_turnaround_hours: Decimal
    source: str
    data_type: str


@dataclass(frozen=True)
class BerthRecord:
    berth_id: str
    port_id: str
    berth_name: str
    commodity: str
    max_loa_m: Decimal
    max_beam_m: Decimal
    max_draft_m: Decimal
    handling_rate_tpd: Decimal
    source: str
    data_type: str


@dataclass(frozen=True)
class VesselClassRecord:
    vessel_class_id: str
    vessel_class_name: str
    dwt_min_mt: Decimal
    dwt_max_mt: Decimal
    loa_m: Decimal
    beam_m: Decimal
    draft_m: Decimal
    speed_knots: Decimal
    cargo_capacity_mt: Decimal
    fuel_consumption_mt_day: Decimal
    source: str
    data_type: str


@dataclass(frozen=True)
class RouteRecord:
    route_id: str
    origin_port_id: str
    destination_port_id: str
    commodity: str
    distance_nm: Decimal
    typical_sailing_days: Decimal
    source: str
    data_type: str


@dataclass(frozen=True)
class FreightRateRecord:
    freight_rate_id: str
    observation_date: datetime.date
    route_id: str
    vessel_class_id: str
    freight_value: Decimal
    freight_unit: FreightUnit
    currency: str
    data_type: str
    source: str


@dataclass(frozen=True)
class FuelPriceRecord:
    fuel_price_id: str
    observation_date: datetime.date
    fuel_type: str
    price_value: Decimal
    currency: str
    unit: str
    data_type: str
    source: str


@dataclass(frozen=True)
class PortActivityRecord:
    activity_id: str
    observation_date: datetime.date
    port_id: str
    vessel_arrivals: int
    average_waiting_hours: Decimal
    average_turnaround_hours: Decimal
    congestion_level: str
    source: str
    data_type: str


# ==============================================================================
# 2. REPOSITORY PROTOCOL DEFINITION
# ==============================================================================

class ReferenceRepositoryProtocol(Protocol):
    """Abstract interface for querying DockTech canonical reference datasets."""

    def get_route(
        self, origin_port_id: str, destination_port_id: str, commodity: str
    ) -> RouteRecord:
        ...

    def get_vessel_class(self, vessel_class_id: str) -> VesselClassRecord:
        ...

    def get_compatible_berth_handling_rate(
        self,
        port_id: str,
        commodity: str,
        vessel_class: VesselClassRecord,
    ) -> Decimal:
        ...

    def get_latest_vlsfo_price(
        self, cost_reference_date: datetime.date
    ) -> Decimal:
        ...

    def get_latest_port_waiting_hours(
        self, port_id: str, cost_reference_date: datetime.date
    ) -> Decimal:
        ...

    def get_latest_freight_rate(
        self,
        route_id: str,
        vessel_class_id: str,
        freight_unit: FreightUnit,
        cost_reference_date: datetime.date,
    ) -> Decimal:
        ...


# ==============================================================================
# 3. CSV REFERENCE DATA REPOSITORY IMPLEMENTATION
# ==============================================================================

class CSVReferenceRepository:
    """
    In-memory indexed reference repository loaded directly from canonical CSV datasets.
    Provides fast, deterministic, reproducible data access without network overhead.
    """

    def __init__(self, data_dir: Path | str) -> None:
        self.data_dir = Path(data_dir)
        self._routes: Dict[tuple[str, str, str], RouteRecord] = {}
        self._vessel_classes: Dict[str, VesselClassRecord] = {}
        self._berths_by_port_comm: Dict[tuple[str, str], List[BerthRecord]] = {}
        self._vlsfo_prices: List[FuelPriceRecord] = []
        self._port_activities: Dict[str, List[PortActivityRecord]] = {}
        self._freight_rates: Dict[tuple[str, str, str], List[FreightRateRecord]] = {}
        self._load_all()

    def _load_all(self) -> None:
        self._load_routes()
        self._load_vessel_classes()
        self._load_berths()
        self._load_fuel_prices()
        self._load_port_activity()
        self._load_freight_rates()

    def _load_routes(self) -> None:
        path = self.data_dir / "routes.csv"
        with open(path, mode="r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                rec = RouteRecord(
                    route_id=row["route_id"].strip(),
                    origin_port_id=row["origin_port_id"].strip(),
                    destination_port_id=row["destination_port_id"].strip(),
                    commodity=row["commodity"].strip(),
                    distance_nm=Decimal(row["distance_nm"]),
                    typical_sailing_days=Decimal(row["typical_sailing_days"]),
                    source=row["source"].strip(),
                    data_type=row["data_type"].strip(),
                )
                self._routes[(rec.origin_port_id, rec.destination_port_id, rec.commodity)] = rec

    def _load_vessel_classes(self) -> None:
        path = self.data_dir / "vessel_classes.csv"
        with open(path, mode="r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                rec = VesselClassRecord(
                    vessel_class_id=row["vessel_class_id"].strip(),
                    vessel_class_name=row["vessel_class_name"].strip(),
                    dwt_min_mt=Decimal(row["dwt_min_mt"]),
                    dwt_max_mt=Decimal(row["dwt_max_mt"]),
                    loa_m=Decimal(row["loa_m"]),
                    beam_m=Decimal(row["beam_m"]),
                    draft_m=Decimal(row["draft_m"]),
                    speed_knots=Decimal(row["speed_knots"]),
                    cargo_capacity_mt=Decimal(row["cargo_capacity_mt"]),
                    fuel_consumption_mt_day=Decimal(row["fuel_consumption_mt_day"]),
                    source=row["source"].strip(),
                    data_type=row["data_type"].strip(),
                )
                self._vessel_classes[rec.vessel_class_id] = rec

    def _load_berths(self) -> None:
        path = self.data_dir / "berths.csv"
        with open(path, mode="r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                rec = BerthRecord(
                    berth_id=row["berth_id"].strip(),
                    port_id=row["port_id"].strip(),
                    berth_name=row["berth_name"].strip(),
                    commodity=row["commodity"].strip(),
                    max_loa_m=Decimal(row["max_loa_m"]),
                    max_beam_m=Decimal(row["max_beam_m"]),
                    max_draft_m=Decimal(row["max_draft_m"]),
                    handling_rate_tpd=Decimal(row["handling_rate_tpd"]),
                    source=row["source"].strip(),
                    data_type=row["data_type"].strip(),
                )
                key = (rec.port_id, rec.commodity)
                if key not in self._berths_by_port_comm:
                    self._berths_by_port_comm[key] = []
                self._berths_by_port_comm[key].append(rec)

    def _load_fuel_prices(self) -> None:
        path = self.data_dir / "fuel_prices.csv"
        with open(path, mode="r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                fuel_type = row["fuel_type"].strip()
                if fuel_type == "VLSFO":
                    obs_date = datetime.date.fromisoformat(row["observation_date"].strip())
                    rec = FuelPriceRecord(
                        fuel_price_id=row["fuel_price_id"].strip(),
                        observation_date=obs_date,
                        fuel_type=fuel_type,
                        price_value=Decimal(row["price_value"]),
                        currency=row["currency"].strip(),
                        unit=row["unit"].strip(),
                        data_type=row["data_type"].strip(),
                        source=row["source"].strip(),
                    )
                    self._vlsfo_prices.append(rec)
        self._vlsfo_prices.sort(key=lambda r: r.observation_date)

    def _load_port_activity(self) -> None:
        path = self.data_dir / "port_activity.csv"
        with open(path, mode="r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                port_id = row["port_id"].strip()
                obs_date = datetime.date.fromisoformat(row["observation_date"].strip())
                rec = PortActivityRecord(
                    activity_id=row["activity_id"].strip(),
                    observation_date=obs_date,
                    port_id=port_id,
                    vessel_arrivals=int(row["vessel_arrivals"]),
                    average_waiting_hours=Decimal(row["average_waiting_hours"]),
                    average_turnaround_hours=Decimal(row["average_turnaround_hours"]),
                    congestion_level=row["congestion_level"].strip(),
                    source=row["source"].strip(),
                    data_type=row["data_type"].strip(),
                )
                if port_id not in self._port_activities:
                    self._port_activities[port_id] = []
                self._port_activities[port_id].append(rec)
        for port_id in self._port_activities:
            self._port_activities[port_id].sort(key=lambda r: r.observation_date)

    def _load_freight_rates(self) -> None:
        path = self.data_dir / "freight_rates.csv"
        with open(path, mode="r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                route_id = row["route_id"].strip()
                vessel_class_id = row["vessel_class_id"].strip()
                freight_unit = FreightUnit.from_str(row["freight_unit"].strip())
                obs_date = datetime.date.fromisoformat(row["observation_date"].strip())
                rec = FreightRateRecord(
                    freight_rate_id=row["freight_rate_id"].strip(),
                    observation_date=obs_date,
                    route_id=route_id,
                    vessel_class_id=vessel_class_id,
                    freight_value=Decimal(row["freight_value"]),
                    freight_unit=freight_unit,
                    currency=row["currency"].strip(),
                    data_type=row["data_type"].strip(),
                    source=row["source"].strip(),
                )
                key = (route_id, vessel_class_id, freight_unit.value)
                if key not in self._freight_rates:
                    self._freight_rates[key] = []
                self._freight_rates[key].append(rec)
        for key in self._freight_rates:
            self._freight_rates[key].sort(key=lambda r: r.observation_date)

    # --------------------------------------------------------------------------
    # PROTOCOL METHOD IMPLEMENTATIONS
    # --------------------------------------------------------------------------

    def get_route(
        self, origin_port_id: str, destination_port_id: str, commodity: str
    ) -> RouteRecord:
        key = (origin_port_id.strip(), destination_port_id.strip(), commodity.strip())
        if key not in self._routes:
            raise RouteNotFoundError(
                f"No canonical route found connecting {origin_port_id} -> {destination_port_id} for commodity '{commodity}'."
            )
        return self._routes[key]

    def get_vessel_class(self, vessel_class_id: str) -> VesselClassRecord:
        vid = vessel_class_id.strip().upper()
        if vid not in self._vessel_classes:
            raise VesselClassNotFoundError(
                f"Vessel class '{vessel_class_id}' does not exist in canonical vessel catalog."
            )
        return self._vessel_classes[vid]

    def get_compatible_berth_handling_rate(
        self,
        port_id: str,
        commodity: str,
        vessel_class: VesselClassRecord,
    ) -> Decimal:
        """
        Retrieves the handling rate from a physically compatible berth dedicated to the commodity.
        If multiple compatible berths exist, returns the maximum available handling rate.
        """
        key = (port_id.strip(), commodity.strip())
        berths = self._berths_by_port_comm.get(key, [])
        if not berths:
            raise InsufficientFeasibilityDataError(
                f"Port '{port_id}' has no configured berths for commodity '{commodity}'."
            )

        # Check physical compatibility (LOA, Beam, Draft)
        compatible_berths = [
            b for b in berths
            if b.max_loa_m >= vessel_class.loa_m
            and b.max_beam_m >= vessel_class.beam_m
            and b.max_draft_m >= vessel_class.draft_m
        ]

        if not compatible_berths:
            raise InsufficientFeasibilityDataError(
                f"Port '{port_id}' has no compatible berth for vessel class '{vessel_class.vessel_class_id}' "
                f"handling commodity '{commodity}'."
            )

        # Return the representative (highest) handling rate among compatible berths
        return max(b.handling_rate_tpd for b in compatible_berths)

    def get_latest_vlsfo_price(
        self, cost_reference_date: datetime.date
    ) -> Decimal:
        """
        Finds the latest VLSFO price on or before cost_reference_date:
          observation_date <= cost_reference_date
        """
        valid = [r for r in self._vlsfo_prices if r.observation_date <= cost_reference_date]
        if not valid:
            raise InsufficientFuelPriceDataError(
                f"No valid VLSFO price record found on or before {cost_reference_date}."
            )
        return valid[-1].price_value

    def get_latest_port_waiting_hours(
        self, port_id: str, cost_reference_date: datetime.date
    ) -> Decimal:
        """
        Finds the latest observed port waiting hours on or before cost_reference_date.
        """
        records = self._port_activities.get(port_id.strip(), [])
        valid = [r for r in records if r.observation_date <= cost_reference_date]
        if not valid:
            raise InsufficientPortActivityDataError(
                f"No valid port activity record found for port '{port_id}' on or before {cost_reference_date}."
            )
        return valid[-1].average_waiting_hours

    def get_latest_freight_rate(
        self,
        route_id: str,
        vessel_class_id: str,
        freight_unit: FreightUnit,
        cost_reference_date: datetime.date,
    ) -> Decimal:
        """
        Finds the latest observed freight rate on or before cost_reference_date.
        """
        key = (route_id.strip(), vessel_class_id.strip().upper(), freight_unit.value)
        records = self._freight_rates.get(key, [])
        valid = [r for r in records if r.observation_date <= cost_reference_date]
        if not valid:
            raise InsufficientFreightDataError(
                f"No historical freight rate found for route '{route_id}', vessel '{vessel_class_id}', "
                f"unit '{freight_unit.value}' on or before {cost_reference_date}."
            )
        return valid[-1].freight_value
