import csv
import os
from typing import Any, Dict, List
import httpx
from app.core.config import settings


class ReferenceRepository:
    """Repository for querying canonical reference datasets (ports, vessel_classes, routes).

    Uses Supabase PostgreSQL REST API as authoritative production source with local CSV fallback.
    """

    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self.base_csv_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "reference")
        )

    def _read_csv(self, filename: str) -> List[Dict[str, Any]]:
        csv_path = os.path.join(self.base_csv_dir, filename)
        results = []
        if os.path.exists(csv_path):
            with open(csv_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cleaned = {}
                    for k, v in row.items():
                        if v is None:
                            cleaned[k] = ""
                        else:
                            try:
                                cleaned[k] = float(v)
                            except ValueError:
                                cleaned[k] = v
                    results.append(cleaned)
        return results

    def get_ports(self) -> List[Dict[str, Any]]:
        if self.supabase_url and self.service_role_key:
            url = f"{self.supabase_url.rstrip('/')}/rest/v1/ports"
            headers = {
                "apikey": self.service_role_key,
                "Authorization": f"Bearer {self.service_role_key}",
                "Accept": "application/json",
            }
            try:
                with httpx.Client(timeout=3.0) as client:
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 200:
                        return resp.json()
            except Exception:
                pass  # Fall back to CSV reference dataset if database is unreachable

        return self._read_csv("ports.csv")

    def get_vessels(self) -> List[Dict[str, Any]]:
        if self.supabase_url and self.service_role_key:
            url = f"{self.supabase_url.rstrip('/')}/rest/v1/vessel_classes"
            headers = {
                "apikey": self.service_role_key,
                "Authorization": f"Bearer {self.service_role_key}",
                "Accept": "application/json",
            }
            try:
                with httpx.Client(timeout=3.0) as client:
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 200:
                        return resp.json()
            except Exception:
                pass  # Fall back to CSV reference dataset if database is unreachable

        return self._read_csv("vessel_classes.csv")

    def get_routes(self) -> List[Dict[str, Any]]:
        if self.supabase_url and self.service_role_key:
            url = f"{self.supabase_url.rstrip('/')}/rest/v1/routes"
            headers = {
                "apikey": self.service_role_key,
                "Authorization": f"Bearer {self.service_role_key}",
                "Accept": "application/json",
            }
            try:
                with httpx.Client(timeout=3.0) as client:
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 200:
                        return resp.json()
            except Exception:
                pass  # Fall back to CSV reference dataset if database is unreachable

        return self._read_csv("routes.csv")


reference_repository = ReferenceRepository()
