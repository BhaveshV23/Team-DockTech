from datetime import datetime, timezone
import os
import sys
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.core import dependencies
from app.core.config import settings
from tests.auth_test_utils import TEST_SUPABASE_URL, supabase_test_token
from app.main import app
import app.api.v1.auth as auth_api


TEST_SECRET = "docktech-user-discovery-test-secret-32-bytes"
client = TestClient(app)


class InMemoryProfiles:
    def __init__(self):
        self.profiles = {}

    def get_by_auth_user_id(self, auth_user_id):
        return self.profiles.get(str(auth_user_id))

    def list_profiles(self):
        return list(self.profiles.values())


def _profile(role):
    now = datetime.now(timezone.utc).isoformat()
    return {
        "user_id": str(uuid4()),
        "auth_user_id": str(uuid4()),
        "display_name": f"{role.title()} User",
        "email": f"{uuid4()}@example.test",
        "role": role,
        "created_at": now,
        "updated_at": now,
    }


def _token(profile):
    return supabase_test_token(
        TEST_SECRET,
        {"sub": profile["auth_user_id"], "email": profile["email"]},
    )


def _setup(monkeypatch, repository):
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", TEST_SECRET)
    monkeypatch.setattr(settings, "SUPABASE_URL", TEST_SUPABASE_URL)
    service = auth_api.ProfileProvisioningService(repository=repository)
    app.dependency_overrides[auth_api.get_profile_provisioning_service] = lambda: service
    monkeypatch.setattr(dependencies, "user_repository", repository)


def test_administrator_can_list_user_profile_summaries_without_auth_identity(monkeypatch):
    repository = InMemoryProfiles()
    admin = _profile("ADMINISTRATOR")
    target = _profile("VIEWER")
    repository.profiles[admin["auth_user_id"]] = admin
    repository.profiles[target["auth_user_id"]] = target
    _setup(monkeypatch, repository)
    try:
        response = client.get(
            "/api/v1/auth/users",
            headers={"Authorization": f"Bearer {_token(admin)}"},
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert len(result) == 2
        assert all(set(profile) == {"user_id", "display_name", "email", "role"} for profile in result)
        assert all("auth_user_id" not in profile for profile in result)
        assert any(profile["user_id"] == target["user_id"] for profile in result)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("role", ["VIEWER", "PLANNER", "MANAGER"])
def test_non_administrator_cannot_list_user_profiles(monkeypatch, role):
    repository = InMemoryProfiles()
    caller = _profile(role)
    repository.profiles[caller["auth_user_id"]] = caller
    _setup(monkeypatch, repository)
    try:
        response = client.get(
            "/api/v1/auth/users",
            headers={"Authorization": f"Bearer {_token(caller)}"},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_unauthenticated_user_cannot_list_user_profiles(monkeypatch):
    _setup(monkeypatch, InMemoryProfiles())
    try:
        response = client.get("/api/v1/auth/users")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_user_profile_storage_failure_returns_service_unavailable(monkeypatch):
    class FailedListingRepository(InMemoryProfiles):
        def list_profiles(self):
            from backend.app.repositories.user_repository import UserProfileStorageError
            raise UserProfileStorageError("storage unavailable")

    repository = FailedListingRepository()
    admin = _profile("ADMINISTRATOR")
    repository.profiles[admin["auth_user_id"]] = admin
    _setup(monkeypatch, repository)
    try:
        response = client.get(
            "/api/v1/auth/users",
            headers={"Authorization": f"Bearer {_token(admin)}"},
        )
        assert response.status_code == 503
        assert response.json()["detail"] == "Application profile storage is unavailable"
    finally:
        app.dependency_overrides.clear()
