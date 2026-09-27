"""
DockTech V1 — Vessel Repository
Loads and queries canonical vessel class data from data/reference/vessel_classes.csv.
Sources: DATA_DICTIONARY.md, ARCHITECTURE.md
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from backend.app.domain.entities import VesselClass
from backend.app.repositories.base import _find_data_reference_dir, load_csv_as_dicts


class VesselRepository:
    """
    Repository for canonical VesselClass reference data.
    Reads from data/reference/vessel_classes.csv — the single source of truth.
    """

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self._data_dir = data_dir or _find_data_reference_dir()
        self._vessels: Optional[Dict[str, VesselClass]] = None

    def _load(self) -> Dict[str, VesselClass]:
        if self._vessels is not None:
            return self._vessels
        rows = load_csv_as_dicts(self._data_dir / "vessel_classes.csv")
        self._vessels = {}
        for row in rows:
            vc_id = row["vessel_class_id"].strip()
            self._vessels[vc_id] = VesselClass(
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
        return self._vessels

    def get_by_id(self, vessel_class_id: str) -> Optional[VesselClass]:
        """Returns a VesselClass by vessel_class_id, or None if not found."""
        return self._load().get(vessel_class_id)

    def get_all(self) -> List[VesselClass]:
        """Returns all canonical vessel classes."""
        return list(self._load().values())

    def exists(self, vessel_class_id: str) -> bool:
        """Returns True if the vessel_class_id is in the canonical dataset."""
        return vessel_class_id in self._load()
