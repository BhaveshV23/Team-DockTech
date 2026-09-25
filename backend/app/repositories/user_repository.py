from typing import Any, Dict, Optional
from uuid import UUID
import httpx
from app.core.config import settings


class UserRepository:
    """Repository for accessing user_profiles from Supabase PostgreSQL or local test storage."""

    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self._mock_profiles: Dict[str, Dict[str, Any]] = {}

    def add_mock_profile(self, profile: Dict[str, Any]) -> None:
        """Register a mock profile (used for testing or mock environments)."""
        auth_user_id = str(profile["auth_user_id"])
        self._mock_profiles[auth_user_id] = profile

    def clear_mock_profiles(self) -> None:
        """Clear all registered mock profiles."""
        self._mock_profiles.clear()

    def get_by_auth_user_id(self, auth_user_id: UUID) -> Optional[Dict[str, Any]]:
        auth_str = str(auth_user_id)

        # 1. Check in-memory mock profiles first
        if auth_str in self._mock_profiles:
            return self._mock_profiles[auth_str]

        # 2. Query Supabase REST API if configured
        if self.supabase_url and self.service_role_key:
            url = f"{self.supabase_url.rstrip('/')}/rest/v1/user_profiles"
            headers = {
                "apikey": self.service_role_key,
                "Authorization": f"Bearer {self.service_role_key}",
                "Accept": "application/json",
            }
            params = {"auth_user_id": f"eq.{auth_str}", "select": "*"}
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


user_repository = UserRepository()
