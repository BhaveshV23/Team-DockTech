from datetime import datetime, timezone
import os
import sys
from uuid import uuid4

from fastapi.testclient import TestClient

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.core import dependencies
from app.core.config import settings
from tests.auth_test_utils import TEST_SUPABASE_URL, supabase_test_token
from app.main import app
import app.api.v1.auth as auth_api


TEST_SECRET = "docktech-profile-provision-test-secret-32-bytes"
client = TestClient(app)


class InMemoryProfiles:
    def __init__(self):
        self.profiles = {}
        self.create_calls = 0

    def get_by_auth_user_id(self, auth_user_id):
        return self.profiles.get(str(auth_user_id))

    def provision_if_missing(self, auth_user_id, *, email, display_name, role):
        auth_id = str(auth_user_id)
        existing = self.profiles.get(auth_id)
        if existing:
            return existing
        self.create_calls += 1
        now = datetime.now(timezone.utc).isoformat()
        profile = {
            "user_id": str(uuid4()),
            "auth_user_id": auth_id,
            "email": email,
            "display_name": display_name,
            "role": role,
            "created_at": now,
            "updated_at": now,
        }
        self.profiles[auth_id] = profile
        return profile


def _token(auth_user_id, email="new.user@example.test", *, metadata=None):
    claims = {"sub": str(auth_user_id), "email": email}
    if metadata is not None:
        claims["user_metadata"] = metadata
    return supabase_test_token(TEST_SECRET, claims)


def _setup(monkeypatch, repository):
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", TEST_SECRET)
    monkeypatch.setattr(settings, "SUPABASE_URL", TEST_SUPABASE_URL)
    service = auth_api.ProfileProvisioningService(repository=repository)
    app.dependency_overrides[auth_api.get_profile_provisioning_service] = lambda: service
    monkeypatch.setattr(dependencies, "user_repository", repository)
    return service


def _assert_existing_profile(response_profile, existing):
    for field in ("user_id", "auth_user_id", "display_name", "email", "role"):
        assert response_profile[field] == existing[field]
    for field in ("created_at", "updated_at"):
        returned = datetime.fromisoformat(response_profile[field].replace("Z", "+00:00"))
        original = datetime.fromisoformat(existing[field].replace("Z", "+00:00"))
        assert returned == original


def test_new_authenticated_user_is_provisioned_with_verified_identity_and_server_role(monkeypatch):
    repository = InMemoryProfiles()
    _setup(monkeypatch, repository)
    auth_id = uuid4()
    supplied_user_id = uuid4()
    token = _token(auth_id, metadata={"display_name": "New Planner", "role": "ADMINISTRATOR"})
    try:
        response = client.post(
            "/api/v1/auth/provision",
            headers={"Authorization": f"Bearer {token}"},
            json={"role": "ADMINISTRATOR", "user_id": str(supplied_user_id), "auth_user_id": str(uuid4())},
        )
        assert response.status_code == 200
        profile = response.json()
        assert profile["auth_user_id"] == str(auth_id)
        assert profile["user_id"] != str(supplied_user_id)
        assert profile["display_name"] == "New Planner"
        assert profile["email"] == "new.user@example.test"
        assert profile["role"] == "VIEWER"
        assert repository.create_calls == 1
    finally:
        app.dependency_overrides.clear()


def test_existing_profile_is_reused_without_overwriting_role_or_metadata(monkeypatch):
    repository = InMemoryProfiles()
    auth_id = uuid4()
    existing = {
        "user_id": str(uuid4()), "auth_user_id": str(auth_id),
        "display_name": "Existing Planner", "email": "existing@example.test",
        "role": "PLANNER", "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    repository.profiles[str(auth_id)] = existing
    _setup(monkeypatch, repository)
    try:
        response = client.post(
            "/api/v1/auth/provision",
            headers={"Authorization": f"Bearer {_token(auth_id)}"},
        )
        assert response.status_code == 200
        _assert_existing_profile(response.json(), existing)
        assert repository.create_calls == 0
    finally:
        app.dependency_overrides.clear()


def test_repeated_provisioning_creates_only_one_profile(monkeypatch):
    repository = InMemoryProfiles()
    _setup(monkeypatch, repository)
    auth_id = uuid4()
    headers = {"Authorization": f"Bearer {_token(auth_id)}"}
    try:
        first = client.post("/api/v1/auth/provision", headers=headers)
        second = client.post("/api/v1/auth/provision", headers=headers)
        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()
        assert repository.create_calls == 1
        assert len(repository.profiles) == 1
    finally:
        app.dependency_overrides.clear()


def test_auth_me_succeeds_after_profile_provisioning(monkeypatch):
    repository = InMemoryProfiles()
    _setup(monkeypatch, repository)
    auth_id = uuid4()
    headers = {"Authorization": f"Bearer {_token(auth_id)}"}
    try:
        provisioned = client.post("/api/v1/auth/provision", headers=headers)
        profile = client.get("/api/v1/auth/me", headers=headers)
        assert provisioned.status_code == profile.status_code == 200
        assert profile.json() == provisioned.json()
    finally:
        app.dependency_overrides.clear()


def test_manually_provisioned_bhavesh_profile_continues_to_work(monkeypatch):
    repository = InMemoryProfiles()
    auth_id = uuid4()
    existing = {
        "user_id": str(uuid4()), "auth_user_id": str(auth_id),
        "display_name": "Bhavesh", "email": "bhavesh@example.test",
        "role": "MANAGER", "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    repository.profiles[str(auth_id)] = existing
    _setup(monkeypatch, repository)
    try:
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {_token(auth_id)}"},
        )
        assert response.status_code == 200
        _assert_existing_profile(response.json(), existing)
        assert repository.create_calls == 0
    finally:
        app.dependency_overrides.clear()


def test_unauthenticated_request_cannot_provision_profile(monkeypatch):
    repository = InMemoryProfiles()
    _setup(monkeypatch, repository)
    try:
        response = client.post(
            "/api/v1/auth/provision",
            json={
                "auth_user_id": str(uuid4()), "user_id": str(uuid4()),
                "email": "attacker@example.test", "role": "ADMINISTRATOR",
            },
        )
        assert response.status_code == 401
        assert repository.create_calls == 0
        assert repository.profiles == {}
    finally:
        app.dependency_overrides.clear()
