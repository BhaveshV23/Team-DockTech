from datetime import datetime, timezone
import os
import sys
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.core import dependencies
from app.core.config import settings
from app.schemas.auth import RoleUpdateRequest, UserRole
from tests.auth_test_utils import TEST_SUPABASE_URL, supabase_test_token
from app.main import app
import app.api.v1.auth as auth_api


TEST_SECRET = "docktech-role-assignment-test-secret-32-bytes"
client = TestClient(app)


class InMemoryProfiles:
    def __init__(self):
        self.profiles = {}
        self.updates = []

    def get_by_auth_user_id(self, auth_user_id):
        return self.profiles.get(str(auth_user_id))

    def get_by_user_id(self, user_id):
        return next(
            (profile for profile in self.profiles.values()
             if profile["user_id"] == str(user_id)),
            None,
        )

    def update_role_by_user_id(self, user_id, role):
        profile = self.get_by_user_id(user_id)
        if profile is None:
            from backend.app.repositories.user_repository import UserProfileNotFoundError
            raise UserProfileNotFoundError("User profile not found")
        profile["role"] = role
        profile["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.updates.append((str(user_id), role))
        return profile


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
    return service


@pytest.mark.parametrize("target_role", [role.value for role in UserRole])
def test_administrator_can_assign_each_allowed_role_and_target_auth_me_reflects_it(
    monkeypatch, target_role,
):
    repository = InMemoryProfiles()
    caller = _profile("ADMINISTRATOR")
    target = _profile("VIEWER")
    repository.profiles[caller["auth_user_id"]] = caller
    repository.profiles[target["auth_user_id"]] = target
    _setup(monkeypatch, repository)
    original_identity = {
        field: target[field]
        for field in ("user_id", "auth_user_id", "email", "display_name", "created_at")
    }
    try:
        response = client.patch(
            f"/api/v1/auth/users/{target['user_id']}/role",
            headers={"Authorization": f"Bearer {_token(caller)}"},
            json={"role": target_role},
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["role"] == target_role
        assert result["user_id"] == original_identity["user_id"]
        assert result["auth_user_id"] == original_identity["auth_user_id"]
        assert result["email"] == original_identity["email"]
        assert result["display_name"] == original_identity["display_name"]
        assert datetime.fromisoformat(result["created_at"].replace("Z", "+00:00")) == datetime.fromisoformat(
            original_identity["created_at"]
        )
        assert target["role"] == target_role

        profile_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {_token(target)}"},
        )
        assert profile_response.status_code == 200
        assert profile_response.json()["role"] == target_role
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("caller_role", ["VIEWER", "PLANNER", "MANAGER"])
def test_non_administrator_cannot_assign_role(monkeypatch, caller_role):
    repository = InMemoryProfiles()
    caller = _profile(caller_role)
    target = _profile("VIEWER")
    repository.profiles[caller["auth_user_id"]] = caller
    repository.profiles[target["auth_user_id"]] = target
    _setup(monkeypatch, repository)
    try:
        response = client.patch(
            f"/api/v1/auth/users/{target['user_id']}/role",
            headers={"Authorization": f"Bearer {_token(caller)}"},
            json={"role": "ADMINISTRATOR"},
        )
        assert response.status_code == 403
        assert target["role"] == "VIEWER"
        assert repository.updates == []
    finally:
        app.dependency_overrides.clear()


def test_unauthenticated_role_assignment_is_rejected(monkeypatch):
    repository = InMemoryProfiles()
    target = _profile("VIEWER")
    repository.profiles[target["auth_user_id"]] = target
    _setup(monkeypatch, repository)
    try:
        response = client.patch(
            f"/api/v1/auth/users/{target['user_id']}/role",
            json={"role": "PLANNER"},
        )
        assert response.status_code == 401
        assert repository.updates == []
    finally:
        app.dependency_overrides.clear()


def test_role_assignment_rejects_missing_target_and_administrator_self_target(monkeypatch):
    repository = InMemoryProfiles()
    admin = _profile("ADMINISTRATOR")
    repository.profiles[admin["auth_user_id"]] = admin
    _setup(monkeypatch, repository)
    headers = {"Authorization": f"Bearer {_token(admin)}"}
    try:
        missing = client.patch(
            f"/api/v1/auth/users/{uuid4()}/role", headers=headers,
            json={"role": "PLANNER"},
        )
        self_target = client.patch(
            f"/api/v1/auth/users/{admin['user_id']}/role", headers=headers,
            json={"role": "VIEWER"},
        )
        assert missing.status_code == 404
        assert self_target.status_code == 403
        assert admin["role"] == "ADMINISTRATOR"
        assert repository.updates == []
    finally:
        app.dependency_overrides.clear()


def test_role_assignment_route_rejects_invalid_role(monkeypatch):
    repository = InMemoryProfiles()
    admin = _profile("ADMINISTRATOR")
    target = _profile("VIEWER")
    repository.profiles[admin["auth_user_id"]] = admin
    repository.profiles[target["auth_user_id"]] = target
    _setup(monkeypatch, repository)
    try:
        response = client.patch(
            f"/api/v1/auth/users/{target['user_id']}/role",
            headers={"Authorization": f"Bearer {_token(admin)}"},
            json={"role": "SUPERUSER"},
        )
        assert response.status_code == 422
        assert target["role"] == "VIEWER"
        assert repository.updates == []
    finally:
        app.dependency_overrides.clear()


def test_role_assignment_rejects_identity_fields_and_ignores_caller_overrides(monkeypatch):
    repository = InMemoryProfiles()
    admin = _profile("ADMINISTRATOR")
    viewer = _profile("VIEWER")
    target = _profile("PLANNER")
    for profile in (admin, viewer, target):
        repository.profiles[profile["auth_user_id"]] = profile
    _setup(monkeypatch, repository)
    try:
        extra_fields = client.patch(
            f"/api/v1/auth/users/{target['user_id']}/role",
            headers={"Authorization": f"Bearer {_token(admin)}"},
            json={
                "role": "MANAGER", "user_id": str(admin["user_id"]),
                "auth_user_id": admin["auth_user_id"], "email": admin["email"],
                "display_name": admin["display_name"],
            },
        )
        spoofed_caller = client.patch(
            f"/api/v1/auth/users/{target['user_id']}/role?caller_user_id={admin['user_id']}",
            headers={
                "Authorization": f"Bearer {_token(viewer)}",
                "X-Role": "ADMINISTRATOR",
            },
            json={"role": "ADMINISTRATOR"},
        )
        assert extra_fields.status_code == 422
        assert spoofed_caller.status_code == 403
        assert target["role"] == "PLANNER"
        assert repository.updates == []
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("role", [role.value for role in UserRole])
def test_role_update_schema_accepts_only_known_roles(role):
    assert RoleUpdateRequest.model_validate({"role": role}).role.value == role


def test_role_update_schema_rejects_invalid_role_and_extra_identity_fields():
    with pytest.raises(ValidationError):
        RoleUpdateRequest.model_validate({"role": "SUPERUSER"})
    with pytest.raises(ValidationError):
        RoleUpdateRequest.model_validate({"role": "PLANNER", "auth_user_id": str(uuid4())})
