"""
DockTech V1 — CSV Reference Data Repository (Base)
Provides thread-safe, cached loading of canonical reference CSV datasets.
Uses only the existing data/reference/*.csv files as the single source of truth.
Sources: DATA_DICTIONARY.md, ARCHITECTURE.md
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Dict, Optional


def _find_data_reference_dir() -> Path:
    """
    Locates the data/reference directory relative to the project root.
    Supports both running from project root and from nested locations.
    """
    # Walk up from this file's location to find the project root
    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        candidate = parent / "data" / "reference"
        if candidate.is_dir() and (candidate / "ports.csv").exists():
            return candidate

    # Try using environment variable override
    env_path = os.environ.get("DOCKTECH_DATA_DIR")
    if env_path:
        p = Path(env_path)
        if p.is_dir():
            return p

    raise FileNotFoundError(
        "Cannot locate data/reference directory. "
        "Set DOCKTECH_DATA_DIR env variable or run from project root."
    )


def load_csv_as_dicts(csv_path: Path) -> list:
    """
    Reads a CSV file and returns a list of row dictionaries.
    All values are strings; numeric conversion is the caller's responsibility.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows
