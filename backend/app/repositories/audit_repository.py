from typing import Any, Dict, List, Optional
from uuid import UUID
import httpx
from app.core.config import settings


class AuditRepository:
    """Repository for persisting and querying audit_logs in Supabase or local mock storage."""

    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self._mock_audit_logs: Dict[str, Dict[str, Any]] = {}

    def clear_mock_logs(self) -> None:
        """Clear mock audit logs (used for test isolation)."""
        self._mock_audit_logs.clear()

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        audit_log_id = str(data["audit_log_id"])

        # 1. Save in mock storage
        self._mock_audit_logs[audit_log_id] = data

        # 2. Persist to Supabase REST API if configured
        if self.supabase_url and self.service_role_key:
            url = f"{self.supabase_url.rstrip('/')}/rest/v1/audit_logs"
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

    def get_by_id(self, audit_log_id: UUID) -> Optional[Dict[str, Any]]:
        log_id_str = str(audit_log_id)

        # 1. Check mock storage first
        if log_id_str in self._mock_audit_logs:
            return self._mock_audit_logs[log_id_str]

        # 2. Query Supabase REST API if configured
        if self.supabase_url and self.service_role_key:
            url = f"{self.supabase_url.rstrip('/')}/rest/v1/audit_logs"
            headers = {
                "apikey": self.service_role_key,
                "Authorization": f"Bearer {self.service_role_key}",
                "Accept": "application/json",
            }
            params = {"audit_log_id": f"eq.{log_id_str}", "select": "*"}
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
        for item in self._mock_audit_logs.values():
            if str(item.get("user_id")) == user_id_str:
                results.append(item)

        # 2. Query Supabase REST API if configured
        if self.supabase_url and self.service_role_key:
            url = f"{self.supabase_url.rstrip('/')}/rest/v1/audit_logs"
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
                        existing_ids = {r["audit_log_id"] for r in results}
                        for rec in db_records:
                            if rec["audit_log_id"] not in existing_ids:
                                results.append(rec)
            except Exception:
                pass

        return results


audit_repository = AuditRepository()
