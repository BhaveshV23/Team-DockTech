from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx

from backend.app.core.config import settings


class ForecastPersistenceError(Exception):
    """Raised when forecast persistence is unavailable or incomplete."""


class ForecastRepository:
    """Repository for authoritative Supabase forecast run and point records."""

    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY

    def _configuration(self, table: str) -> tuple[str, Dict[str, str]]:
        if not self.supabase_url or not self.service_role_key:
            raise ForecastPersistenceError("Forecast persistence is not configured")
        return (
            f"{self.supabase_url.rstrip('/')}/rest/v1/{table}",
            {
                "apikey": self.service_role_key,
                "Authorization": f"Bearer {self.service_role_key}",
                "Accept": "application/json",
            },
        )

    @staticmethod
    def _check_response(response: httpx.Response) -> None:
        if response.status_code < 200 or response.status_code >= 300:
            raise ForecastPersistenceError(
                f"Forecast persistence failed with status {response.status_code}"
            )

    def _insert(self, table: str, records: Any) -> List[Dict[str, Any]]:
        url, headers = self._configuration(table)
        headers = {
            **headers,
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, headers=headers, json=records)
            self._check_response(response)
            result = response.json()
            if not isinstance(result, list):
                raise ForecastPersistenceError(
                    f"Forecast persistence returned an invalid {table} response"
                )
            return result
        except ForecastPersistenceError:
            raise
        except Exception as exc:
            raise ForecastPersistenceError("Forecast persistence service is unavailable") from exc

    def create_forecast_run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert one run and require its persisted representation."""
        run_id = str(data["forecast_run_id"])
        try:
            records = self._insert("forecast_runs", data)
            if len(records) != 1:
                raise ForecastPersistenceError(
                    "Forecast run was not confirmed by the database"
                )
            if (
                str(records[0].get("forecast_run_id")) != run_id
                or records[0].get("freight_unit") != data.get("freight_unit")
            ):
                raise ForecastPersistenceError(
                    "Persisted forecast run does not match the submitted run"
                )
            return records[0]
        except Exception as exc:
            try:
                self._rollback_run(run_id)
            except ForecastPersistenceError as rollback_exc:
                raise ForecastPersistenceError(
                    "Forecast run persistence failed and cleanup also failed"
                ) from rollback_exc
            if isinstance(exc, ForecastPersistenceError):
                raise
            raise ForecastPersistenceError("Forecast run persistence failed") from exc

    def create_forecast_points(
        self,
        forecast_run_id: UUID,
        freight_unit: str,
        points: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Insert all points; remove the parent run if the child write is incomplete."""
        run_id = str(forecast_run_id)
        normalized_points = [
            {
                **point,
                "forecast_run_id": run_id,
                "unit": freight_unit,
            }
            for point in points
        ]
        if not normalized_points:
            self._rollback_run(run_id)
            raise ForecastPersistenceError("Forecast produced no points to persist")

        try:
            saved_points = self._insert("forecast_points", normalized_points)
            if len(saved_points) != len(normalized_points):
                raise ForecastPersistenceError(
                    "Forecast point persistence returned an incomplete result"
                )
            if any(
                str(point.get("forecast_run_id")) != run_id
                or point.get("unit") != freight_unit
                for point in saved_points
            ):
                raise ForecastPersistenceError(
                    "Persisted forecast points do not match their parent run"
                )
            return saved_points
        except Exception as exc:
            try:
                self._rollback_run(run_id)
            except ForecastPersistenceError as rollback_exc:
                raise ForecastPersistenceError(
                    "Forecast points failed and the incomplete run could not be removed"
                ) from rollback_exc
            if isinstance(exc, ForecastPersistenceError):
                raise
            raise ForecastPersistenceError("Forecast point persistence failed") from exc

    def _rollback_run(self, run_id: str) -> None:
        """Delete the run; the schema cascades any points already attached to it."""
        url, headers = self._configuration("forecast_runs")
        params = {"forecast_run_id": f"eq.{run_id}"}
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.delete(url, headers=headers, params=params)
            self._check_response(response)
        except ForecastPersistenceError:
            raise
        except Exception as exc:
            raise ForecastPersistenceError("Forecast rollback failed") from exc

    def get_forecast_run(self, forecast_run_id: UUID) -> Optional[Dict[str, Any]]:
        url, headers = self._configuration("forecast_runs")
        params = {"forecast_run_id": f"eq.{forecast_run_id}", "select": "*"}
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=headers, params=params)
            self._check_response(response)
            records = response.json()
            return records[0] if records else None
        except ForecastPersistenceError:
            raise
        except Exception as exc:
            raise ForecastPersistenceError("Forecast storage is unavailable") from exc

    def get_forecast_points(self, forecast_run_id: UUID) -> List[Dict[str, Any]]:
        url, headers = self._configuration("forecast_points")
        params = {
            "forecast_run_id": f"eq.{forecast_run_id}",
            "select": "*",
            "order": "forecast_date.asc",
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=headers, params=params)
            self._check_response(response)
            return response.json()
        except ForecastPersistenceError:
            raise
        except Exception as exc:
            raise ForecastPersistenceError("Forecast storage is unavailable") from exc


forecast_repository = ForecastRepository()
