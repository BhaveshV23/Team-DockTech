"""
DockTech V1 — Berth Repository
Loads and queries canonical berth data from data/reference/berths.csv.
Sources: DATA_DICTIONARY.md, ARCHITECTURE.md
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from backend.app.domain.entities import Berth
from backend.app.repositories.base import _find_data_reference_dir, load_csv_as_dicts


class BerthRepository:
    """
    Repository for canonical Berth reference data.
    Reads from data/reference/berths.csv — the single source of truth.
    Berths are the authoritative operational layer for feasibility.
    """

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self._data_dir = data_dir or _find_data_reference_dir()
        self._berths: Optional[Dict[str, Berth]] = None

    def _load(self) -> Dict[str, Berth]:
        if self._berths is not None:
            return self._berths
        rows = load_csv_as_dicts(self._data_dir / "berths.csv")
        self._berths = {}
        for row in rows:
            berth_id = row["berth_id"].strip()
            self._berths[berth_id] = Berth(
                berth_id=berth_id,
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
        return self._berths

    def get_by_id(self, berth_id: str) -> Optional[Berth]:
        """Returns a Berth by berth_id, or None if not found."""
        return self._load().get(berth_id)

    def get_all(self) -> List[Berth]:
        """Returns all canonical berths."""
        return list(self._load().values())

    def get_by_port_and_commodity(self, port_id: str, commodity: str) -> List[Berth]:
        """
        Returns all berths at the given port that handle the specified commodity.
        This is the canonical query for feasibility evaluation.
        NEVER returns generic berths — matches exactly on commodity field.
        """
        return [
            b for b in self._load().values()
            if b.port_id == port_id and b.commodity == commodity
        ]

    def get_by_port(self, port_id: str) -> List[Berth]:
        """Returns all berths at the given port (all commodities)."""
        return [
            b for b in self._load().values()
            if b.port_id == port_id
        ]
