from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx

from backend.app.core.config import settings

class ForecastRepository:
    """Repository for persisting forecast runs and forecast points."""

    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY

        # Local fallback used when Supabase is not configured.
        self._mock_forecast_runs: Dict[str, Dict[str, Any]] = {}
        self._mock_forecast_points: Dict[str, List[Dict[str, Any]]] = {}

    def create_forecast_run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create and persist one forecast_runs record."""

        forecast_run_id = str(data["forecast_run_id"])

        self._mock_forecast_runs[forecast_run_id] = data

        if self.supabase_url and self.service_role_key:
            url = f"{self.supabase_url.rstrip('/')}/rest/v1/forecast_runs"
            headers = {
                "apikey": self.service_role_key,
                "Authorization": f"Bearer {self.service_role_key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            }

            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.post(
                        url,
                        headers=headers,
                        json=data,
                    )

                    if response.status_code in (200, 201):
                        records = response.json()
                        if records:
                            return records[0]

            except Exception:
                pass

        return data

    def create_forecast_points(
        self, forecast_run_id: UUID, points: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create and persist forecast_points records."""

        run_id = str(forecast_run_id)

        normalized_points = []

        for point in points:
            record = {
                **point,
                "forecast_run_id": run_id,
            }
            normalized_points.append(record)

        self._mock_forecast_points[run_id] = normalized_points

        if self.supabase_url and self.service_role_key:
            url = f"{self.supabase_url.rstrip('/')}/rest/v1/forecast_points"
            headers = {
                "apikey": self.service_role_key,
                "Authorization": f"Bearer {self.service_role_key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            }

            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.post(
                        url,
                        headers=headers,
                        json=normalized_points,
                    )

                    if response.status_code in (200, 201):
                        records = response.json()
                        if records:
                            return records

            except Exception:
                pass

        return normalized_points

    def get_forecast_run(
        self, forecast_run_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Retrieve one forecast run by ID."""

        run_id = str(forecast_run_id)

        if run_id in self._mock_forecast_runs:
            return self._mock_forecast_runs[run_id]

        if self.supabase_url and self.service_role_key:
            url = f"{self.supabase_url.rstrip('/')}/rest/v1/forecast_runs"
            headers = {
                "apikey": self.service_role_key,
                "Authorization": f"Bearer {self.service_role_key}",
                "Accept": "application/json",
            }
            params = {
                "forecast_run_id": f"eq.{run_id}",
                "select": "*",
            }

            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(
                        url,
                        headers=headers,
                        params=params,
                    )

                    if response.status_code == 200:
                        records = response.json()
                        if records:
                            return records[0]

            except Exception:
                pass

        return None

    def get_forecast_points(
        self, forecast_run_id: UUID
    ) -> List[Dict[str, Any]]:
        """Retrieve forecast points belonging to a forecast run."""

        run_id = str(forecast_run_id)

        if run_id in self._mock_forecast_points:
            return self._mock_forecast_points[run_id]

        if self.supabase_url and self.service_role_key:
            url = f"{self.supabase_url.rstrip('/')}/rest/v1/forecast_points"
            headers = {
                "apikey": self.service_role_key,
                "Authorization": f"Bearer {self.service_role_key}",
                "Accept": "application/json",
            }
            params = {
                "forecast_run_id": f"eq.{run_id}",
                "select": "*",
                "order": "forecast_date.asc",
            }

            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(
                        url,
                        headers=headers,
                        params=params,
                    )

                    if response.status_code == 200:
                        return response.json()

            except Exception:
                pass

        return []


forecast_repository = ForecastRepository()