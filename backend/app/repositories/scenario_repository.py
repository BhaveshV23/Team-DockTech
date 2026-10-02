"""Supabase/PostgreSQL repository for canonical scenario records."""

import csv
from pathlib import Path
from typing import Any, Dict, List

import httpx

from backend.app.core.config import settings
from backend.app.domain.constants import CongestionLevel, ScenarioType
from backend.app.domain.entities import ScenarioDefault, ScenarioResult


class ScenarioStorageUnavailable(Exception):
    """Scenario storage or its required configuration is unavailable."""


class ScenarioPersistenceError(ScenarioStorageUnavailable):
    """The database did not confirm scenario persistence."""


class ScenarioRepository:
    """Access canonical defaults and persist results in Supabase PostgreSQL."""

    def __init__(self, db_client: Any = None, reference_data_dir: Path | None = None):
        self.db_client = db_client
        self.use_supabase_reference_data = db_client is None and reference_data_dir is None
        self.supabase_url = settings.SUPABASE_URL
        self.service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self.reference_data_dir = reference_data_dir or (
            Path(__file__).resolve().parent.parent.parent.parent / "data" / "reference"
        )

    def get_scenario_defaults(self) -> List[ScenarioDefault]:
        if self.use_supabase_reference_data:
            from backend.app.repositories.reference_repository import reference_repository
            try:
                rows = reference_repository.get_rows("scenario_defaults", {"order": "scenario_id.asc"})
                return [self._default_from_row(row) for row in rows]
            except Exception as exc:
                raise ScenarioStorageUnavailable("Canonical scenario defaults are unavailable") from exc
        if self.db_client is not None:
            try:
                response = self.db_client.table("scenario_defaults").select("*").execute()
                if not response.data:
                    raise ScenarioStorageUnavailable(
                        "Canonical scenario defaults are unavailable"
                    )
                return [self._default_from_row(row) for row in response.data]
            except ScenarioStorageUnavailable:
                raise
            except Exception as exc:
                raise ScenarioStorageUnavailable(
                    "Canonical scenario defaults are unavailable"
                ) from exc
        path = self.reference_data_dir / "scenario_defaults.csv"
        if not path.exists():
            raise ScenarioStorageUnavailable("Canonical scenario defaults are unavailable")
        try:
            with path.open(mode="r", encoding="utf-8") as stream:
                return [self._default_from_row(row) for row in csv.DictReader(stream)]
        except Exception as exc:
            raise ScenarioStorageUnavailable("Canonical scenario defaults are invalid") from exc

    @staticmethod
    def _default_from_row(row: dict[str, Any]) -> ScenarioDefault:
        return ScenarioDefault(
            scenario_id=ScenarioType(row["scenario_id"].strip()),
            scenario_name=row["scenario_name"].strip(),
            freight_change_pct=float(row["freight_change_pct"]),
            fuel_change_pct=float(row["fuel_change_pct"]),
            delay_hours=float(row["delay_hours"]),
            port_congestion_level=CongestionLevel(row["port_congestion_level"].strip()),
            description=row["description"].strip(),
        )

    def get_scenario_default_by_type(self, scenario_type: ScenarioType) -> ScenarioDefault:
        for default in self.get_scenario_defaults():
            if default.scenario_id == scenario_type:
                return default
        raise ScenarioStorageUnavailable(f"Scenario default {scenario_type.value} is unavailable")

    def save_scenario_result(self, result: ScenarioResult) -> ScenarioResult:
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
        try:
            if self.db_client is not None:
                response = self.db_client.table("scenarios").insert(record).execute()
                rows = response.data
            else:
                url, headers = self._configuration()
                headers = {
                    **headers,
                    "Content-Type": "application/json",
                    "Prefer": "return=representation",
                }
                with httpx.Client(timeout=10.0) as client:
                    response = client.post(f"{url}/rest/v1/scenarios", headers=headers, json=record)
                if response.status_code < 200 or response.status_code >= 300:
                    raise ScenarioPersistenceError(
                        f"Scenario persistence failed with status {response.status_code}"
                    )
                rows = response.json()
            if not isinstance(rows, list) or len(rows) != 1:
                raise ScenarioPersistenceError("Database did not confirm scenario persistence")
            if str(rows[0].get("scenario_instance_id")) != str(result.scenario_instance_id):
                raise ScenarioPersistenceError("Persisted scenario does not match the submitted result")
            return result
        except ScenarioStorageUnavailable:
            raise
        except Exception as exc:
            raise ScenarioPersistenceError("Scenario persistence is unavailable") from exc

    def get_scenarios_by_cargo_request(self, cargo_request_id) -> List[Dict[str, Any]]:
        """Read persisted scenario rows; the canonical table does not store the response breakdown."""
        try:
            if self.db_client is not None:
                response = (
                    self.db_client.table("scenarios")
                    .select("*")
                    .eq("cargo_request_id", str(cargo_request_id))
                    .execute()
                )
                rows = response.data
            else:
                url, headers = self._configuration()
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(
                        f"{url}/rest/v1/scenarios",
                        headers=headers,
                        params={"cargo_request_id": f"eq.{cargo_request_id}", "select": "*"},
                    )
                if response.status_code < 200 or response.status_code >= 300:
                    raise ScenarioStorageUnavailable(
                        f"Scenario query failed with status {response.status_code}"
                    )
                rows = response.json()
            if not isinstance(rows, list):
                raise ScenarioStorageUnavailable("Scenario query returned an invalid response")
            return rows
        except ScenarioStorageUnavailable:
            raise
        except Exception as exc:
            raise ScenarioStorageUnavailable("Scenario storage is unavailable") from exc

    def _configuration(self) -> tuple[str, dict[str, str]]:
        if not self.supabase_url or not self.service_role_key:
            raise ScenarioStorageUnavailable("Scenario persistence is not configured")
        return (
            self.supabase_url.rstrip("/"),
            {
                "apikey": self.service_role_key,
                "Authorization": f"Bearer {self.service_role_key}",
                "Accept": "application/json",
            },
        )
