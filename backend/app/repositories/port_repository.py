"""
DockTech V1 — Port Repository
Loads and queries canonical port data from data/reference/ports.csv.
Sources: DATA_DICTIONARY.md, ARCHITECTURE.md
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from backend.app.domain.entities import Port
from backend.app.repositories.base import _find_data_reference_dir, load_csv_as_dicts


class PortRepository:
    """
    Repository for canonical Port reference data.
    Reads from data/reference/ports.csv — the single source of truth.
    """

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self._data_dir = data_dir or _find_data_reference_dir()
        self._ports: Optional[Dict[str, Port]] = None

    def _load(self) -> Dict[str, Port]:
        if self._ports is not None:
            return self._ports
        rows = load_csv_as_dicts(self._data_dir / "ports.csv")
        self._ports = {}
        for row in rows:
            port_id = row["port_id"].strip()
            self._ports[port_id] = Port(
                port_id=port_id,
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
        return self._ports

    def get_by_id(self, port_id: str) -> Optional[Port]:
        """Returns a Port by port_id, or None if not found."""
        return self._load().get(port_id)

    def get_all(self) -> List[Port]:
        """Returns all canonical ports."""
        return list(self._load().values())

    def exists(self, port_id: str) -> bool:
        """Returns True if the port_id is in the canonical dataset."""
        return port_id in self._load()
