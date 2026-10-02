from datetime import datetime, timezone
from uuid import uuid4

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
