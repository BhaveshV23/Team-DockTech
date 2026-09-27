from typing import Any, Dict, List, Optional
from uuid import UUID
import httpx
from ..core.config import settings


class CargoPersistenceError(Exception):
    """Raised when the authoritative cargo_requests store is unavailable."""


class CargoRepository:
    """Repository for persisting and querying cargo_requests in Supabase PostgreSQL."""

    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY

    def _configuration(self) -> tuple[str, Dict[str, str]]:
        if not self.supabase_url or not self.service_role_key:
            raise CargoPersistenceError("Cargo persistence is not configured")
        return (
            f"{self.supabase_url.rstrip('/')}/rest/v1/cargo_requests",
            {
                "apikey": self.service_role_key,
                "Authorization": f"Bearer {self.service_role_key}",
                "Accept": "application/json",
            },
        )

    @staticmethod
    def _raise_for_database_error(response: httpx.Response) -> None:
        if response.status_code < 200 or response.status_code >= 300:
            raise CargoPersistenceError(
                f"Cargo persistence request failed with status {response.status_code}"
            )

    @staticmethod
    def _raise_for_transport_error(exc: Exception) -> None:
        raise CargoPersistenceError("Cargo persistence service is unavailable") from exc

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        url, headers = self._configuration()
        headers = {**headers, "Content-Type": "application/json", "Prefer": "return=representation"}
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, headers=headers, json=data)
            self._raise_for_database_error(response)
            records = response.json()
            if not records or not isinstance(records, list):
                raise CargoPersistenceError("Cargo persistence returned no saved record")
            return records[0]
        except CargoPersistenceError:
            raise
        except Exception as exc:
            self._raise_for_transport_error(exc)

    def get_by_id(self, cargo_request_id: UUID) -> Optional[Dict[str, Any]]:
        url, headers = self._configuration()
        params = {"cargo_request_id": f"eq.{cargo_request_id}", "select": "*"}
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=headers, params=params)
            self._raise_for_database_error(response)
            records = response.json()
            return records[0] if records else None
        except CargoPersistenceError:
            raise
        except Exception as exc:
            self._raise_for_transport_error(exc)

    def get_by_user_id(self, user_id: UUID) -> List[Dict[str, Any]]:
        url, headers = self._configuration()
        params = {"user_id": f"eq.{user_id}", "select": "*"}
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=headers, params=params)
            self._raise_for_database_error(response)
            return response.json()
        except CargoPersistenceError:
            raise
        except Exception as exc:
            self._raise_for_transport_error(exc)


cargo_repository = CargoRepository()
