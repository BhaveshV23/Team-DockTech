"""
DockTech V1 — Route Repository
Loads and queries canonical route data from data/reference/routes.csv.
Sources: DATA_DICTIONARY.md, ARCHITECTURE.md
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from backend.app.domain.entities import Route
from backend.app.repositories.base import _find_data_reference_dir, load_csv_as_dicts


class RouteRepository:
    """
    Repository for canonical Route reference data.
    Reads from data/reference/routes.csv — the single source of truth.
    """

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self._data_dir = data_dir or _find_data_reference_dir()
        self._routes: Optional[Dict[str, Route]] = None
        self._route_by_key: Optional[Dict[Tuple[str, str, str], Route]] = None

    def _load(self) -> Dict[str, Route]:
        if self._routes is not None:
            return self._routes
        rows = load_csv_as_dicts(self._data_dir / "routes.csv")
        self._routes = {}
        self._route_by_key = {}
        for row in rows:
            route_id = row["route_id"].strip()
            origin = row["origin_port_id"].strip()
            destination = row["destination_port_id"].strip()
            commodity = row["commodity"].strip()
            route = Route(
                route_id=route_id,
                origin_port_id=origin,
                destination_port_id=destination,
                commodity=commodity,
                distance_nm=float(row["distance_nm"]),
                typical_sailing_days=float(row["typical_sailing_days"]),
                source=row["source"].strip(),
                data_type=row["data_type"].strip(),
            )
            self._routes[route_id] = route
            self._route_by_key[(origin, destination, commodity)] = route
        return self._routes

    def _ensure_key_index(self) -> Dict[Tuple[str, str, str], Route]:
        self._load()
        assert self._route_by_key is not None
        return self._route_by_key

    def get_by_id(self, route_id: str) -> Optional[Route]:
        """Returns a Route by route_id, or None if not found."""
        return self._load().get(route_id)

    def get_by_origin_dest_commodity(
        self,
        origin_port_id: str,
        destination_port_id: str,
        commodity: str,
    ) -> Optional[Route]:
        """
        Returns the canonical route matching (origin, destination, commodity), or None.
        This implements the formal route resolution step from the V1 Feasibility Evaluation Sequence.
        """
        return self._ensure_key_index().get((origin_port_id, destination_port_id, commodity))

    def get_all(self) -> List[Route]:
        """Returns all canonical routes."""
        return list(self._load().values())
