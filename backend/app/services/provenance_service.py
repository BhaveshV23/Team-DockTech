"""Expose provenance already recorded in the reference CSV seed artifacts."""

import csv
import json
from functools import lru_cache
from pathlib import Path
from typing import Any


REFERENCE_DIR = Path(__file__).resolve().parents[3] / "data" / "reference"


@lru_cache(maxsize=1)
def get_reference_provenance() -> dict[str, Any]:
    """Read the manifest and summarize exact source/type/date/unit CSV fields."""
    manifest_path = REFERENCE_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    datasets = []

    for filename in manifest["checksums_sha256"]:
        dataset_path = REFERENCE_DIR / filename
        with dataset_path.open(encoding="utf-8", newline="") as source_file:
            reader = csv.DictReader(source_file)
            fields = set(reader.fieldnames or [])
            if not {"source", "data_type"}.issubset(fields):
                raise ValueError(f"Provenance columns are missing from {filename}")

            provenance_pairs: set[tuple[str, str]] = set()
            observations: list[str] = []
            units: set[str] = set()
            for row in reader:
                source = row.get("source", "").strip()
                data_type = row.get("data_type", "").strip()
                if not source or not data_type:
                    raise ValueError(f"A source or data_type value is blank in {filename}")
                provenance_pairs.add((source, data_type))
                if row.get("observation_date"):
                    observations.append(row["observation_date"].strip())
                unit = row.get("freight_unit") or row.get("unit")
                if unit and unit.strip():
                    units.add(unit.strip())

        datasets.append({
            "dataset": Path(filename).stem,
            "provenance": [
                {"source": source, "data_type": data_type}
                for source, data_type in sorted(provenance_pairs)
            ],
            "date_start": min(observations) if observations else None,
            "date_end": max(observations) if observations else None,
            "units": sorted(units),
        })

    return {
        "generator_name": manifest["generator_name"],
        "generator_version": manifest["generator_version"],
        "generation_timestamp": manifest["generation_timestamp"],
        "history_start_date": manifest["history_start_date"],
        "history_end_date": manifest["history_end_date"],
        "datasets": datasets,
    }
