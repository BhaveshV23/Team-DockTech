"""Scenario repository for DockTech V1.

Encapsulates data access for scenario_defaults and scenarios table in Supabase PostgreSQL.
Supports fallback loading directly from canonical data/reference/scenario_defaults.csv.
"""

import csv
from pathlib import Path
from typing import Any, List, Optional
from uuid import UUID

from backend.app.domain.constants import CongestionLevel, RiskLevel, ScenarioType
from backend.app.domain.entities import ScenarioDefault, ScenarioResult


class ScenarioRepository:
    """Repository managing scenario defaults and simulation result persistence."""

    def __init__(self, db_client: Optional[Any] = None, reference_data_dir: Optional[Path] = None):
        self.db_client = db_client
        if reference_data_dir is None:
            # Default to repository root data/reference
            self.reference_data_dir = (
                Path(__file__).resolve().parent.parent.parent.parent / "data" / "reference"
            )
        else:
            self.reference_data_dir = reference_data_dir
        self._memory_store: dict[UUID, ScenarioResult] = {}

    def get_scenario_defaults(self) -> List[ScenarioDefault]:
        """Retrieves canonical scenario default presets.
        
        Uses database table scenario_defaults if client is connected,
        otherwise falls back to canonical data/reference/scenario_defaults.csv.
        """
        if self.db_client:
            try:
                response = self.db_client.table("scenario_defaults").select("*").execute()
                if response.data:
                    return [
                        ScenarioDefault(
                            scenario_id=ScenarioType(row["scenario_id"]),
                            scenario_name=row["scenario_name"],
                            freight_change_pct=float(row["freight_change_pct"]),
                            fuel_change_pct=float(row["fuel_change_pct"]),
                            delay_hours=float(row["delay_hours"]),
                            port_congestion_level=CongestionLevel(row["port_congestion_level"]),
                            description=row["description"],
                        )
                        for row in response.data
                    ]
            except Exception:
                # Fall back to canonical CSV seed file
                pass

        csv_path = self.reference_data_dir / "scenario_defaults.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"Canonical scenario_defaults.csv not found at {csv_path}")

        defaults: List[ScenarioDefault] = []
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                defaults.append(
                    ScenarioDefault(
                        scenario_id=ScenarioType(row["scenario_id"].strip()),
                        scenario_name=row["scenario_name"].strip(),
                        freight_change_pct=float(row["freight_change_pct"]),
                        fuel_change_pct=float(row["fuel_change_pct"]),
                        delay_hours=float(row["delay_hours"]),
                        port_congestion_level=CongestionLevel(row["port_congestion_level"].strip()),
                        description=row["description"].strip(),
                    )
                )
        return defaults

    def get_scenario_default_by_type(self, scenario_type: ScenarioType) -> ScenarioDefault:
        """Finds a scenario default preset by scenario_type."""
        defaults = self.get_scenario_defaults()
        for d in defaults:
            if d.scenario_id == scenario_type:
                return d
        raise ValueError(f"Scenario default for '{scenario_type}' not found.")

    def save_scenario_result(self, result: ScenarioResult) -> ScenarioResult:
        """Persists a scenario simulation result to the scenarios table."""
        self._memory_store[result.scenario_instance_id] = result

        if self.db_client:
            record = {
                "scenario_instance_id": str(result.scenario_instance_id),
                "cargo_request_id": str(result.cargo_request_id),
                "scenario_type": result.scenario_type.value,
                "freight_change_pct": result.freight_change_pct,
                "fuel_change_pct": result.fuel_change_pct,
                "delay_hours": result.delay_hours,
                "congestion_level": result.congestion_level.value,
                "estimated_total_cost": result.estimated_total_cost,
                "risk_level": result.risk_level.value,
            }
            self.db_client.table("scenarios").insert(record).execute()

        return result

    def get_scenarios_by_cargo_request(self, cargo_request_id: UUID) -> List[ScenarioResult]:
        """Retrieves stored scenario results for a cargo request."""
        if self.db_client:
            response = (
                self.db_client.table("scenarios")
                .select("*")
                .eq("cargo_request_id", str(cargo_request_id))
                .execute()
            )
            # Reconstruct from DB or memory
            results: List[ScenarioResult] = []
            for row in response.data:
                sc_id = UUID(row["scenario_instance_id"])
                if sc_id in self._memory_store:
                    results.append(self._memory_store[sc_id])
            return results

        return [
            r for r in self._memory_store.values() if r.cargo_request_id == cargo_request_id
        ]
