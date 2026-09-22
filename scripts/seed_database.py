#!/usr/bin/env python3
"""
DockTech V1 — Reference Data Database Seeder
=============================================
Loads the 9 canonical synthetic reference CSV datasets into the DockTech V1
PostgreSQL/Supabase database using direct connection via psycopg2-binary.

Authoritative Source-of-Truth Documents:
  1. PRD.md
  2. DATA_DICTIONARY.md (Frozen Canonical Contract)
  3. ARCHITECTURE.md (Pipeline Lifecycle & Database Layers)
  4. SYNTHETIC_DATA_DESIGN.md (Data Generation Models)
  5. supabase/migrations/20260922000000_create_docktech_v1_schema.sql

Seeded Reference Datasets:
  1. data/reference/ports.csv             (15 rows)
  2. data/reference/vessel_classes.csv    (6 rows)
  3. data/reference/berths.csv            (32 rows)
  4. data/reference/routes.csv            (28 rows)
  5. data/reference/freight_rates.csv     (245,616 rows)
  6. data/reference/commodity_prices.csv  (1,462 rows)
  7. data/reference/fuel_prices.csv       (1,462 rows)
  8. data/reference/port_activity.csv     (10,965 rows)
  9. data/reference/scenario_defaults.csv (3 rows)
  Total Expected Records: 259,589 rows.

Guarantees:
  - Strict preflight validation via validate_reference_data.py
  - Single atomic transaction (All-or-Nothing COMMIT/ROLLBACK)
  - Idempotent upsert logic (ON CONFLICT DO UPDATE)
  - Memory-efficient batch insertion via psycopg2.extras.execute_values
  - Zero exposure or logging of credentials/DATABASE_URL
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

import psycopg2
import psycopg2.extras


# ==============================================================================
# 1. DATASET CONFIGURATION & SCHEMAS
# ==============================================================================

@dataclass(frozen=True)
class TableSeedConfig:
    table_name: str
    csv_file: str
    columns: Sequence[str]
    conflict_target: str
    expected_rows: int


REFERENCE_TABLES: Sequence[TableSeedConfig] = (
    TableSeedConfig(
        table_name="ports",
        csv_file="ports.csv",
        columns=(
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
        ),
        conflict_target="port_id",
        expected_rows=15,
    ),
    TableSeedConfig(
        table_name="vessel_classes",
        csv_file="vessel_classes.csv",
        columns=(
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
        ),
        conflict_target="vessel_class_id",
        expected_rows=6,
    ),
    TableSeedConfig(
        table_name="berths",
        csv_file="berths.csv",
        columns=(
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
        ),
        conflict_target="berth_id",
        expected_rows=32,
    ),
    TableSeedConfig(
        table_name="routes",
        csv_file="routes.csv",
        columns=(
            "route_id",
            "origin_port_id",
            "destination_port_id",
            "commodity",
            "distance_nm",
            "typical_sailing_days",
            "source",
            "data_type",
        ),
        conflict_target="route_id",
        expected_rows=28,
    ),
    TableSeedConfig(
        table_name="freight_rates",
        csv_file="freight_rates.csv",
        columns=(
            "freight_rate_id",
            "observation_date",
            "route_id",
            "vessel_class_id",
            "freight_value",
            "freight_unit",
            "currency",
            "data_type",
            "source",
        ),
        conflict_target="freight_rate_id",
        expected_rows=245616,
    ),
    TableSeedConfig(
        table_name="commodity_prices",
        csv_file="commodity_prices.csv",
        columns=(
            "commodity_price_id",
            "observation_date",
            "commodity",
            "market",
            "price_value",
            "currency",
            "unit",
            "data_type",
            "source",
        ),
        conflict_target="commodity_price_id",
        expected_rows=1462,
    ),
    TableSeedConfig(
        table_name="fuel_prices",
        csv_file="fuel_prices.csv",
        columns=(
            "fuel_price_id",
            "observation_date",
            "fuel_type",
            "price_value",
            "currency",
            "unit",
            "data_type",
            "source",
        ),
        conflict_target="fuel_price_id",
        expected_rows=1462,
    ),
    TableSeedConfig(
        table_name="port_activity",
        csv_file="port_activity.csv",
        columns=(
            "activity_id",
            "observation_date",
            "port_id",
            "vessel_arrivals",
            "average_waiting_hours",
            "average_turnaround_hours",
            "congestion_level",
            "source",
            "data_type",
        ),
        conflict_target="activity_id",
        expected_rows=10965,
    ),
    TableSeedConfig(
        table_name="scenario_defaults",
        csv_file="scenario_defaults.csv",
        columns=(
            "scenario_id",
            "scenario_name",
            "freight_change_pct",
            "fuel_change_pct",
            "delay_hours",
            "port_congestion_level",
            "description",
            "source",
            "data_type",
        ),
        conflict_target="scenario_id",
        expected_rows=3,
    ),
)

TOTAL_EXPECTED_ROWS = 259589
DEFAULT_BATCH_SIZE = 5000


# ==============================================================================
# 2. PREFLIGHT CHECKS & VALIDATION
# ==============================================================================

def check_reference_files(data_dir: Path) -> None:
    """Verifies that all 9 canonical reference CSV files exist on disk."""
    if not data_dir.is_dir():
        raise FileNotFoundError(f"Reference data directory does not exist: {data_dir}")

    missing_files: List[str] = []
    for cfg in REFERENCE_TABLES:
        csv_path = data_dir / cfg.csv_file
        if not csv_path.is_file():
            missing_files.append(cfg.csv_file)

    if missing_files:
        raise FileNotFoundError(
            f"Missing reference CSV file(s) in {data_dir}: {', '.join(missing_files)}"
        )


def run_preflight_validation(data_dir: Path, repo_root: Path) -> None:
    """Executes the canonical reference-data validation gate."""
    validator_script = repo_root / "scripts" / "validate_reference_data.py"
    if not validator_script.is_file():
        raise FileNotFoundError(f"Validator script not found: {validator_script}")

    cmd = [sys.executable, str(validator_script), "--data-dir", str(data_dir)]
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode != 0:
        error_snippet = res.stdout.strip() or res.stderr.strip()
        raise RuntimeError(
            f"Preflight reference-data validation failed (exit code {res.returncode}):\n{error_snippet}"
        )


# ==============================================================================
# 3. UPSERT QUERY GENERATION & BATCH SEEDING
# ==============================================================================

def build_upsert_sql(cfg: TableSeedConfig) -> str:
    """Constructs an idempotent INSERT ... ON CONFLICT DO UPDATE statement."""
    cols = cfg.columns
    col_names = ", ".join(cols)
    update_set = ", ".join(
        f"{c} = EXCLUDED.{c}" for c in cols if c != cfg.conflict_target
    )
    if update_set:
        conflict_clause = f"ON CONFLICT ({cfg.conflict_target}) DO UPDATE SET {update_set}"
    else:
        conflict_clause = f"ON CONFLICT ({cfg.conflict_target}) DO NOTHING"

    return f"INSERT INTO {cfg.table_name} ({col_names}) VALUES %s {conflict_clause}"


def seed_table(
    cursor: Any,
    csv_path: Path,
    cfg: TableSeedConfig,
    batch_size: int,
) -> int:
    """Reads a CSV file and batch-inserts records into PostgreSQL using execute_values."""
    sql = build_upsert_sql(cfg)
    rows_inserted = 0

    with open(csv_path, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        batch: List[Tuple[Any, ...]] = []

        for row in reader:
            record = tuple(row[col] for col in cfg.columns)
            batch.append(record)

            if len(batch) >= batch_size:
                psycopg2.extras.execute_values(cursor, sql, batch, page_size=batch_size)
                rows_inserted += len(batch)
                batch = []

        if batch:
            psycopg2.extras.execute_values(cursor, sql, batch, page_size=batch_size)
            rows_inserted += len(batch)

    return rows_inserted


# ==============================================================================
# 4. POST-SEED INTEGRITY VERIFICATION
# ==============================================================================

def verify_database_state(cursor: Any) -> Dict[str, int]:
    """Verifies table row counts and relational integrity before transaction commit."""
    counts: Dict[str, int] = {}
    for cfg in REFERENCE_TABLES:
        cursor.execute(f"SELECT COUNT(*) FROM {cfg.table_name};")  # nosec
        cnt = cursor.fetchone()[0]
        counts[cfg.table_name] = cnt

        if cnt != cfg.expected_rows:
            raise ValueError(
                f"Row count mismatch for '{cfg.table_name}': expected exactly {cfg.expected_rows}, found {cnt}"
            )

    # Referential Integrity Verification
    cursor.execute("""
        SELECT COUNT(*) FROM berths b
        WHERE NOT EXISTS (SELECT 1 FROM ports p WHERE p.port_id = b.port_id);
    """)
    if cursor.fetchone()[0] > 0:
        raise ValueError("Foreign key violation: orphaned berths found")

    cursor.execute("""
        SELECT COUNT(*) FROM routes r
        WHERE NOT EXISTS (SELECT 1 FROM ports p WHERE p.port_id = r.origin_port_id)
           OR NOT EXISTS (SELECT 1 FROM ports p WHERE p.port_id = r.destination_port_id);
    """)
    if cursor.fetchone()[0] > 0:
        raise ValueError("Foreign key violation: orphaned routes found")

    cursor.execute("""
        SELECT COUNT(*) FROM freight_rates fr
        WHERE NOT EXISTS (SELECT 1 FROM routes r WHERE r.route_id = fr.route_id)
           OR NOT EXISTS (SELECT 1 FROM vessel_classes v WHERE v.vessel_class_id = fr.vessel_class_id);
    """)
    if cursor.fetchone()[0] > 0:
        raise ValueError("Foreign key violation: orphaned freight rates found")

    cursor.execute("""
        SELECT COUNT(*) FROM port_activity pa
        WHERE NOT EXISTS (SELECT 1 FROM ports p WHERE p.port_id = pa.port_id);
    """)
    if cursor.fetchone()[0] > 0:
        raise ValueError("Foreign key violation: orphaned port activity records found")

    return counts


# ==============================================================================
# 5. CLI RUNNER & TRANSACTION ORCHESTRATION
# ==============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="DockTech V1 — Seed Reference Data into Supabase PostgreSQL"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Path to directory containing canonical reference CSV files (defaults to data/reference/)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Batch size for bulk insertion (default: {DEFAULT_BATCH_SIZE})",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    data_dir = args.data_dir if args.data_dir else repo_root / "data" / "reference"

    print("=" * 60)
    print("DockTech V1 Reference Data Database Seeder")
    print("=" * 60)

    # Step 1: Environment & Preflight Validation
    print("\n[1/4] Checking environment and reference files...")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url or not database_url.strip():
        print(
            "ERROR: DATABASE_URL is not configured.\n"
            "Set DATABASE_URL in your environment before running the seed script.",
            file=sys.stderr,
        )
        return 1

    print("DATABASE_URL: configured")

    try:
        check_reference_files(data_dir)
        print(f"Reference CSV directory verified: {data_dir}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    # Step 2: Preflight Validator Gate
    print("\n[2/4] Running preflight reference-data validation gate...")
    try:
        run_preflight_validation(data_dir, repo_root)
        print("Validation gate: PASS (All 259,589 records & invariants verified)")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    # Step 3: Database Connection & Seeding Transaction
    print("\n[3/4] Connecting to database and seeding reference tables...")
    conn = None
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = False  # Explicit atomic transaction control

        with conn.cursor() as cursor:
            for cfg in REFERENCE_TABLES:
                csv_path = data_dir / cfg.csv_file
                inserted = seed_table(cursor, csv_path, cfg, args.batch_size)
                print(f"  -> {cfg.table_name:<20} : {inserted:>7} rows processed")

            # Step 4: Verification before COMMIT
            print("\n[4/4] Verifying database state and referential integrity...")
            counts = verify_database_state(cursor)
            total_db_rows = sum(counts.values())

            if total_db_rows != TOTAL_EXPECTED_ROWS:
                raise ValueError(
                    f"Total database rows mismatch: expected {TOTAL_EXPECTED_ROWS}, found {total_db_rows}"
                )

            print(f"  Expected total : {TOTAL_EXPECTED_ROWS}")
            print(f"  Database total : {total_db_rows}")

            # Commit Transaction
            conn.commit()
            print("\n============================================================")
            print("SUCCESS: Reference data seeded and committed successfully.")
            print("============================================================")
            return 0

    except Exception as e:
        if conn is not None:
            try:
                conn.rollback()
                print("\n[ROLLBACK] Database transaction rolled back due to error.", file=sys.stderr)
            except Exception:
                pass
        print(f"\nDATABASE SEED ERROR: {e}", file=sys.stderr)
        return 1

    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
