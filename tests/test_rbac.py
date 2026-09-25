from datetime import datetime, timezone
import os
import sys
from uuid import uuid4

# Ensure backend directory is in sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
import jwt
from app.core.config import settings
from app.core.dependencies import require_roles
from app.repositories.user_repository import user_repository
from app.schemas.auth import UserProfileResponse, UserRole
from main import app

# Set test JWT secret
TEST_JWT_SECRET = "docktech-test-jwt-secret-key-32-bytes-long"
settings.SUPABASE_JWT_SECRET = TEST_JWT_SECRET

# Setup test router with endpoints demonstrating RBAC requirements
rbac_test_router = APIRouter(prefix="/test-rbac", tags=["Test RBAC"])


@rbac_test_router.get("/viewer-only")
def viewer_only_endpoint(
    profile: UserProfileResponse = Depends(require_roles(UserRole.VIEWER)),
):
    return {"message": "Welcome Viewer", "role": profile.role}


@rbac_test_router.get("/planner-only")
def planner_only_endpoint(
    profile: UserProfileResponse = Depends(require_roles(UserRole.PLANNER)),
):
    return {"message": "Welcome Planner", "role": profile.role}


@rbac_test_router.get("/planner-or-manager")
def planner_or_manager_endpoint(
    profile: UserProfileResponse = Depends(
        require_roles(UserRole.PLANNER, UserRole.MANAGER)
    ),
):
    return {"message": "Welcome Planner/Manager", "role": profile.role}


@rbac_test_router.get("/admin-only")
def admin_only_endpoint(
    profile: UserProfileResponse = Depends(require_roles(UserRole.ADMINISTRATOR)),
):
    return {"message": "Welcome Administrator", "role": profile.role}


# Include test routes in app for testing
app.include_router(rbac_test_router)
client = TestClient(app)


def helper_create_test_profile(role: str):
    user_id = uuid4()
    auth_user_id = uuid4()
    now = datetime.now(timezone.utc).isoformat()

    profile = {
        "user_id": str(user_id),
        "auth_user_id": str(auth_user_id),
        "display_name": f"Test {role.capitalize()}",
        "email": f"{role.lower()}@docktech.com",
        "role": role,
        "created_at": now,
        "updated_at": now,
    }
    user_repository.add_mock_profile(profile)
    token = jwt.encode(
        {"sub": str(auth_user_id), "email": profile["email"]},
        TEST_JWT_SECRET,
        algorithm="HS256",
    )
    return token, profile


def test_unauthenticated_request_returns_401():
    """Verify unauthenticated request to an RBAC-protected endpoint returns 401."""
    response = client.get("/test-rbac/planner-only")
    assert response.status_code == 401
    assert "Missing authorization token" in response.json()["detail"]


def test_viewer_allowed_for_viewer_endpoint():
    """Verify authenticated VIEWER is permitted on VIEWER-allowed endpoint."""
    token, _ = helper_create_test_profile("VIEWER")
    try:
        response = client.get(
            "/test-rbac/viewer-only", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["role"] == "VIEWER"
    finally:
        user_repository.clear_mock_profiles()


def test_viewer_rejected_for_planner_endpoint_returns_403():
    """Verify authenticated VIEWER is rejected with HTTP 403 on PLANNER-required endpoint."""
    token, _ = helper_create_test_profile("VIEWER")
    try:
        response = client.get(
            "/test-rbac/planner-only", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
        assert "Access forbidden" in response.json()["detail"]
    finally:
        user_repository.clear_mock_profiles()


def test_planner_allowed_for_planner_endpoint():
    """Verify authenticated PLANNER is permitted on PLANNER-required endpoint."""
    token, _ = helper_create_test_profile("PLANNER")
    try:
        response = client.get(
            "/test-rbac/planner-only", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["role"] == "PLANNER"
    finally:
        user_repository.clear_mock_profiles()


def test_manager_allowed_for_planner_or_manager_endpoint():
    """Verify authenticated MANAGER is permitted on PLANNER/MANAGER endpoint."""
    token, _ = helper_create_test_profile("MANAGER")
    try:
        response = client.get(
            "/test-rbac/planner-or-manager",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["role"] == "MANAGER"
    finally:
        user_repository.clear_mock_profiles()


def test_administrator_allowed_for_admin_endpoint():
    """Verify authenticated ADMINISTRATOR is permitted on ADMINISTRATOR-required endpoint."""
    token, _ = helper_create_test_profile("ADMINISTRATOR")
    try:
        response = client.get(
            "/test-rbac/admin-only", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["role"] == "ADMINISTRATOR"
    finally:
        user_repository.clear_mock_profiles()


def test_client_supplied_role_override_attempt_is_ignored():
    """Verify that role parameters supplied in query string/headers/body cannot override DB profile role."""
    token, _ = helper_create_test_profile("VIEWER")
    try:
        # Client tries sending ?role=ADMINISTRATOR and X-Role header
        response = client.get(
            "/test-rbac/admin-only?role=ADMINISTRATOR",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Role": "ADMINISTRATOR",
            },
        )
        assert response.status_code == 403
        assert "Access forbidden" in response.json()["detail"]
    finally:
        user_repository.clear_mock_profiles()
