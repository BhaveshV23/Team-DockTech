from typing import Any, Dict, List, Optional
from uuid import UUID
import httpx
from app.core.config import settings


class CargoRepository:
    """Repository for persisting and querying cargo_requests in Supabase or local mock storage."""

    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self._mock_cargo_requests: Dict[str, Dict[str, Any]] = {}

    def clear_mock_requests(self) -> None:
        """Clear mock cargo requests (used for test isolation)."""
        self._mock_cargo_requests.clear()

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        cargo_request_id = str(data["cargo_request_id"])

        # 1. Save in mock storage
        self._mock_cargo_requests[cargo_request_id] = data

        # 2. Persist to Supabase REST API if configured
        if self.supabase_url and self.service_role_key:
            url = f"{self.supabase_url.rstrip('/')}/rest/v1/cargo_requests"
            headers = {
                "apikey": self.service_role_key,
                "Authorization": f"Bearer {self.service_role_key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            }
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(url, headers=headers, json=data)
                    if resp.status_code in [200, 201] and resp.json():
                        return resp.json()[0]
            except Exception:
                pass

        return data

    def get_by_id(self, cargo_request_id: UUID) -> Optional[Dict[str, Any]]:
        req_id_str = str(cargo_request_id)

        # 1. Check mock storage first
        if req_id_str in self._mock_cargo_requests:
            return self._mock_cargo_requests[req_id_str]

        # 2. Query Supabase REST API if configured
        if self.supabase_url and self.service_role_key:
            url = f"{self.supabase_url.rstrip('/')}/rest/v1/cargo_requests"
            headers = {
                "apikey": self.service_role_key,
                "Authorization": f"Bearer {self.service_role_key}",
                "Accept": "application/json",
            }
            params = {"cargo_request_id": f"eq.{req_id_str}", "select": "*"}
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.get(url, headers=headers, params=params)
                    if resp.status_code == 200:
                        records = resp.json()
                        if records and len(records) > 0:
                            return records[0]
            except Exception:
                pass

        return None

    def get_by_user_id(self, user_id: UUID) -> List[Dict[str, Any]]:
        user_id_str = str(user_id)
        results: List[Dict[str, Any]] = []

        # 1. Filter mock storage
        for item in self._mock_cargo_requests.values():
            if str(item.get("user_id")) == user_id_str:
                results.append(item)

        # 2. Query Supabase REST API if configured
        if self.supabase_url and self.service_role_key:
            url = f"{self.supabase_url.rstrip('/')}/rest/v1/cargo_requests"
            headers = {
                "apikey": self.service_role_key,
                "Authorization": f"Bearer {self.service_role_key}",
                "Accept": "application/json",
            }
            params = {"user_id": f"eq.{user_id_str}", "select": "*"}
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.get(url, headers=headers, params=params)
                    if resp.status_code == 200:
                        db_records = resp.json()
                        existing_ids = {r["cargo_request_id"] for r in results}
                        for rec in db_records:
                            if rec["cargo_request_id"] not in existing_ids:
                                results.append(rec)
            except Exception:
                pass

        return results


cargo_repository = CargoRepository()
