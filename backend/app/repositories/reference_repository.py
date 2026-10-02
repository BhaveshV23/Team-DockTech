"""
DockTech V1 — Reference Data Repository

Provides data access abstractions for canonical maritime reference data.
Application runtime reads use Supabase. The CSV repository remains available
for explicit offline fixtures and reproducible seed-data validation.
"""

from __future__ import annotations

import csv
import datetime
import httpx
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from backend.app.domain.cost.errors import (
    InsufficientFeasibilityDataError,
    InsufficientFreightDataError,
    InsufficientFuelPriceDataError,
    InsufficientPortActivityDataError,
    RouteNotFoundError,
    VesselClassNotFoundError,
)
from backend.app.domain.cost.models import FreightUnit
from backend.app.core.config import settings
from backend.app.repositories.base import (
    _find_data_reference_dir,
    load_csv_as_dicts,
)
from backend.app.domain.entities import Port, Berth, VesselClass, Route


# ============================================================================
# 1. REFERENCE RECORD DATA STRUCTURES
# ============================================================================


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


# ============================================================================
# 2. REPOSITORY PROTOCOL
# ============================================================================


class ReferenceRepositoryProtocol(Protocol):
    """Abstract interface for querying DockTech canonical reference datasets."""

    def get_route(
        self,
        origin_port_id: str,
        destination_port_id: str,
        commodity: str,
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

    def get_compatible_berth(
        self, port_id: str, commodity: str, vessel_class: VesselClassRecord
    ) -> BerthRecord:
        ...

    def get_latest_vlsfo_price(
        self,
        cost_reference_date: datetime.date,
    ) -> Decimal:
        ...

    def get_latest_port_waiting_hours(
        self,
        port_id: str,
        cost_reference_date: datetime.date,
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

    def get_freight_observations(
        self, route_id: str, vessel_class_id: str, freight_unit: FreightUnit
    ) -> List[FreightRateRecord]:
        ...


# ============================================================================
# 3. CSV REFERENCE DATA REPOSITORY
# ============================================================================


class CSVReferenceRepository:
    """
    In-memory indexed reference repository loaded from canonical CSV datasets.

    Provides deterministic, reproducible access for tests and offline tooling.
    """

    def __init__(self, data_dir: Path | str) -> None:
        self.data_dir = Path(data_dir)

        self._ports: Dict[str, PortRecord] = {}
        self._routes: Dict[tuple[str, str, str], RouteRecord] = {}
        self._vessel_classes: Dict[str, VesselClassRecord] = {}
        self._berths_by_port_comm: Dict[
            tuple[str, str], List[BerthRecord]
        ] = {}
        self._vlsfo_prices: List[FuelPriceRecord] = []
        self._port_activities: Dict[str, List[PortActivityRecord]] = {}
        self._freight_rates: Dict[
            tuple[str, str, str], List[FreightRateRecord]
        ] = {}

        self._load_all()


    def _load_all(self) -> None:
        self._load_ports()
        self._load_routes()
        self._load_vessel_classes()
        self._load_berths()
        self._load_fuel_prices()
        self._load_port_activity()
        self._load_freight_rates()

    def _load_ports(self) -> None:
        path = self.data_dir / "ports.csv"

        for row in load_csv_as_dicts(path):
            record = PortRecord(
                port_id=row["port_id"].strip(),
                port_name=row["port_name"].strip(),
                country=row["country"].strip(),
                max_loa_m=Decimal(row["max_loa_m"]),
                max_beam_m=Decimal(row["max_beam_m"]),
                max_draft_m=Decimal(row["max_draft_m"]),
                handling_rate_tpd=Decimal(row["handling_rate_tpd"]),
                typical_turnaround_hours=Decimal(
                    row["typical_turnaround_hours"]
                ),
                source=row["source"].strip(),
                data_type=row["data_type"].strip(),
            )
            self._ports[record.port_id] = record

    def _load_routes(self) -> None:
        path = self.data_dir / "routes.csv"

        for row in load_csv_as_dicts(path):
            record = RouteRecord(
                route_id=row["route_id"].strip(),
                origin_port_id=row["origin_port_id"].strip(),
                destination_port_id=row["destination_port_id"].strip(),
                commodity=row["commodity"].strip(),
                distance_nm=Decimal(row["distance_nm"]),
                typical_sailing_days=Decimal(row["typical_sailing_days"]),
                source=row["source"].strip(),
                data_type=row["data_type"].strip(),
            )

            self._routes[
                (
                    record.origin_port_id,
                    record.destination_port_id,
                    record.commodity,
                )
            ] = record

    def _load_vessel_classes(self) -> None:
        path = self.data_dir / "vessel_classes.csv"

        for row in load_csv_as_dicts(path):
            record = VesselClassRecord(
                vessel_class_id=row["vessel_class_id"].strip(),
                vessel_class_name=row["vessel_class_name"].strip(),
                dwt_min_mt=Decimal(row["dwt_min_mt"]),
                dwt_max_mt=Decimal(row["dwt_max_mt"]),
                loa_m=Decimal(row["loa_m"]),
                beam_m=Decimal(row["beam_m"]),
                draft_m=Decimal(row["draft_m"]),
                speed_knots=Decimal(row["speed_knots"]),
                cargo_capacity_mt=Decimal(row["cargo_capacity_mt"]),
                fuel_consumption_mt_day=Decimal(
                    row["fuel_consumption_mt_day"]
                ),
                source=row["source"].strip(),
                data_type=row["data_type"].strip(),
            )

            self._vessel_classes[record.vessel_class_id] = record

    def _load_berths(self) -> None:
        path = self.data_dir / "berths.csv"

        for row in load_csv_as_dicts(path):
            record = BerthRecord(
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

            key = (record.port_id, record.commodity)

            if key not in self._berths_by_port_comm:
                self._berths_by_port_comm[key] = []

            self._berths_by_port_comm[key].append(record)

    def _load_fuel_prices(self) -> None:
        path = self.data_dir / "fuel_prices.csv"

        for row in load_csv_as_dicts(path):
            fuel_type = row["fuel_type"].strip()

            if fuel_type == "VLSFO":
                record = FuelPriceRecord(
                    fuel_price_id=row["fuel_price_id"].strip(),
                    observation_date=datetime.date.fromisoformat(
                        row["observation_date"].strip()
                    ),
                    fuel_type=fuel_type,
                    price_value=Decimal(row["price_value"]),
                    currency=row["currency"].strip(),
                    unit=row["unit"].strip(),
                    data_type=row["data_type"].strip(),
                    source=row["source"].strip(),
                )

                self._vlsfo_prices.append(record)

        self._vlsfo_prices.sort(key=lambda r: r.observation_date)

    def _load_port_activity(self) -> None:
        path = self.data_dir / "port_activity.csv"

        for row in load_csv_as_dicts(path):
            port_id = row["port_id"].strip()

            record = PortActivityRecord(
                activity_id=row["activity_id"].strip(),
                observation_date=datetime.date.fromisoformat(
                    row["observation_date"].strip()
                ),
                port_id=port_id,
                vessel_arrivals=int(row["vessel_arrivals"]),
                average_waiting_hours=Decimal(
                    row["average_waiting_hours"]
                ),
                average_turnaround_hours=Decimal(
                    row["average_turnaround_hours"]
                ),
                congestion_level=row["congestion_level"].strip(),
                source=row["source"].strip(),
                data_type=row["data_type"].strip(),
            )

            if port_id not in self._port_activities:
                self._port_activities[port_id] = []

            self._port_activities[port_id].append(record)

        for records in self._port_activities.values():
            records.sort(key=lambda r: r.observation_date)

    def _load_freight_rates(self) -> None:
        path = self.data_dir / "freight_rates.csv"

        for row in load_csv_as_dicts(path):
            route_id = row["route_id"].strip()
            vessel_class_id = row["vessel_class_id"].strip()
            freight_unit = FreightUnit.from_str(
                row["freight_unit"].strip()
            )

            record = FreightRateRecord(
                freight_rate_id=row["freight_rate_id"].strip(),
                observation_date=datetime.date.fromisoformat(
                    row["observation_date"].strip()
                ),
                route_id=route_id,
                vessel_class_id=vessel_class_id,
                freight_value=Decimal(row["freight_value"]),
                freight_unit=freight_unit,
                currency=row["currency"].strip(),
                data_type=row["data_type"].strip(),
                source=row["source"].strip(),
            )

            key = (
                route_id,
                vessel_class_id,
                freight_unit.value,
            )

            if key not in self._freight_rates:
                self._freight_rates[key] = []

            self._freight_rates[key].append(record)

        for records in self._freight_rates.values():
            records.sort(key=lambda r: r.observation_date)

    # ========================================================================
    # Compatibility methods for the existing reference API
    # ========================================================================

    def get_ports(self) -> List[Dict[str, Any]]:
        """Return canonical ports in the format expected by the reference API."""
        return [
            {
                "port_id": record.port_id,
                "port_name": record.port_name,
                "country": record.country,
                "max_loa_m": float(record.max_loa_m),
                "max_beam_m": float(record.max_beam_m),
                "max_draft_m": float(record.max_draft_m),
                "handling_rate_tpd": float(record.handling_rate_tpd),
                "typical_turnaround_hours": float(
                    record.typical_turnaround_hours
                ),
                "source": record.source,
                "data_type": record.data_type,
            }
            for record in self._ports.values()
        ]

    def get_vessels(self) -> List[Dict[str, Any]]:
        """Return canonical vessel classes for the existing reference API."""
        return [
            {
                "vessel_class_id": record.vessel_class_id,
                "vessel_class_name": record.vessel_class_name,
                "dwt_min_mt": float(record.dwt_min_mt),
                "dwt_max_mt": float(record.dwt_max_mt),
                "loa_m": float(record.loa_m),
                "beam_m": float(record.beam_m),
                "draft_m": float(record.draft_m),
                "speed_knots": float(record.speed_knots),
                "cargo_capacity_mt": float(record.cargo_capacity_mt),
                "fuel_consumption_mt_day": float(
                    record.fuel_consumption_mt_day
                ),
                "source": record.source,
                "data_type": record.data_type,
            }
            for record in self._vessel_classes.values()
        ]

    def get_routes(self) -> List[Dict[str, Any]]:
        """Return canonical routes for the existing reference API."""
        return [
            {
                "route_id": record.route_id,
                "origin_port_id": record.origin_port_id,
                "destination_port_id": record.destination_port_id,
                "commodity": record.commodity,
                "distance_nm": float(record.distance_nm),
                "typical_sailing_days": float(
                    record.typical_sailing_days
                ),
                "source": record.source,
                "data_type": record.data_type,
            }
            for record in self._routes.values()
        ]

    # ========================================================================
    # Protocol method implementations
    # ========================================================================

    def get_route(
        self,
        origin_port_id: str,
        destination_port_id: str,
        commodity: str,
    ) -> RouteRecord:
        key = (
            origin_port_id.strip(),
            destination_port_id.strip(),
            commodity.strip(),
        )

        if key not in self._routes:
            raise RouteNotFoundError(
                f"No canonical route found connecting "
                f"{origin_port_id} -> {destination_port_id} "
                f"for commodity '{commodity}'."
            )

        return self._routes[key]

    def get_vessel_class(
        self,
        vessel_class_id: str,
    ) -> VesselClassRecord:
        vid = vessel_class_id.strip().upper()

        if vid not in self._vessel_classes:
            raise VesselClassNotFoundError(
                f"Vessel class '{vessel_class_id}' does not exist "
                f"in canonical vessel catalog."
            )

        return self._vessel_classes[vid]

    def get_compatible_berth_handling_rate(
        self,
        port_id: str,
        commodity: str,
        vessel_class: VesselClassRecord,
    ) -> Decimal:
        """
        Retrieve the handling rate from a physically compatible berth
        dedicated to the commodity.
        """

        key = (port_id.strip(), commodity.strip())
        berths = self._berths_by_port_comm.get(key, [])

        if not berths:
            raise InsufficientFeasibilityDataError(
                f"Port '{port_id}' has no configured berths "
                f"for commodity '{commodity}'."
            )

        compatible_berths = [
            berth
            for berth in berths
            if berth.max_loa_m >= vessel_class.loa_m
            and berth.max_beam_m >= vessel_class.beam_m
            and berth.max_draft_m >= vessel_class.draft_m
        ]

        if not compatible_berths:
            raise InsufficientFeasibilityDataError(
                f"Port '{port_id}' has no compatible berth for "
                f"vessel class '{vessel_class.vessel_class_id}' "
                f"handling commodity '{commodity}'."
            )

        return max(
            berth.handling_rate_tpd
            for berth in compatible_berths
        )

    def get_compatible_berth(
        self, port_id: str, commodity: str, vessel_class: VesselClassRecord
    ) -> BerthRecord:
        key = (port_id.strip(), commodity.strip())
        berths = self._berths_by_port_comm.get(key, [])
        compatible = [
            berth for berth in berths
            if berth.max_loa_m >= vessel_class.loa_m
            and berth.max_beam_m >= vessel_class.beam_m
            and berth.max_draft_m >= vessel_class.draft_m
        ]
        if not compatible:
            raise InsufficientFeasibilityDataError(
                f"Port '{port_id}' has no compatible berth for vessel class '{vessel_class.vessel_class_id}' "
                f"handling commodity '{commodity}'."
            )
        return max(compatible, key=lambda berth: berth.handling_rate_tpd)

    def get_latest_vlsfo_price(
        self,
        cost_reference_date: datetime.date,
    ) -> Decimal:
        valid = [
            record
            for record in self._vlsfo_prices
            if record.observation_date <= cost_reference_date
        ]

        if not valid:
            raise InsufficientFuelPriceDataError(
                f"No valid VLSFO price record found on or before "
                f"{cost_reference_date}."
            )

        return valid[-1].price_value

    def get_latest_port_waiting_hours(
        self,
        port_id: str,
        cost_reference_date: datetime.date,
    ) -> Decimal:
        records = self._port_activities.get(port_id.strip(), [])

        valid = [
            record
            for record in records
            if record.observation_date <= cost_reference_date
        ]

        if not valid:
            raise InsufficientPortActivityDataError(
                f"No valid port activity record found for port "
                f"'{port_id}' on or before {cost_reference_date}."
            )

        return valid[-1].average_waiting_hours

    def get_latest_freight_rate(
        self,
        route_id: str,
        vessel_class_id: str,
        freight_unit: FreightUnit,
        cost_reference_date: datetime.date,
    ) -> Decimal:
        key = (
            route_id.strip(),
            vessel_class_id.strip().upper(),
            freight_unit.value,
        )

        records = self._freight_rates.get(key, [])

        valid = [
            record
            for record in records
            if record.observation_date <= cost_reference_date
        ]

        if not valid:
            raise InsufficientFreightDataError(
                f"No historical freight rate found for route "
                f"'{route_id}', vessel '{vessel_class_id}', "
                f"unit '{freight_unit.value}' on or before "
                f"{cost_reference_date}."
            )

        return valid[-1].freight_value

    def get_freight_observations(
        self, route_id: str, vessel_class_id: str, freight_unit: FreightUnit
    ) -> List[FreightRateRecord]:
        """Return the stored observations for one canonical freight series."""
        key = (route_id.strip(), vessel_class_id.strip().upper(), freight_unit.value)
        return list(self._freight_rates.get(key, []))


class ReferenceDataUnavailableError(Exception):
    """Raised when the authoritative Supabase reference store cannot be queried."""


class ReferenceObservationNotFoundError(Exception):
    """Raised when no dated reference observation exists before the requested date."""


class SupabaseCostReferenceRepository:
    """Application reference-data access backed by canonical Supabase tables."""

    def __init__(self, supabase_url: str | None = None, service_role_key: str | None = None):
        self.supabase_url = settings.SUPABASE_URL if supabase_url is None else supabase_url
        self.service_role_key = (
            settings.SUPABASE_SERVICE_ROLE_KEY
            if service_role_key is None
            else service_role_key
        )

    def _get(self, table: str, params: Dict[str, str]) -> List[Dict[str, Any]]:
        if not self.supabase_url or not self.service_role_key:
            raise ReferenceDataUnavailableError("Reference data storage is not configured")
        url = f"{self.supabase_url.rstrip('/')}/rest/v1/{table}"
        headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Accept": "application/json",
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=headers, params={"select": "*", **params})
            if response.status_code < 200 or response.status_code >= 300:
                raise ReferenceDataUnavailableError(
                    f"Reference data query failed with status {response.status_code}"
                )
            rows = response.json()
            if not isinstance(rows, list):
                raise ReferenceDataUnavailableError("Reference data query returned an invalid response")
            return rows
        except ReferenceDataUnavailableError:
            raise
        except Exception as exc:
            raise ReferenceDataUnavailableError("Reference data service is unavailable") from exc

    def _one(self, table: str, params: Dict[str, str], missing_error: Exception) -> Dict[str, Any]:
        rows = self._get(table, {**params, "limit": "1"})
        if not rows:
            raise missing_error
        return rows[0]

    def get_rows(self, table: str, filters: Dict[str, str] | None = None) -> List[Dict[str, Any]]:
        """Return reference rows for application repositories and API services."""
        params = dict(filters or {})
        return self._get(table, params)

    def get_ports(self) -> List[Dict[str, Any]]:
        return self.get_rows("ports", {"order": "port_id.asc"})

    def get_vessels(self) -> List[Dict[str, Any]]:
        return self.get_rows("vessel_classes", {"order": "vessel_class_id.asc"})

    def get_routes(self) -> List[Dict[str, Any]]:
        return self.get_rows("routes", {"order": "route_id.asc"})

    def get_freight_observations(
        self, route_id: str, vessel_class_id: str, freight_unit: FreightUnit
    ) -> List[FreightRateRecord]:
        rows = self._get("freight_rates", {
            "route_id": f"eq.{route_id.strip()}",
            "vessel_class_id": f"eq.{vessel_class_id.strip().upper()}",
            "freight_unit": f"eq.{freight_unit.value}",
            "order": "observation_date.asc",
        })
        return [FreightRateRecord(
            freight_rate_id=row["freight_rate_id"],
            observation_date=datetime.date.fromisoformat(row["observation_date"]),
            route_id=row["route_id"], vessel_class_id=row["vessel_class_id"],
            freight_value=Decimal(str(row["freight_value"])),
            freight_unit=FreightUnit.from_str(row["freight_unit"]),
            currency=row["currency"], data_type=row["data_type"], source=row["source"],
        ) for row in rows]

    def get_port_entity(self, port_id: str) -> Optional[Port]:
        rows = self._get("ports", {"port_id": f"eq.{port_id.strip()}", "limit": "1"})
        return self._port_entity(rows[0]) if rows else None

    def get_port_entities(self) -> List[Port]:
        return [self._port_entity(row) for row in self.get_ports()]

    @staticmethod
    def _port_entity(row: Dict[str, Any]) -> Port:
        return Port(
            port_id=row["port_id"], port_name=row["port_name"], country=row["country"],
            max_loa_m=float(row["max_loa_m"]), max_beam_m=float(row["max_beam_m"]),
            max_draft_m=float(row["max_draft_m"]), handling_rate_tpd=float(row["handling_rate_tpd"]),
            typical_turnaround_hours=float(row["typical_turnaround_hours"]),
            source=row["source"], data_type=row["data_type"],
        )

    def get_berth_entities(self, port_id: str) -> List[Berth]:
        rows = self._get("berths", {"port_id": f"eq.{port_id.strip()}", "order": "berth_id.asc"})
        return [Berth(
            berth_id=row["berth_id"], port_id=row["port_id"], berth_name=row["berth_name"],
            commodity=row["commodity"], max_loa_m=float(row["max_loa_m"]),
            max_beam_m=float(row["max_beam_m"]), max_draft_m=float(row["max_draft_m"]),
            handling_rate_tpd=float(row["handling_rate_tpd"]), source=row["source"],
            data_type=row["data_type"],
        ) for row in rows]

    def get_berth_entities_for_all_ports(self) -> List[Berth]:
        rows = self._get("berths", {"order": "berth_id.asc"})
        return [Berth(
            berth_id=row["berth_id"], port_id=row["port_id"], berth_name=row["berth_name"],
            commodity=row["commodity"], max_loa_m=float(row["max_loa_m"]),
            max_beam_m=float(row["max_beam_m"]), max_draft_m=float(row["max_draft_m"]),
            handling_rate_tpd=float(row["handling_rate_tpd"]), source=row["source"],
            data_type=row["data_type"],
        ) for row in rows]

    def get_vessel_entity(self, vessel_class_id: str) -> Optional[VesselClass]:
        try:
            record = self.get_vessel_class(vessel_class_id)
        except VesselClassNotFoundError:
            return None
        return VesselClass(
            vessel_class_id=record.vessel_class_id, vessel_class_name=record.vessel_class_name,
            dwt_min_mt=float(record.dwt_min_mt), dwt_max_mt=float(record.dwt_max_mt),
            loa_m=float(record.loa_m), beam_m=float(record.beam_m), draft_m=float(record.draft_m),
            speed_knots=float(record.speed_knots), cargo_capacity_mt=float(record.cargo_capacity_mt),
            fuel_consumption_mt_day=float(record.fuel_consumption_mt_day),
            source=record.source, data_type=record.data_type,
        )

    def get_vessel_entities(self) -> List[VesselClass]:
        return [self._vessel_entity(row) for row in self.get_vessels()]

    @staticmethod
    def _vessel_entity(row: Dict[str, Any]) -> VesselClass:
        return VesselClass(
            vessel_class_id=row["vessel_class_id"], vessel_class_name=row["vessel_class_name"],
            dwt_min_mt=float(row["dwt_min_mt"]), dwt_max_mt=float(row["dwt_max_mt"]),
            loa_m=float(row["loa_m"]), beam_m=float(row["beam_m"]), draft_m=float(row["draft_m"]),
            speed_knots=float(row["speed_knots"]), cargo_capacity_mt=float(row["cargo_capacity_mt"]),
            fuel_consumption_mt_day=float(row["fuel_consumption_mt_day"]),
            source=row["source"], data_type=row["data_type"],
        )

    def get_route_entity(
        self, origin_port_id: str, destination_port_id: str, commodity: str
    ) -> Optional[Route]:
        rows = self._get("routes", {
            "origin_port_id": f"eq.{origin_port_id.strip()}",
            "destination_port_id": f"eq.{destination_port_id.strip()}",
            "commodity": f"eq.{commodity.strip()}", "limit": "1",
        })
        return self._route_entity(rows[0]) if rows else None

    @staticmethod
    def _route_entity(row: Dict[str, Any]) -> Route:
        return Route(
            route_id=row["route_id"], origin_port_id=row["origin_port_id"],
            destination_port_id=row["destination_port_id"], commodity=row["commodity"],
            distance_nm=float(row["distance_nm"]), typical_sailing_days=float(row["typical_sailing_days"]),
            source=row["source"], data_type=row["data_type"],
        )

    def get_route_entities(self) -> List[Route]:
        return [self._route_entity(row) for row in self.get_routes()]

    def get_route(self, origin_port_id: str, destination_port_id: str, commodity: str) -> RouteRecord:
        row = self._one(
            "routes",
            {
                "origin_port_id": f"eq.{origin_port_id.strip()}",
                "destination_port_id": f"eq.{destination_port_id.strip()}",
                "commodity": f"eq.{commodity.strip()}",
            },
            RouteNotFoundError(
                f"No canonical route found connecting {origin_port_id} -> {destination_port_id} for commodity '{commodity}'."
            ),
        )
        return RouteRecord(
            route_id=row["route_id"], origin_port_id=row["origin_port_id"],
            destination_port_id=row["destination_port_id"], commodity=row["commodity"],
            distance_nm=Decimal(str(row["distance_nm"])),
            typical_sailing_days=Decimal(str(row["typical_sailing_days"])),
            source=row["source"], data_type=row["data_type"],
        )

    def get_vessel_class(self, vessel_class_id: str) -> VesselClassRecord:
        row = self._one(
            "vessel_classes", {"vessel_class_id": f"eq.{vessel_class_id.strip().upper()}"},
            VesselClassNotFoundError(f"Vessel class '{vessel_class_id}' does not exist in canonical vessel catalog."),
        )
        return VesselClassRecord(
            vessel_class_id=row["vessel_class_id"], vessel_class_name=row["vessel_class_name"],
            dwt_min_mt=Decimal(str(row["dwt_min_mt"])), dwt_max_mt=Decimal(str(row["dwt_max_mt"])),
            loa_m=Decimal(str(row["loa_m"])), beam_m=Decimal(str(row["beam_m"])),
            draft_m=Decimal(str(row["draft_m"])), speed_knots=Decimal(str(row["speed_knots"])),
            cargo_capacity_mt=Decimal(str(row["cargo_capacity_mt"])),
            fuel_consumption_mt_day=Decimal(str(row["fuel_consumption_mt_day"])),
            source=row["source"], data_type=row["data_type"],
        )

    def get_compatible_berth_handling_rate(self, port_id: str, commodity: str, vessel_class: VesselClassRecord) -> Decimal:
        rows = self._get("berths", {
            "port_id": f"eq.{port_id.strip()}", "commodity": f"eq.{commodity.strip()}"
        })
        compatible = [
            row for row in rows
            if Decimal(str(row["max_loa_m"])) >= vessel_class.loa_m
            and Decimal(str(row["max_beam_m"])) >= vessel_class.beam_m
            and Decimal(str(row["max_draft_m"])) >= vessel_class.draft_m
        ]
        if not compatible:
            raise InsufficientFeasibilityDataError(
                f"Port '{port_id}' has no compatible berth for vessel class '{vessel_class.vessel_class_id}' handling commodity '{commodity}'."
            )
        return max(Decimal(str(row["handling_rate_tpd"])) for row in compatible)

    def get_compatible_berth(self, port_id: str, commodity: str, vessel_class: VesselClassRecord) -> BerthRecord:
        rows = self._get("berths", {
            "port_id": f"eq.{port_id.strip()}", "commodity": f"eq.{commodity.strip()}"
        })
        compatible = [
            row for row in rows
            if Decimal(str(row["max_loa_m"])) >= vessel_class.loa_m
            and Decimal(str(row["max_beam_m"])) >= vessel_class.beam_m
            and Decimal(str(row["max_draft_m"])) >= vessel_class.draft_m
        ]
        if not compatible:
            raise InsufficientFeasibilityDataError(
                f"Port '{port_id}' has no compatible berth for vessel class '{vessel_class.vessel_class_id}' handling commodity '{commodity}'."
            )
        row = max(compatible, key=lambda item: Decimal(str(item["handling_rate_tpd"])))
        return BerthRecord(
            berth_id=row["berth_id"], port_id=row["port_id"], berth_name=row["berth_name"],
            commodity=row["commodity"], max_loa_m=Decimal(str(row["max_loa_m"])),
            max_beam_m=Decimal(str(row["max_beam_m"])), max_draft_m=Decimal(str(row["max_draft_m"])),
            handling_rate_tpd=Decimal(str(row["handling_rate_tpd"])),
            source=row["source"], data_type=row["data_type"],
        )

    def _latest(self, table: str, filters: Dict[str, str], date: datetime.date) -> Dict[str, Any]:
        return self._one(
            table,
            {**filters, "observation_date": f"lte.{date.isoformat()}", "order": "observation_date.desc"},
            ReferenceObservationNotFoundError(
                "No reference observation exists on or before the cost reference date"
            ),
        )

    def get_latest_vlsfo_price(self, cost_reference_date: datetime.date) -> Decimal:
        try:
            row = self._latest("fuel_prices", {"fuel_type": "eq.VLSFO"}, cost_reference_date)
        except ReferenceObservationNotFoundError as exc:
            raise InsufficientFuelPriceDataError(str(exc)) from exc
        return Decimal(str(row["price_value"]))

    def get_latest_port_waiting_hours(self, port_id: str, cost_reference_date: datetime.date) -> Decimal:
        try:
            row = self._latest("port_activity", {"port_id": f"eq.{port_id.strip()}"}, cost_reference_date)
        except ReferenceObservationNotFoundError as exc:
            raise InsufficientPortActivityDataError(str(exc)) from exc
        return Decimal(str(row["average_waiting_hours"]))

    def get_latest_freight_rate(self, route_id: str, vessel_class_id: str, freight_unit: FreightUnit, cost_reference_date: datetime.date) -> Decimal:
        try:
            row = self._latest("freight_rates", {
                "route_id": f"eq.{route_id.strip()}",
                "vessel_class_id": f"eq.{vessel_class_id.strip().upper()}",
                "freight_unit": f"eq.{freight_unit.value}",
            }, cost_reference_date)
        except ReferenceObservationNotFoundError as exc:
            raise InsufficientFreightDataError(str(exc)) from exc
        return Decimal(str(row["freight_value"]))


# ============================================================================
# Existing reference-service compatibility instance
# ============================================================================

reference_repository = SupabaseCostReferenceRepository()
