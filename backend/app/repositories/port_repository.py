import csv
import os
from typing import Set
import httpx
from app.core.config import settings


class PortRepository:
    """Repository for validating port IDs against CSV reference data or Supabase storage."""

    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self._cached_ports: Set[str] = set()
        self._load_ports_from_csv()

    def _load_ports_from_csv(self) -> None:
        """Load static reference ports from data/reference/ports.csv."""
        csv_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "data", "reference", "ports.csv"
            )
        )
        if os.path.exists(csv_path):
            try:
                with open(csv_path, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        port_id = row.get("port_id")
                        if port_id:
                            self._cached_ports.add(port_id.strip().upper())
            except Exception:
                pass

    def is_valid_port(self, port_id: str) -> bool:
        if not port_id or not port_id.strip():
            return False

        normalized = port_id.strip().upper()

        # 1. Check local reference cache
        if normalized in self._cached_ports:
            return True

        # 2. Query Supabase REST API if configured
        if self.supabase_url and self.service_role_key:
            url = f"{self.supabase_url.rstrip('/')}/rest/v1/ports"
            headers = {
                "apikey": self.service_role_key,
                "Authorization": f"Bearer {self.service_role_key}",
                "Accept": "application/json",
            }
            params = {"port_id": f"eq.{normalized}", "select": "port_id"}
            try:
                with httpx.Client(timeout=5.0) as client:
                    resp = client.get(url, headers=headers, params=params)
                    if resp.status_code == 200 and resp.json():
                        self._cached_ports.add(normalized)
                        return True
            except Exception:
                pass

        return False


port_repository = PortRepository()
