from datetime import datetime, timedelta, timezone
import os
import sys
from uuid import uuid4

import jwt
import pytest

BACKEND_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if BACKEND_PATH not in sys.path:
    sys.path.insert(0, BACKEND_PATH)

from app.core.config import settings
from app.integrations.supabase_auth import SupabaseAuthError, SupabaseAuthVerifier
from tests.auth_test_utils import TEST_SUPABASE_ISSUER, TEST_SUPABASE_URL


TEST_SECRET = "docktech-test-jwt-secret-key-32-bytes-long"


@pytest.fixture
def verifier(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", TEST_SECRET)
    monkeypatch.setattr(settings, "SUPABASE_URL", TEST_SUPABASE_URL)
    return SupabaseAuthVerifier()


def make_token(claims=None, *, secret=TEST_SECRET):
    payload = {
        "sub": str(uuid4()),
        "iss": TEST_SUPABASE_ISSUER,
        "aud": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    if claims is not None:
        payload.update(claims)
        payload = {key: value for key, value in payload.items() if value is not None}
    return jwt.encode(payload, secret, algorithm="HS256")


def test_accepts_valid_supabase_access_token(verifier):
    result = verifier.verify_token(make_token())
    assert result["auth_user_id"]
    assert result["claims"]["iss"] == TEST_SUPABASE_ISSUER
    assert result["claims"]["aud"] == "authenticated"


@pytest.mark.parametrize(
    "claims",
    [
        {"iss": "https://attacker.example/auth/v1"},
        {"aud": "service_role"},
        {"iss": None},
        {"aud": None},
        {"sub": None},
    ],
)
def test_rejects_invalid_or_missing_required_claims(verifier, claims):
    with pytest.raises(SupabaseAuthError):
        verifier.verify_token(make_token(claims))


def test_rejects_expired_token(verifier):
    expired = datetime.now(timezone.utc) - timedelta(minutes=1)
    with pytest.raises(SupabaseAuthError, match="expired"):
        verifier.verify_token(make_token({"exp": expired}))


def test_rejects_invalid_signature(verifier):
    with pytest.raises(SupabaseAuthError, match="Invalid authorization token"):
        verifier.verify_token(make_token(secret="wrong-test-secret"))


def test_fails_closed_when_issuer_cannot_be_derived(monkeypatch, verifier):
    monkeypatch.setattr(settings, "SUPABASE_URL", "")
    with pytest.raises(SupabaseAuthError, match="missing Supabase URL"):
        verifier.verify_token(make_token())


def test_client_supplied_identity_claim_cannot_override_signed_subject(verifier):
    signed_subject = str(uuid4())
    token = make_token({"sub": signed_subject, "auth_user_id": str(uuid4())})
    result = verifier.verify_token(token)
    assert result["auth_user_id"] == signed_subject
