from datetime import datetime, timezone
from uuid import UUID, uuid4

from backend.app.repositories.user_repository import UserRepository


class _Response:
    def __init__(self, status_code, records):
        self.status_code = status_code
        self.records = records

    def json(self):
        return self.records


class _PostgrestClient:
    stored_profiles = {}
    requests = []

    def __init__(self, timeout):
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def get(self, _url, headers, params):
        auth_id = params["auth_user_id"][3:]
        profile = self.stored_profiles.get(auth_id)
        return _Response(200, [profile] if profile else [])

    def post(self, _url, *, headers, params, json):
        self.requests.append((headers, params, json))
        auth_id = json["auth_user_id"]
        if auth_id in self.stored_profiles:
            return _Response(201, [])
        profile = {
            **json,
            "user_id": str(uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.stored_profiles[auth_id] = profile
        return _Response(201, [profile])


def test_profile_repository_is_idempotent_and_uses_auth_identity(monkeypatch):
    _PostgrestClient.stored_profiles = {}
    _PostgrestClient.requests = []
    monkeypatch.setattr(
        "backend.app.repositories.user_repository.httpx.Client", _PostgrestClient,
    )
    repository = UserRepository()
    repository.supabase_url = "https://supabase.example.test"
    repository.service_role_key = "backend-only-test-key"
    auth_user_id = uuid4()

    first = repository.provision_if_missing(
        auth_user_id, email="new@example.test", display_name="New User", role="VIEWER",
    )
    second = repository.provision_if_missing(
        auth_user_id, email="changed@example.test", display_name="Changed Name", role="ADMINISTRATOR",
    )

    assert first == second
    assert first["auth_user_id"] == str(auth_user_id)
    assert first["role"] == "VIEWER"
    assert len(_PostgrestClient.requests) == 1
    _, params, payload = _PostgrestClient.requests[0]
    assert params == {"on_conflict": "auth_user_id"}
    assert payload["auth_user_id"] == str(auth_user_id)
    assert "user_id" not in payload


class _RoleUpdatePostgrestClient:
    profile = None
    get_params = []
    patch_requests = []

    def __init__(self, timeout):
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def get(self, _url, *, headers, params):
        self.get_params.append(params)
        matches = self.profile and params.get("user_id") == f"eq.{self.profile['user_id']}"
        return _Response(200, [self.profile] if matches else [])

    def patch(self, _url, *, headers, params, json):
        self.patch_requests.append((params, json))
        matches = self.profile and params.get("user_id") == f"eq.{self.profile['user_id']}"
        if not matches:
            return _Response(200, [])
        self.profile.update(json)
        return _Response(200, [self.profile])


class _ProfileListingPostgrestClient:
    records = []
    requests = []
    status_code = 200

    def __init__(self, timeout):
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def get(self, _url, *, headers, params):
        self.requests.append((headers, params))
        return _Response(self.status_code, self.records)


def test_profile_repository_lists_only_discovery_fields_from_storage(monkeypatch):
    profile = {
        "user_id": str(uuid4()),
        "auth_user_id": str(uuid4()),
        "display_name": "Target User",
        "email": "target@example.test",
        "role": "VIEWER",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _ProfileListingPostgrestClient.records = [profile]
    _ProfileListingPostgrestClient.requests = []
    _ProfileListingPostgrestClient.status_code = 200
    monkeypatch.setattr(
        "backend.app.repositories.user_repository.httpx.Client",
        _ProfileListingPostgrestClient,
    )
    repository = UserRepository()
    repository.supabase_url = "https://supabase.example.test"
    repository.service_role_key = "backend-only-test-key"

    result = repository.list_profiles()

    assert result == [{
        "user_id": profile["user_id"],
        "display_name": profile["display_name"],
        "email": profile["email"],
        "role": profile["role"],
    }]
    _, params = _ProfileListingPostgrestClient.requests[0]
    assert params == {"select": "user_id,display_name,email,role"}


def test_profile_repository_list_storage_failure_raises_storage_error(monkeypatch):
    import pytest

    from backend.app.repositories.user_repository import UserProfileStorageError

    _ProfileListingPostgrestClient.records = []
    _ProfileListingPostgrestClient.requests = []
    _ProfileListingPostgrestClient.status_code = 500
    monkeypatch.setattr(
        "backend.app.repositories.user_repository.httpx.Client",
        _ProfileListingPostgrestClient,
    )
    repository = UserRepository()
    repository.supabase_url = "https://supabase.example.test"
    repository.service_role_key = "backend-only-test-key"

    with pytest.raises(UserProfileStorageError):
        repository.list_profiles()


def test_role_update_repository_selects_by_profile_id_and_writes_only_role_and_updated_at(monkeypatch):
    target = {
        "user_id": str(uuid4()),
        "auth_user_id": str(uuid4()),
        "email": "target@example.test",
        "display_name": "Target User",
        "role": "VIEWER",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    original_identity = {
        key: target[key]
        for key in ("user_id", "auth_user_id", "email", "display_name", "created_at")
    }
    _RoleUpdatePostgrestClient.profile = dict(target)
    _RoleUpdatePostgrestClient.get_params = []
    _RoleUpdatePostgrestClient.patch_requests = []
    monkeypatch.setattr(
        "backend.app.repositories.user_repository.httpx.Client",
        _RoleUpdatePostgrestClient,
    )
    repository = UserRepository()
    repository.supabase_url = "https://supabase.example.test"
    repository.service_role_key = "backend-only-test-key"

    assert repository.get_by_user_id(UUID(target["user_id"]))["user_id"] == target["user_id"]
    updated = repository.update_role_by_user_id(UUID(target["user_id"]), "MANAGER")

    assert _RoleUpdatePostgrestClient.get_params == [
        {"user_id": f"eq.{target['user_id']}", "select": "*"},
    ]
    params, payload = _RoleUpdatePostgrestClient.patch_requests[0]
    assert params == {"user_id": f"eq.{target['user_id']}", "select": "*"}
    assert set(payload) == {"role", "updated_at"}
    assert payload["role"] == "MANAGER"
    assert updated["role"] == "MANAGER"
    assert {key: updated[key] for key in original_identity} == original_identity
