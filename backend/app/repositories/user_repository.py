from typing import Any, Dict, Optional
from uuid import UUID
import httpx
from app.core.config import settings


class UserProfileProvisioningError(Exception):
    """Raised when the backend cannot safely create or retrieve a user profile."""


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

    def provision_if_missing(
        self,
        auth_user_id: UUID,
        *,
        email: str,
        display_name: str,
        role: str,
    ) -> Dict[str, Any]:
        """Insert one server-authorized profile, reusing an existing auth-linked row."""
        existing = self.get_by_auth_user_id(auth_user_id)
        if existing:
            return existing

        if not self.supabase_url or not self.service_role_key:
            raise UserProfileProvisioningError("Profile storage is unavailable")

        url = f"{self.supabase_url.rstrip('/')}/rest/v1/user_profiles"
        headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Prefer": "resolution=ignore-duplicates,return=representation",
        }
        payload = {
            "auth_user_id": str(auth_user_id),
            "display_name": display_name,
            "email": email,
            "role": role,
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    url,
                    headers=headers,
                    params={"on_conflict": "auth_user_id"},
                    json=payload,
                )
            if response.status_code not in (200, 201):
                # A concurrent request may have inserted the unique auth identity.
                if response.status_code == 409:
                    existing = self.get_by_auth_user_id(auth_user_id)
                    if existing:
                        return existing
                raise UserProfileProvisioningError("Profile storage rejected provisioning")

            records = response.json()
            if records:
                return records[0]

            # ON CONFLICT DO NOTHING returns an empty representation to the
            # losing request in a concurrent first-login race.
            existing = self.get_by_auth_user_id(auth_user_id)
            if existing:
                return existing
            raise UserProfileProvisioningError("Profile could not be retrieved after provisioning")
        except UserProfileProvisioningError:
            raise
        except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
            raise UserProfileProvisioningError("Profile storage is unavailable") from exc


user_repository = UserRepository()
