#!/usr/bin/env python3
"""
DockTech V1 — Reference Data Validation Gate
=============================================
Pre-seeding validation gate for DockTech V1 reference CSV datasets.

Authoritative Source-of-Truth Documents:
  1. PRD.md
  2. DATA_DICTIONARY.md (Frozen Canonical Contract)
  3. ARCHITECTURE.md (Pipeline Lifecycle & Boundaries)
  4. SYNTHETIC_DATA_DESIGN.md (Data Generation & Economic Models)

Workflow Role:
  python scripts/generate_synthetic_data.py
  python scripts/validate_reference_data.py  <-- (This script: must exit 0)
  python scripts/seed_database.py           <-- (Only proceeds if validator passes)

Datasets Validated:
  data/reference/
  ├── ports.csv             (15 rows)
  ├── berths.csv            (32 rows)
  ├── vessel_classes.csv    (6 rows)
  ├── routes.csv            (28 routes)
  ├── freight_rates.csv     (245,616 rows)
  ├── commodity_prices.csv  (1,462 rows)
  ├── fuel_prices.csv       (1,462 rows)
  ├── port_activity.csv     (10,965 rows)
  └── scenario_defaults.csv (3 rows)
  Total Reference Records: 259,589 rows.

This validator is strictly read-only, deterministic, and dependency-free
(uses standard-library Python only).
"""

from __future__ import annotations

import argparse
import csv
import datetime
import math
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ==============================================================================
# 1. ERROR REPORTING DATASTRUCTURES
# ==============================================================================

@dataclass
class ValidationError:
    dataset: str
    check: str
    message: str
    row_sample: Optional[str] = None


class ValidationContext:
    """Accumulates validation errors and tracks dataset-level statuses."""

    def __init__(self) -> None:
        self.errors: List[ValidationError] = []
        self.warnings: List[str] = []
        self.dataset_status: Dict[str, bool] = {}
        self.cross_dataset_status: Dict[str, bool] = {}
        self.row_counts: Dict[str, int] = {}

    def add_error(
        self,
        dataset: str,
        check: str,
        message: str,
        row_sample: Optional[str] = None,
    ) -> None:
        self.errors.append(
            ValidationError(
                dataset=dataset,
                check=check,
                message=message,
                row_sample=row_sample,
            )
        )

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


# ==============================================================================
# 2. CANONICAL SCHEMAS & VOCABULARIES (DATA_DICTIONARY.md)
# ==============================================================================

CANONICAL_SCHEMAS: Dict[str, List[str]] = {
    "ports.csv": [
        "port_id",
        "port_name",
        "country",
        "max_loa_m",
        "max_beam_m",
        "max_draft_m",
        "handling_rate_tpd",
        "typical_turnaround_hours",
        "source",
        "data_type",
    ],
    "berths.csv": [
        "berth_id",
        "port_id",
        "berth_name",
        "commodity",
        "max_loa_m",
        "max_beam_m",
        "max_draft_m",
        "handling_rate_tpd",
        "source",
        "data_type",
    ],
    "vessel_classes.csv": [
        "vessel_class_id",
        "vessel_class_name",
        "dwt_min_mt",
        "dwt_max_mt",
        "loa_m",
        "beam_m",
        "draft_m",
        "speed_knots",
        "cargo_capacity_mt",
        "fuel_consumption_mt_day",
        "source",
        "data_type",
    ],
    "routes.csv": [
        "route_id",
        "origin_port_id",
        "destination_port_id",
        "commodity",
        "distance_nm",
        "typical_sailing_days",
        "source",
        "data_type",
    ],
    "freight_rates.csv": [
        "freight_rate_id",
        "observation_date",
        "route_id",
        "vessel_class_id",
        "freight_value",
        "freight_unit",
        "currency",
        "data_type",
        "source",
    ],
    "commodity_prices.csv": [
        "commodity_price_id",
        "observation_date",
        "commodity",
        "market",
        "price_value",
        "currency",
        "unit",
        "data_type",
        "source",
    ],
    "fuel_prices.csv": [
        "fuel_price_id",
        "observation_date",
        "fuel_type",
        "price_value",
        "currency",
        "unit",
        "data_type",
        "source",
    ],
    "port_activity.csv": [
        "activity_id",
        "observation_date",
        "port_id",
        "vessel_arrivals",
        "average_waiting_hours",
        "average_turnaround_hours",
        "congestion_level",
        "source",
        "data_type",
    ],
    "scenario_defaults.csv": [
        "scenario_id",
        "scenario_name",
        "freight_change_pct",
        "fuel_change_pct",
        "delay_hours",
        "port_congestion_level",
        "description",
        "source",
        "data_type",
    ],
}

EXPECTED_ROW_COUNTS: Dict[str, int] = {
    "ports.csv": 15,
    "berths.csv": 32,
    "vessel_classes.csv": 6,
    "routes.csv": 28,
    "freight_rates.csv": 245616,
    "commodity_prices.csv": 1462,
    "fuel_prices.csv": 1462,
    "port_activity.csv": 10965,
    "scenario_defaults.csv": 3,
}

EXPECTED_TOTAL_ROWS = 259589

CANONICAL_VESSEL_CLASSES = {
    "HANDYSIZE",
    "SUPRAMAX",
    "ULTRAMAX",
    "PANAMAX",
    "KAMSARMAX",
    "CAPESIZE",
}

CANONICAL_COMMODITIES = {
    "THERMAL_COAL",
    "COKING_COAL",
}

CANONICAL_SCENARIOS = {
    "BASELINE",
    "ADVERSE",
    "FAVORABLE",
}

CANONICAL_CONGESTION_LEVELS = {
    "LOW",
    "MEDIUM",
    "HIGH",
}

CANONICAL_FREIGHT_UNITS = {
    "USD_PER_MT",
    "USD_PER_DAY",
}

CANONICAL_FUEL_TYPES = {
    "VLSFO",
    "MGO",
}

EXPECTED_SOURCE = "SYNTHETIC_GENERATOR_V1"
EXPECTED_DATA_TYPE = "SYNTHETIC"
EXPECTED_CURRENCY = "USD"
START_DATE = datetime.date(2024, 1, 1)
END_DATE = datetime.date(2025, 12, 31)
EXPECTED_DAYS_COUNT = 731


# ==============================================================================
# 3. HELPER PARSING UTILITIES
# ==============================================================================

def parse_float(val: str, field_name: str, row_desc: str) -> Optional[float]:
    """Parses a string as float, ensuring non-NaN/non-Inf."""
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def parse_int(val: str) -> Optional[int]:
    """Parses a string as integer."""
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def parse_date(val: str) -> Optional[datetime.date]:
    """Parses ISO YYYY-MM-DD date."""
    try:
        return datetime.date.fromisoformat(val)
    except (ValueError, TypeError):
        return None


# ==============================================================================
# 4. DATASET VALIDATORS
# ==============================================================================

def validate_csv_structure_and_schema(
    filepath: Path,
    expected_filename: str,
    ctx: ValidationContext,
) -> Optional[List[List[str]]]:
    """
    Validates:
      - File existence and non-emptiness
      - Exact header list and exact column order
      - Returns raw rows (excluding header) if successful, None otherwise.
    """
    if not filepath.exists():
        ctx.add_error(expected_filename, "file_existence", f"Required CSV file missing: {filepath}")
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            try:
                headers = next(reader)
            except StopIteration:
                ctx.add_error(expected_filename, "file_empty", "File is completely empty (no header).")
                return None

            expected_headers = CANONICAL_SCHEMAS[expected_filename]
            if headers != expected_headers:
                ctx.add_error(
                    expected_filename,
                    "schema_mismatch",
                    f"Header mismatch.\nExpected: {expected_headers}\nActual:   {headers}",
                )
                return None

            rows = list(reader)
            ctx.row_counts[expected_filename] = len(rows)
            return rows

    except Exception as e:
        ctx.add_error(expected_filename, "read_error", f"Failed to read CSV: {e}")
        return None


def validate_ports(
    rows: List[List[str]],
    ctx: ValidationContext,
) -> Dict[str, Dict[str, Any]]:
    """Validates ports.csv and returns port lookup dict."""
    dataset = "ports.csv"
    expected_headers = CANONICAL_SCHEMAS[dataset]
    col_idx = {h: i for i, h in enumerate(expected_headers)}

    port_map: Dict[str, Dict[str, Any]] = {}
    seen_ids: Set[str] = set()
    seen_names: Set[str] = set()

    for row_num, row in enumerate(rows, start=2):
        if len(row) != len(expected_headers):
            ctx.add_error(dataset, "column_count", f"Row {row_num} has {len(row)} columns, expected {len(expected_headers)}")
            continue

        port_id = row[col_idx["port_id"]].strip()
        port_name = row[col_idx["port_name"]].strip()
        country = row[col_idx["country"]].strip()
        loa_str = row[col_idx["max_loa_m"]].strip()
        beam_str = row[col_idx["max_beam_m"]].strip()
        draft_str = row[col_idx["max_draft_m"]].strip()
        rate_str = row[col_idx["handling_rate_tpd"]].strip()
        turnaround_str = row[col_idx["typical_turnaround_hours"]].strip()
        source = row[col_idx["source"]].strip()
        data_type = row[col_idx["data_type"]].strip()

        # Primary Key uniqueness
        if not port_id or port_id != row[col_idx["port_id"]]:
            ctx.add_error(dataset, "primary_key", f"Row {row_num}: Invalid or whitespace in port_id '{port_id}'")
        if port_id in seen_ids:
            ctx.add_error(dataset, "primary_key", f"Row {row_num}: Duplicate port_id '{port_id}'")
        seen_ids.add(port_id)

        if port_name in seen_names:
            ctx.add_error(dataset, "unique_constraint", f"Row {row_num}: Duplicate port_name '{port_name}'")
        seen_names.add(port_name)

        # Provenance
        if source != EXPECTED_SOURCE:
            ctx.add_error(dataset, "provenance", f"Row {row_num}: Invalid source '{source}'")
        if data_type != EXPECTED_DATA_TYPE:
            ctx.add_error(dataset, "provenance", f"Row {row_num}: Invalid data_type '{data_type}'")

        # Physical bounds
        loa = parse_float(loa_str, "max_loa_m", f"Row {row_num}")
        beam = parse_float(beam_str, "max_beam_m", f"Row {row_num}")
        draft = parse_float(draft_str, "max_draft_m", f"Row {row_num}")
        rate = parse_float(rate_str, "handling_rate_tpd", f"Row {row_num}")
        turnaround = parse_float(turnaround_str, "typical_turnaround_hours", f"Row {row_num}")

        for name, val in [("max_loa_m", loa), ("max_beam_m", beam), ("max_draft_m", draft), ("handling_rate_tpd", rate), ("typical_turnaround_hours", turnaround)]:
            if val is None or val <= 0:
                ctx.add_error(dataset, "physical_bounds", f"Row {row_num} ({port_id}): {name} must be > 0, got {val}")

        if port_id and loa and beam and draft:
            port_map[port_id] = {
                "port_name": port_name,
                "country": country,
                "max_loa_m": loa,
                "max_beam_m": beam,
                "max_draft_m": draft,
                "handling_rate_tpd": rate,
                "typical_turnaround_hours": turnaround,
            }

    return port_map


def validate_berths(
    rows: List[List[str]],
    port_map: Dict[str, Dict[str, Any]],
    ctx: ValidationContext,
) -> Dict[str, Dict[str, Any]]:
    """Validates berths.csv and enforces berth draft <= port draft."""
    dataset = "berths.csv"
    expected_headers = CANONICAL_SCHEMAS[dataset]
    col_idx = {h: i for i, h in enumerate(expected_headers)}

    berth_map: Dict[str, Dict[str, Any]] = {}
    seen_ids: Set[str] = set()

    for row_num, row in enumerate(rows, start=2):
        if len(row) != len(expected_headers):
            ctx.add_error(dataset, "column_count", f"Row {row_num} has {len(row)} columns")
            continue

        berth_id = row[col_idx["berth_id"]].strip()
        port_id = row[col_idx["port_id"]].strip()
        berth_name = row[col_idx["berth_name"]].strip()
        commodity = row[col_idx["commodity"]].strip()
        loa_str = row[col_idx["max_loa_m"]].strip()
        beam_str = row[col_idx["max_beam_m"]].strip()
        draft_str = row[col_idx["max_draft_m"]].strip()
        rate_str = row[col_idx["handling_rate_tpd"]].strip()
        source = row[col_idx["source"]].strip()
        data_type = row[col_idx["data_type"]].strip()

        # Primary Key
        if not berth_id or berth_id in seen_ids:
            ctx.add_error(dataset, "primary_key", f"Row {row_num}: Duplicate or empty berth_id '{berth_id}'")
        seen_ids.add(berth_id)

        # Foreign Key to ports.csv
        if port_id not in port_map:
            ctx.add_error(dataset, "foreign_key", f"Row {row_num} ({berth_id}): Orphan port_id '{port_id}' not found in ports.csv")

        # Commodity Vocabulary
        if commodity not in CANONICAL_COMMODITIES:
            ctx.add_error(dataset, "vocabulary", f"Row {row_num} ({berth_id}): Invalid commodity '{commodity}'")

        # Provenance
        if source != EXPECTED_SOURCE or data_type != EXPECTED_DATA_TYPE:
            ctx.add_error(dataset, "provenance", f"Row {row_num}: Invalid provenance ({source}, {data_type})")

        # Physical bounds & hierarchy
        loa = parse_float(loa_str, "max_loa_m", f"Row {row_num}")
        beam = parse_float(beam_str, "max_beam_m", f"Row {row_num}")
        draft = parse_float(draft_str, "max_draft_m", f"Row {row_num}")
        rate = parse_float(rate_str, "handling_rate_tpd", f"Row {row_num}")

        for name, val in [("max_loa_m", loa), ("max_beam_m", beam), ("max_draft_m", draft), ("handling_rate_tpd", rate)]:
            if val is None or val <= 0:
                ctx.add_error(dataset, "physical_bounds", f"Row {row_num} ({berth_id}): {name} must be > 0, got {val}")

        # Berth Draft <= Parent Port Draft
        if port_id in port_map and draft is not None:
            parent_port_draft = port_map[port_id]["max_draft_m"]
            if draft > parent_port_draft:
                ctx.add_error(
                    dataset,
                    "draft_hierarchy",
                    f"Row {row_num} ({berth_id}): Berth max_draft_m ({draft}m) exceeds parent port {port_id} draft ({parent_port_draft}m)",
                )

        if berth_id and port_id and loa and beam and draft:
            berth_map[berth_id] = {
                "port_id": port_id,
                "commodity": commodity,
                "max_loa_m": loa,
                "max_beam_m": beam,
                "max_draft_m": draft,
                "handling_rate_tpd": rate,
            }

    return berth_map


def validate_vessel_classes(
    rows: List[List[str]],
    ctx: ValidationContext,
) -> Dict[str, Dict[str, Any]]:
    """Validates vessel_classes.csv and enforces cargo capacity < DWT max."""
    dataset = "vessel_classes.csv"
    expected_headers = CANONICAL_SCHEMAS[dataset]
    col_idx = {h: i for i, h in enumerate(expected_headers)}

    vessel_map: Dict[str, Dict[str, Any]] = {}
    seen_ids: Set[str] = set()

    for row_num, row in enumerate(rows, start=2):
        if len(row) != len(expected_headers):
            ctx.add_error(dataset, "column_count", f"Row {row_num} has {len(row)} columns")
            continue

        vc_id = row[col_idx["vessel_class_id"]].strip()
        vc_name = row[col_idx["vessel_class_name"]].strip()
        dwt_min_str = row[col_idx["dwt_min_mt"]].strip()
        dwt_max_str = row[col_idx["dwt_max_mt"]].strip()
        loa_str = row[col_idx["loa_m"]].strip()
        beam_str = row[col_idx["beam_m"]].strip()
        draft_str = row[col_idx["draft_m"]].strip()
        speed_str = row[col_idx["speed_knots"]].strip()
        capacity_str = row[col_idx["cargo_capacity_mt"]].strip()
        fuel_str = row[col_idx["fuel_consumption_mt_day"]].strip()
        source = row[col_idx["source"]].strip()
        data_type = row[col_idx["data_type"]].strip()

        # Vocabulary
        if vc_id not in CANONICAL_VESSEL_CLASSES:
            ctx.add_error(dataset, "vocabulary", f"Row {row_num}: Invalid vessel_class_id '{vc_id}'")
        if vc_id in seen_ids:
            ctx.add_error(dataset, "primary_key", f"Row {row_num}: Duplicate vessel_class_id '{vc_id}'")
        seen_ids.add(vc_id)

        # Provenance
        if source != EXPECTED_SOURCE or data_type != EXPECTED_DATA_TYPE:
            ctx.add_error(dataset, "provenance", f"Row {row_num}: Invalid provenance ({source}, {data_type})")

        dwt_min = parse_float(dwt_min_str, "dwt_min_mt", f"Row {row_num}")
        dwt_max = parse_float(dwt_max_str, "dwt_max_mt", f"Row {row_num}")
        loa = parse_float(loa_str, "loa_m", f"Row {row_num}")
        beam = parse_float(beam_str, "beam_m", f"Row {row_num}")
        draft = parse_float(draft_str, "draft_m", f"Row {row_num}")
        speed = parse_float(speed_str, "speed_knots", f"Row {row_num}")
        capacity = parse_float(capacity_str, "cargo_capacity_mt", f"Row {row_num}")
        fuel = parse_float(fuel_str, "fuel_consumption_mt_day", f"Row {row_num}")

        for name, val in [("dwt_min_mt", dwt_min), ("dwt_max_mt", dwt_max), ("loa_m", loa), ("beam_m", beam), ("draft_m", draft), ("speed_knots", speed), ("cargo_capacity_mt", capacity), ("fuel_consumption_mt_day", fuel)]:
            if val is None or val <= 0:
                ctx.add_error(dataset, "physical_bounds", f"Row {row_num} ({vc_id}): {name} must be > 0, got {val}")

        # DWT Range: min < max
        if dwt_min is not None and dwt_max is not None and dwt_min >= dwt_max:
            ctx.add_error(dataset, "dwt_range", f"Row {row_num} ({vc_id}): dwt_min_mt ({dwt_min}) >= dwt_max_mt ({dwt_max})")

        # Invariant: cargo_capacity_mt < dwt_max_mt
        if capacity is not None and dwt_max is not None and capacity >= dwt_max:
            ctx.add_error(dataset, "capacity_invariant", f"Row {row_num} ({vc_id}): cargo_capacity_mt ({capacity}) >= dwt_max_mt ({dwt_max})")

        if vc_id and loa and beam and draft:
            vessel_map[vc_id] = {
                "name": vc_name,
                "loa_m": loa,
                "beam_m": beam,
                "draft_m": draft,
                "cargo_capacity_mt": capacity,
            }

    return vessel_map


def validate_routes(
    rows: List[List[str]],
    port_map: Dict[str, Dict[str, Any]],
    ctx: ValidationContext,
) -> Dict[str, Dict[str, Any]]:
    """Validates routes.csv, natural grain uniqueness, and foreign keys."""
    dataset = "routes.csv"
    expected_headers = CANONICAL_SCHEMAS[dataset]
    col_idx = {h: i for i, h in enumerate(expected_headers)}

    route_map: Dict[str, Dict[str, Any]] = {}
    seen_ids: Set[str] = set()
    seen_grains: Set[Tuple[str, str, str]] = set()

    for row_num, row in enumerate(rows, start=2):
        if len(row) != len(expected_headers):
            ctx.add_error(dataset, "column_count", f"Row {row_num} has {len(row)} columns")
            continue

        route_id = row[col_idx["route_id"]].strip()
        orig = row[col_idx["origin_port_id"]].strip()
        dest = row[col_idx["destination_port_id"]].strip()
        commodity = row[col_idx["commodity"]].strip()
        dist_str = row[col_idx["distance_nm"]].strip()
        sailing_str = row[col_idx["typical_sailing_days"]].strip()
        source = row[col_idx["source"]].strip()
        data_type = row[col_idx["data_type"]].strip()

        # Primary Key
        if not route_id or route_id in seen_ids:
            ctx.add_error(dataset, "primary_key", f"Row {row_num}: Duplicate or empty route_id '{route_id}'")
        seen_ids.add(route_id)

        # Natural Grain Uniqueness: origin + destination + commodity
        grain = (orig, dest, commodity)
        if grain in seen_grains:
            ctx.add_error(dataset, "grain_uniqueness", f"Row {row_num}: Duplicate route grain {grain}")
        seen_grains.add(grain)

        # Foreign Keys to ports
        if orig not in port_map:
            ctx.add_error(dataset, "foreign_key", f"Row {row_num} ({route_id}): Orphan origin_port_id '{orig}'")
        if dest not in port_map:
            ctx.add_error(dataset, "foreign_key", f"Row {row_num} ({route_id}): Orphan destination_port_id '{dest}'")

        # Origin != Destination
        if orig == dest:
            ctx.add_error(dataset, "geographic_integrity", f"Row {row_num} ({route_id}): Self-loop route {orig} == {dest}")

        # Commodity Vocabulary
        if commodity not in CANONICAL_COMMODITIES:
            ctx.add_error(dataset, "vocabulary", f"Row {row_num} ({route_id}): Invalid commodity '{commodity}'")

        # Provenance
        if source != EXPECTED_SOURCE or data_type != EXPECTED_DATA_TYPE:
            ctx.add_error(dataset, "provenance", f"Row {row_num}: Invalid provenance ({source}, {data_type})")

        # Distance & Sailing Days
        dist = parse_float(dist_str, "distance_nm", f"Row {row_num}")
        sailing = parse_float(sailing_str, "typical_sailing_days", f"Row {row_num}")

        if dist is None or dist <= 0:
            ctx.add_error(dataset, "physical_bounds", f"Row {row_num} ({route_id}): distance_nm must be > 0, got {dist}")
        if sailing is None or sailing <= 0:
            ctx.add_error(dataset, "physical_bounds", f"Row {row_num} ({route_id}): typical_sailing_days must be > 0, got {sailing}")

        if route_id:
            route_map[route_id] = {
                "origin_port_id": orig,
                "destination_port_id": dest,
                "commodity": commodity,
                "distance_nm": dist,
                "typical_sailing_days": sailing,
            }

    return route_map


def validate_freight_rates(
    rows: List[List[str]],
    route_map: Dict[str, Dict[str, Any]],
    vessel_map: Dict[str, Dict[str, Any]],
    ctx: ValidationContext,
) -> None:
    """
    Validates freight_rates.csv:
      - Grain: observation_date + route_id + vessel_class_id + freight_unit
      - Total rows: 245,616
      - Date continuity: 731 dates per series slice
      - Positivity: freight_value > 0
      - Economic Hierarchy on comparable route/date slices:
          USD_PER_MT: CAPESIZE < PANAMAX < SUPRAMAX
          USD_PER_DAY: CAPESIZE > PANAMAX > SUPRAMAX
    """
    dataset = "freight_rates.csv"
    expected_headers = CANONICAL_SCHEMAS[dataset]
    col_idx = {h: i for i, h in enumerate(expected_headers)}

    seen_ids: Set[str] = set()
    # Track counts and date presence per slice: (route_id, vessel_class_id, freight_unit) -> Set[date]
    series_date_map: Dict[Tuple[str, str, str], Set[datetime.date]] = defaultdict(set)

    # For hierarchy evaluation: (route_id, date_str, freight_unit) -> {vessel_class_id: freight_value}
    slice_hierarchy: Dict[Tuple[str, str, str], Dict[str, float]] = defaultdict(dict)

    non_positive_count = 0
    duplicate_grain_count = 0
    foreign_key_errors = 0

    for row_num, row in enumerate(rows, start=2):
        if len(row) != len(expected_headers):
            ctx.add_error(dataset, "column_count", f"Row {row_num} has {len(row)} columns")
            continue

        rate_id = row[col_idx["freight_rate_id"]].strip()
        date_str = row[col_idx["observation_date"]].strip()
        route_id = row[col_idx["route_id"]].strip()
        vc_id = row[col_idx["vessel_class_id"]].strip()
        val_str = row[col_idx["freight_value"]].strip()
        unit = row[col_idx["freight_unit"]].strip()
        currency = row[col_idx["currency"]].strip()
        data_type = row[col_idx["data_type"]].strip()
        source = row[col_idx["source"]].strip()

        # Primary Key
        if rate_id in seen_ids:
            ctx.add_error(dataset, "primary_key", f"Row {row_num}: Duplicate freight_rate_id '{rate_id}'")
        seen_ids.add(rate_id)

        # Foreign keys
        if route_id not in route_map:
            if foreign_key_errors < 5:
                ctx.add_error(dataset, "foreign_key", f"Row {row_num}: Orphan route_id '{route_id}'")
            foreign_key_errors += 1

        if vc_id not in vessel_map:
            if foreign_key_errors < 5:
                ctx.add_error(dataset, "foreign_key", f"Row {row_num}: Orphan vessel_class_id '{vc_id}'")
            foreign_key_errors += 1

        # Unit and Currency
        if unit not in CANONICAL_FREIGHT_UNITS:
            ctx.add_error(dataset, "vocabulary", f"Row {row_num}: Invalid freight_unit '{unit}'")
        if currency != EXPECTED_CURRENCY:
            ctx.add_error(dataset, "vocabulary", f"Row {row_num}: Currency must be USD, got '{currency}'")

        # Provenance
        if source != EXPECTED_SOURCE or data_type != EXPECTED_DATA_TYPE:
            ctx.add_error(dataset, "provenance", f"Row {row_num}: Invalid provenance ({source}, {data_type})")

        # Value positivity
        val = parse_float(val_str, "freight_value", f"Row {row_num}")
        if val is None or val <= 0:
            non_positive_count += 1
            if non_positive_count <= 3:
                ctx.add_error(dataset, "positivity", f"Row {row_num}: freight_value must be > 0, got {val}")

        # Date validation
        d = parse_date(date_str)
        if d is None or not (START_DATE <= d <= END_DATE):
            ctx.add_error(dataset, "date_range", f"Row {row_num}: observation_date '{date_str}' out of window")
        else:
            slice_key = (route_id, vc_id, unit)
            if d in series_date_map[slice_key]:
                duplicate_grain_count += 1
                if duplicate_grain_count <= 3:
                    ctx.add_error(dataset, "grain_uniqueness", f"Row {row_num}: Duplicate date {d} for slice {slice_key}")
            else:
                series_date_map[slice_key].add(d)

            if val is not None:
                slice_hierarchy[(route_id, date_str, unit)][vc_id] = val

    # Verify temporal completeness for all 336 series slices (28 routes x 6 vessels x 2 units)
    expected_slices = 28 * 6 * 2
    if len(series_date_map) != expected_slices:
        ctx.add_error(
            dataset,
            "slice_count",
            f"Expected {expected_slices} distinct (route, vessel, unit) slices, found {len(series_date_map)}",
        )

    missing_date_slices = 0
    for slice_key, date_set in series_date_map.items():
        if len(date_set) != EXPECTED_DAYS_COUNT:
            missing_date_slices += 1
            if missing_date_slices <= 3:
                ctx.add_error(
                    dataset,
                    "date_continuity",
                    f"Slice {slice_key} has {len(date_set)} observations, expected {EXPECTED_DAYS_COUNT}",
                )

    # Economic Hierarchy Validation across all comparable (route, date) slices
    mt_violations = []
    day_violations = []

    for (rt, dt, unit), v_map in slice_hierarchy.items():
        if "CAPESIZE" in v_map and "PANAMAX" in v_map and "SUPRAMAX" in v_map:
            c = v_map["CAPESIZE"]
            p = v_map["PANAMAX"]
            s = v_map["SUPRAMAX"]

            if unit == "USD_PER_MT":
                if not (c < p < s):
                    mt_violations.append((rt, dt, c, p, s))
            elif unit == "USD_PER_DAY":
                if not (c > p > s):
                    day_violations.append((rt, dt, c, p, s))

    if mt_violations:
        ctx.add_error(
            dataset,
            "freight_hierarchy_mt",
            f"{len(mt_violations)} slices violated USD_PER_MT hierarchy (CAPESIZE < PANAMAX < SUPRAMAX). Example: Route {mt_violations[0][0]} Date {mt_violations[0][1]}: Capesize={mt_violations[0][2]}, Panamax={mt_violations[0][3]}, Supramax={mt_violations[0][4]}",
        )

    if day_violations:
        ctx.add_error(
            dataset,
            "freight_hierarchy_day",
            f"{len(day_violations)} slices violated USD_PER_DAY hierarchy (CAPESIZE > PANAMAX > SUPRAMAX). Example: Route {day_violations[0][0]} Date {day_violations[0][1]}: Capesize={day_violations[0][2]}, Panamax={day_violations[0][3]}, Supramax={day_violations[0][4]}",
        )


def validate_commodity_prices(
    rows: List[List[str]],
    ctx: ValidationContext,
) -> None:
    """Validates commodity_prices.csv."""
    dataset = "commodity_prices.csv"
    expected_headers = CANONICAL_SCHEMAS[dataset]
    col_idx = {h: i for i, h in enumerate(expected_headers)}

    seen_ids: Set[str] = set()
    series_dates: Dict[Tuple[str, str], Set[datetime.date]] = defaultdict(set)

    for row_num, row in enumerate(rows, start=2):
        if len(row) != len(expected_headers):
            ctx.add_error(dataset, "column_count", f"Row {row_num} has {len(row)} columns")
            continue

        cp_id = row[col_idx["commodity_price_id"]].strip()
        date_str = row[col_idx["observation_date"]].strip()
        comm = row[col_idx["commodity"]].strip()
        market = row[col_idx["market"]].strip()
        val_str = row[col_idx["price_value"]].strip()
        currency = row[col_idx["currency"]].strip()
        unit = row[col_idx["unit"]].strip()
        data_type = row[col_idx["data_type"]].strip()
        source = row[col_idx["source"]].strip()

        if cp_id in seen_ids:
            ctx.add_error(dataset, "primary_key", f"Row {row_num}: Duplicate commodity_price_id '{cp_id}'")
        seen_ids.add(cp_id)

        if comm not in CANONICAL_COMMODITIES:
            ctx.add_error(dataset, "vocabulary", f"Row {row_num}: Invalid commodity '{comm}'")

        if currency != EXPECTED_CURRENCY or unit != "USD_PER_MT":
            ctx.add_error(dataset, "unit_currency", f"Row {row_num}: Invalid currency/unit ({currency}, {unit})")

        if source != EXPECTED_SOURCE or data_type != EXPECTED_DATA_TYPE:
            ctx.add_error(dataset, "provenance", f"Row {row_num}: Invalid provenance ({source}, {data_type})")

        val = parse_float(val_str, "price_value", f"Row {row_num}")
        if val is None or val <= 0:
            ctx.add_error(dataset, "positivity", f"Row {row_num}: price_value must be > 0, got {val}")

        d = parse_date(date_str)
        if d is None or not (START_DATE <= d <= END_DATE):
            ctx.add_error(dataset, "date_range", f"Row {row_num}: Invalid observation_date '{date_str}'")
        else:
            series_dates[(comm, market)].add(d)

    # 2 commodities x 1 market = 2 series slices, each with 731 dates
    if len(series_dates) != 2:
        ctx.add_error(dataset, "series_count", f"Expected exactly 2 commodity series, found {len(series_dates)}")
    for (comm, mkt), dates in series_dates.items():
        if len(dates) != EXPECTED_DAYS_COUNT:
            ctx.add_error(dataset, "date_continuity", f"Series ({comm}, {mkt}) has {len(dates)} dates, expected {EXPECTED_DAYS_COUNT}")


def validate_fuel_prices(
    rows: List[List[str]],
    ctx: ValidationContext,
) -> None:
    """Validates fuel_prices.csv."""
    dataset = "fuel_prices.csv"
    expected_headers = CANONICAL_SCHEMAS[dataset]
    col_idx = {h: i for i, h in enumerate(expected_headers)}

    seen_ids: Set[str] = set()
    series_dates: Dict[str, Set[datetime.date]] = defaultdict(set)

    for row_num, row in enumerate(rows, start=2):
        if len(row) != len(expected_headers):
            ctx.add_error(dataset, "column_count", f"Row {row_num} has {len(row)} columns")
            continue

        fp_id = row[col_idx["fuel_price_id"]].strip()
        date_str = row[col_idx["observation_date"]].strip()
        fuel_type = row[col_idx["fuel_type"]].strip()
        val_str = row[col_idx["price_value"]].strip()
        currency = row[col_idx["currency"]].strip()
        unit = row[col_idx["unit"]].strip()
        data_type = row[col_idx["data_type"]].strip()
        source = row[col_idx["source"]].strip()

        if fp_id in seen_ids:
            ctx.add_error(dataset, "primary_key", f"Row {row_num}: Duplicate fuel_price_id '{fp_id}'")
        seen_ids.add(fp_id)

        if fuel_type not in CANONICAL_FUEL_TYPES:
            ctx.add_error(dataset, "vocabulary", f"Row {row_num}: Invalid fuel_type '{fuel_type}'")

        if currency != EXPECTED_CURRENCY or unit != "USD_PER_MT":
            ctx.add_error(dataset, "unit_currency", f"Row {row_num}: Invalid currency/unit ({currency}, {unit})")

        if source != EXPECTED_SOURCE or data_type != EXPECTED_DATA_TYPE:
            ctx.add_error(dataset, "provenance", f"Row {row_num}: Invalid provenance ({source}, {data_type})")

        val = parse_float(val_str, "price_value", f"Row {row_num}")
        if val is None or val <= 0:
            ctx.add_error(dataset, "positivity", f"Row {row_num}: price_value must be > 0, got {val}")

        d = parse_date(date_str)
        if d is None or not (START_DATE <= d <= END_DATE):
            ctx.add_error(dataset, "date_range", f"Row {row_num}: Invalid observation_date '{date_str}'")
        else:
            series_dates[fuel_type].add(d)

    # 2 fuel types (VLSFO active, MGO reference-only) x 731 dates
    if len(series_dates) != 2:
        ctx.add_error(dataset, "series_count", f"Expected exactly 2 fuel series, found {len(series_dates)}")
    for fuel_type, dates in series_dates.items():
        if len(dates) != EXPECTED_DAYS_COUNT:
            ctx.add_error(dataset, "date_continuity", f"Fuel series '{fuel_type}' has {len(dates)} dates, expected {EXPECTED_DAYS_COUNT}")


def validate_port_activity(
    rows: List[List[str]],
    port_map: Dict[str, Dict[str, Any]],
    ctx: ValidationContext,
) -> None:
    """Validates port_activity.csv."""
    dataset = "port_activity.csv"
    expected_headers = CANONICAL_SCHEMAS[dataset]
    col_idx = {h: i for i, h in enumerate(expected_headers)}

    seen_ids: Set[str] = set()
    series_dates: Dict[str, Set[datetime.date]] = defaultdict(set)

    for row_num, row in enumerate(rows, start=2):
        if len(row) != len(expected_headers):
            ctx.add_error(dataset, "column_count", f"Row {row_num} has {len(row)} columns")
            continue

        act_id = row[col_idx["activity_id"]].strip()
        date_str = row[col_idx["observation_date"]].strip()
        port_id = row[col_idx["port_id"]].strip()
        arrivals_str = row[col_idx["vessel_arrivals"]].strip()
        waiting_str = row[col_idx["average_waiting_hours"]].strip()
        turnaround_str = row[col_idx["average_turnaround_hours"]].strip()
        congestion = row[col_idx["congestion_level"]].strip()
        source = row[col_idx["source"]].strip()
        data_type = row[col_idx["data_type"]].strip()

        if act_id in seen_ids:
            ctx.add_error(dataset, "primary_key", f"Row {row_num}: Duplicate activity_id '{act_id}'")
        seen_ids.add(act_id)

        if port_id not in port_map:
            ctx.add_error(dataset, "foreign_key", f"Row {row_num}: Orphan port_id '{port_id}'")

        arrivals = parse_int(arrivals_str)
        waiting = parse_float(waiting_str, "average_waiting_hours", f"Row {row_num}")
        turnaround = parse_float(turnaround_str, "average_turnaround_hours", f"Row {row_num}")

        if arrivals is None or arrivals < 0:
            ctx.add_error(dataset, "bounds", f"Row {row_num}: vessel_arrivals must be >= 0, got {arrivals_str}")
        if waiting is None or waiting < 0:
            ctx.add_error(dataset, "bounds", f"Row {row_num}: average_waiting_hours must be >= 0, got {waiting_str}")
        if turnaround is None or turnaround <= 0:
            ctx.add_error(dataset, "bounds", f"Row {row_num}: average_turnaround_hours must be > 0, got {turnaround_str}")

        if congestion not in CANONICAL_CONGESTION_LEVELS:
            ctx.add_error(dataset, "vocabulary", f"Row {row_num}: Invalid congestion_level '{congestion}'")

        if source != EXPECTED_SOURCE or data_type != EXPECTED_DATA_TYPE:
            ctx.add_error(dataset, "provenance", f"Row {row_num}: Invalid provenance ({source}, {data_type})")

        d = parse_date(date_str)
        if d is None or not (START_DATE <= d <= END_DATE):
            ctx.add_error(dataset, "date_range", f"Row {row_num}: Invalid observation_date '{date_str}'")
        else:
            series_dates[port_id].add(d)

    # 15 ports x 731 dates
    if len(series_dates) != 15:
        ctx.add_error(dataset, "port_count", f"Expected activity series for 15 ports, found {len(series_dates)}")
    for pid, dates in series_dates.items():
        if len(dates) != EXPECTED_DAYS_COUNT:
            ctx.add_error(dataset, "date_continuity", f"Port '{pid}' has {len(dates)} dates, expected {EXPECTED_DAYS_COUNT}")


def validate_scenario_defaults(
    rows: List[List[str]],
    ctx: ValidationContext,
) -> None:
    """Validates scenario_defaults.csv and verifies exact required preset values."""
    dataset = "scenario_defaults.csv"
    expected_headers = CANONICAL_SCHEMAS[dataset]
    col_idx = {h: i for i, h in enumerate(expected_headers)}

    seen_ids: Set[str] = set()

    expected_scenarios = {
        "BASELINE": {
            "freight_change_pct": 0.0,
            "fuel_change_pct": 0.0,
            "delay_hours": 0.0,
            "congestion": "MEDIUM",
        },
        "ADVERSE": {
            "freight_change_pct": 25.0,
            "fuel_change_pct": 15.0,
            "delay_hours": 48.0,
            "congestion": "HIGH",
        },
        "FAVORABLE": {
            "freight_change_pct": -15.0,
            "fuel_change_pct": -10.0,
            "delay_hours": 0.0,
            "congestion": "LOW",
        },
    }

    for row_num, row in enumerate(rows, start=2):
        if len(row) != len(expected_headers):
            ctx.add_error(dataset, "column_count", f"Row {row_num} has {len(row)} columns")
            continue

        sc_id = row[col_idx["scenario_id"]].strip()
        sc_name = row[col_idx["scenario_name"]].strip()
        f_chg = parse_float(row[col_idx["freight_change_pct"]].strip(), "freight_change_pct", f"Row {row_num}")
        b_chg = parse_float(row[col_idx["fuel_change_pct"]].strip(), "fuel_change_pct", f"Row {row_num}")
        delay = parse_float(row[col_idx["delay_hours"]].strip(), "delay_hours", f"Row {row_num}")
        cong = row[col_idx["port_congestion_level"]].strip()
        desc = row[col_idx["description"]].strip()
        source = row[col_idx["source"]].strip()
        data_type = row[col_idx["data_type"]].strip()

        if sc_id not in CANONICAL_SCENARIOS:
            ctx.add_error(dataset, "vocabulary", f"Row {row_num}: Invalid scenario_id '{sc_id}'")
        if sc_id in seen_ids:
            ctx.add_error(dataset, "primary_key", f"Row {row_num}: Duplicate scenario_id '{sc_id}'")
        seen_ids.add(sc_id)

        if source != EXPECTED_SOURCE or data_type != EXPECTED_DATA_TYPE:
            ctx.add_error(dataset, "provenance", f"Row {row_num}: Invalid provenance ({source}, {data_type})")

        # Check exact required values
        if sc_id in expected_scenarios:
            exp = expected_scenarios[sc_id]
            if f_chg != exp["freight_change_pct"]:
                ctx.add_error(dataset, "preset_value", f"{sc_id} freight_change_pct expected {exp['freight_change_pct']}, got {f_chg}")
            if b_chg != exp["fuel_change_pct"]:
                ctx.add_error(dataset, "preset_value", f"{sc_id} fuel_change_pct expected {exp['fuel_change_pct']}, got {b_chg}")
            if delay != exp["delay_hours"]:
                ctx.add_error(dataset, "preset_value", f"{sc_id} delay_hours expected {exp['delay_hours']}, got {delay}")
            if cong != exp["congestion"]:
                ctx.add_error(dataset, "preset_value", f"{sc_id} port_congestion_level expected {exp['congestion']}, got {cong}")

    if seen_ids != CANONICAL_SCENARIOS:
        ctx.add_error(dataset, "scenario_set", f"Expected scenarios {CANONICAL_SCENARIOS}, found {seen_ids}")


# ==============================================================================
# 5. CROSS-DATASET FEASIBILITY COVERAGE VALIDATION
# ==============================================================================

def validate_feasibility_coverage(
    port_map: Dict[str, Dict[str, Any]],
    berth_map: Dict[str, Dict[str, Any]],
    vessel_map: Dict[str, Dict[str, Any]],
    route_map: Dict[str, Dict[str, Any]],
    ctx: ValidationContext,
) -> None:
    """
    Validates three-tier feasibility coverage:
      1. Feasible vessel-route cases exist (e.g. Capesize on deepwater routes, Supramax/Panamax on standard routes)
      2. Infeasible vessel-route cases exist (e.g. Capesize at Haldia or Sagar-Sandheads due to draft limits)
      3. Insufficient feasibility data cases exist (e.g. Baltimore for thermal coal, Taboneo for coking coal)
    """
    dataset = "cross_dataset_feasibility"
    feasible_count = 0
    infeasible_count = 0
    insufficient_data_count = 0

    # Helper function to check feasibility for (vessel, route)
    for route_id, r in route_map.items():
        orig_port = r["origin_port_id"]
        dest_port = r["destination_port_id"]
        commodity = r["commodity"]

        # Find berths handling commodity at origin
        orig_berths = [
            b for b in berth_map.values()
            if b["port_id"] == orig_port and b["commodity"] == commodity
        ]
        # Find berths handling commodity at destination
        dest_berths = [
            b for b in berth_map.values()
            if b["port_id"] == dest_port and b["commodity"] == commodity
        ]

        if not orig_berths or not dest_berths:
            insufficient_data_count += 1
            continue

        for vc_id, v in vessel_map.items():
            # Check origin physical compatibility across candidate berths
            orig_ok = any(
                v["loa_m"] <= b["max_loa_m"] and
                v["beam_m"] <= b["max_beam_m"] and
                v["draft_m"] <= b["max_draft_m"]
                for b in orig_berths
            )
            # Check destination physical compatibility across candidate berths
            dest_ok = any(
                v["loa_m"] <= b["max_loa_m"] and
                v["beam_m"] <= b["max_beam_m"] and
                v["draft_m"] <= b["max_draft_m"]
                for b in dest_berths
            )

            if orig_ok and dest_ok:
                feasible_count += 1
            else:
                infeasible_count += 1

    # Also test that out-of-route port/commodity pairs trigger insufficient feasibility data
    # (e.g., Baltimore has NO thermal berth; Taboneo/Samarinda have NO coking berth)
    baltimore_thermal = [b for b in berth_map.values() if b["port_id"] == "BALTIMORE" and b["commodity"] == "THERMAL_COAL"]
    taboneo_coking = [b for b in berth_map.values() if b["port_id"] == "TABONEO" and b["commodity"] == "COKING_COAL"]

    if len(baltimore_thermal) == 0:
        insufficient_data_count += 1
    if len(taboneo_coking) == 0:
        insufficient_data_count += 1

    if feasible_count == 0:
        ctx.add_error(dataset, "feasible_coverage", "Zero feasible vessel/route combinations found in reference data.")
    if infeasible_count == 0:
        ctx.add_error(dataset, "infeasible_coverage", "Zero infeasible vessel/route combinations found (no draft/dimension rejection capability).")
    if insufficient_data_count == 0:
        ctx.add_error(dataset, "insufficient_coverage", "Zero insufficient-feasibility-data paths found (ports must intentionally lack certain commodity berths).")


# ==============================================================================
# 6. MAIN RUNNER & REPORTING
# ==============================================================================

def validate_all_reference_data(data_dir: Path) -> int:
    """
    Executes full pre-seeding validation gate across all 9 canonical CSVs.
    Returns:
      0 if validation PASSES
      1 if validation FAILS
    """
    print("=" * 70)
    print("  DockTech V1 — Reference Data Validation Gate")
    print(f"  Target Directory: {data_dir.resolve()}")
    print("=" * 70)

    ctx = ValidationContext()

    # Step 1: Validate existence, headers, and row counts of all 9 files
    raw_datasets: Dict[str, List[List[str]]] = {}
    for filename in CANONICAL_SCHEMAS.keys():
        filepath = data_dir / filename
        rows = validate_csv_structure_and_schema(filepath, filename, ctx)
        if rows is not None:
            raw_datasets[filename] = rows

    # Step 2: Validate Row Counts against Frozen Design Expectations
    for filename, expected_len in EXPECTED_ROW_COUNTS.items():
        actual_len = ctx.row_counts.get(filename, 0)
        if actual_len != expected_len:
            ctx.add_error(
                filename,
                "row_count",
                f"Row count mismatch. Expected {expected_len:,d} rows, got {actual_len:,d} rows",
            )

    total_actual_rows = sum(ctx.row_counts.values())
    if total_actual_rows != EXPECTED_TOTAL_ROWS:
        ctx.add_error(
            "global_counts",
            "total_rows",
            f"Total row count across 9 datasets is {total_actual_rows:,d}, expected {EXPECTED_TOTAL_ROWS:,d}",
        )

    # Step 3: Parse and Validate Static Tables
    port_map = {}
    if "ports.csv" in raw_datasets:
        port_map = validate_ports(raw_datasets["ports.csv"], ctx)

    berth_map = {}
    if "berths.csv" in raw_datasets:
        berth_map = validate_berths(raw_datasets["berths.csv"], port_map, ctx)

    vessel_map = {}
    if "vessel_classes.csv" in raw_datasets:
        vessel_map = validate_vessel_classes(raw_datasets["vessel_classes.csv"], ctx)

    route_map = {}
    if "routes.csv" in raw_datasets:
        route_map = validate_routes(raw_datasets["routes.csv"], port_map, ctx)

    # Step 4: Parse and Validate Time-Series Tables
    if "freight_rates.csv" in raw_datasets:
        validate_freight_rates(raw_datasets["freight_rates.csv"], route_map, vessel_map, ctx)

    if "commodity_prices.csv" in raw_datasets:
        validate_commodity_prices(raw_datasets["commodity_prices.csv"], ctx)

    if "fuel_prices.csv" in raw_datasets:
        validate_fuel_prices(raw_datasets["fuel_prices.csv"], ctx)

    if "port_activity.csv" in raw_datasets:
        validate_port_activity(raw_datasets["port_activity.csv"], port_map, ctx)

    # Step 5: Parse and Validate Scenario Presets
    if "scenario_defaults.csv" in raw_datasets:
        validate_scenario_defaults(raw_datasets["scenario_defaults.csv"], ctx)

    # Step 6: Cross-Dataset Feasibility Coverage
    if port_map and berth_map and vessel_map and route_map:
        validate_feasibility_coverage(port_map, berth_map, vessel_map, route_map, ctx)

    # ==============================================================================
    # OUTPUT SUMMARY
    # ==============================================================================
    print("\nREFERENCE DATA VALIDATION SUMMARY")
    print("---------------------------------")
    all_files_ok = True
    for filename in CANONICAL_SCHEMAS.keys():
        file_errors = [e for e in ctx.errors if e.dataset == filename]
        cnt = ctx.row_counts.get(filename, 0)
        status = "PASS" if not file_errors else "FAIL"
        if file_errors:
            all_files_ok = False
        print(f"  [{status}]  {filename:<22} ({cnt:>8,d} rows)")

    print(f"\nTotal Reference Records Audited: {total_actual_rows:,d} / {EXPECTED_TOTAL_ROWS:,d}")

    # Cross-dataset checks
    cross_errors = [e for e in ctx.errors if e.dataset not in CANONICAL_SCHEMAS]
    print("\nCROSS-DATASET INVARIANT CHECKS")
    print("------------------------------")
    checks = [
        ("Exact Schemas & Header Ordering", not any(e.check == "schema_mismatch" for e in ctx.errors)),
        ("Row Count Expectations (259,589 total)", not any(e.check in ("row_count", "total_rows") for e in ctx.errors)),
        ("Foreign Key Referential Integrity", not any(e.check == "foreign_key" for e in ctx.errors)),
        ("Natural Grain Uniqueness", not any(e.check in ("primary_key", "grain_uniqueness") for e in ctx.errors)),
        ("Date Window & Continuity (731 dates)", not any(e.check in ("date_range", "date_continuity") for e in ctx.errors)),
        ("Physical Constraints (Draft/DWT/LOA)", not any(e.check in ("physical_bounds", "draft_hierarchy", "capacity_invariant") for e in ctx.errors)),
        ("Provenance Standards (SYNTHETIC)", not any(e.check == "provenance" for e in ctx.errors)),
        ("Freight Economic Hierarchy ($/MT & $/day)", not any("freight_hierarchy" in e.check for e in ctx.errors)),
        ("Feasibility Coverage (Feasible + Rejection)", not any("coverage" in e.check for e in ctx.errors)),
    ]

    for label, passed in checks:
        status_str = "PASS" if passed else "FAIL"
        print(f"  [{status_str}] {label}")

    print("=" * 70)
    if ctx.is_valid:
        print("  RESULT: PASS")
        print("  Validation gate cleared. Datasets are ready for database seeding.")
        print("=" * 70)
        return 0
    else:
        print(f"  RESULT: FAIL — {len(ctx.errors)} validation errors discovered.")
        print("=" * 70)

        # Group errors by dataset
        grouped: Dict[str, List[ValidationError]] = defaultdict(list)
        for err in ctx.errors:
            grouped[err.dataset].append(err)

        for ds, err_list in grouped.items():
            print(f"\n[{ds}] ({len(err_list)} errors):")
            for err in err_list[:8]:  # Limit output per dataset
                print(f"  - [{err.check}] {err.message}")
            if len(err_list) > 8:
                print(f"  ... and {len(err_list) - 8} more errors truncated.")

        return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate DockTech V1 reference CSV datasets against DATA_DICTIONARY.md."
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/reference",
        help="Path to reference datasets directory (default: data/reference)",
    )
    args = parser.parse_args()

    # Resolve relative to repo root (parent of scripts/)
    repo_root = Path(__file__).resolve().parent.parent
    data_dir = repo_root / args.data_dir

    exit_code = validate_all_reference_data(data_dir)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
