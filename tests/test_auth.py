from datetime import datetime, timezone
import os
import sys
from uuid import uuid4

# Ensure backend directory is in sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from fastapi.testclient import TestClient
import jwt
from app.core.config import settings
from app.repositories.user_repository import user_repository
from main import app

# Set test JWT secret for signature verification testing
TEST_JWT_SECRET = "docktech-test-jwt-secret-key-32-bytes-long"
settings.SUPABASE_JWT_SECRET = TEST_JWT_SECRET

client = TestClient(app)


def test_root_endpoint():
    """Verify GET / returns health check response."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "DockTech API is running"}


def test_auth_me_missing_header():
    """Verify GET /api/v1/auth/me returns 401 when Authorization header is missing."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "Missing authorization token" in response.json()["detail"]


def test_auth_me_malformed_header():
    """Verify GET /api/v1/auth/me returns 401 when Authorization header is malformed."""
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "InvalidHeaderFormat"}
    )
    assert response.status_code == 401
    assert "Invalid authorization header format" in response.json()["detail"]


def test_auth_me_invalid_token():
    """Verify GET /api/v1/auth/me returns 401 when Bearer token is invalid or signed with wrong secret."""
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token_xyz"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] is not None


def test_auth_me_unverified_token_rejected_when_unconfigured():
    """Verify unverified tokens are strictly rejected when auth secret is unconfigured."""
    original_secret = settings.SUPABASE_JWT_SECRET
    original_url = settings.SUPABASE_URL
    try:
        settings.SUPABASE_JWT_SECRET = ""
        settings.SUPABASE_URL = ""
        token = jwt.encode({"sub": str(uuid4())}, "dummy", algorithm="HS256")
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401
        assert "Authentication system unconfigured" in response.json()["detail"]
    finally:
        settings.SUPABASE_JWT_SECRET = original_secret
        settings.SUPABASE_URL = original_url


def test_auth_me_user_profile_not_found():
    """Verify GET /api/v1/auth/me returns 404 when authenticated user has no user_profiles record."""
    auth_user_id = str(uuid4())

    token = jwt.encode(
        {"sub": auth_user_id, "email": "unknown@docktech.com"},
        TEST_JWT_SECRET,
        algorithm="HS256",
    )

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404
    assert "User profile not found" in response.json()["detail"]


def test_auth_me_successful():
    """Verify GET /api/v1/auth/me returns 200 OK and UserProfile payload when token is valid & profile exists."""
    user_id = uuid4()
    auth_user_id = uuid4()
    now = datetime.now(timezone.utc).isoformat()

    mock_profile = {
        "user_id": str(user_id),
        "auth_user_id": str(auth_user_id),
        "display_name": "Test Manager",
        "email": "manager@docktech.com",
        "role": "MANAGER",
        "created_at": now,
        "updated_at": now,
    }

    user_repository.add_mock_profile(mock_profile)

    try:
        token = jwt.encode(
            {"sub": str(auth_user_id), "email": "manager@docktech.com"},
            TEST_JWT_SECRET,
            algorithm="HS256",
        )

        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(user_id)
        assert data["auth_user_id"] == str(auth_user_id)
        assert data["display_name"] == "Test Manager"
        assert data["email"] == "manager@docktech.com"
        assert data["role"] == "MANAGER"
    finally:
        user_repository.clear_mock_profiles()


def test_cors_preflight_request():
    """Verify CORS preflight OPTIONS request returns correct headers for configured origin."""
    response = client.options(
        "/api/v1/auth/me",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "Authorization" in response.headers.get("access-control-allow-headers", "")
