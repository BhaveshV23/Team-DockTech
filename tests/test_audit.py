from datetime import datetime, timezone
import json
import os
import sys
from uuid import uuid4
import pytest

# Ensure backend directory is in sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from fastapi.testclient import TestClient
import jwt
from app.core.config import settings
from app.repositories.audit_repository import audit_repository
from app.repositories.cargo_repository import cargo_repository
from app.repositories.user_repository import user_repository
from app.schemas.audit import AuditAction, AuditEntityType, AuditEventCreate
from app.services.audit_service import audit_service, scrub_sensitive_data
from main import app

TEST_JWT_SECRET = "docktech-test-jwt-secret-key-32-bytes-long"
settings.SUPABASE_JWT_SECRET = TEST_JWT_SECRET

client = TestClient(app)


def helper_create_test_user(display_name: str = "Audit User", role: str = "PLANNER"):
    user_id = uuid4()
    auth_user_id = uuid4()
    now = datetime.now(timezone.utc).isoformat()

    profile = {
        "user_id": str(user_id),
        "auth_user_id": str(auth_user_id),
        "display_name": display_name,
        "email": f"{str(user_id)[:8]}@docktech.com",
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


def test_audit_action_enum_values():
    """Verify all 6 canonical AuditAction enum values are defined."""
    expected_actions = {
        "CREATE",
        "UPDATE",
        "DELETE",
        "EXPORT",
        "GENERATE_FORECAST",
        "GENERATE_RECOMMENDATION",
    }
    actual_actions = {action.value for action in AuditAction}
    assert actual_actions == expected_actions


def test_audit_entity_type_enum_values():
    """Verify all 10 canonical AuditEntityType enum values are defined."""
    expected_types = {
        "CARGO_REQUEST",
        "FORECAST_RUN",
        "SCENARIO",
        "RECOMMENDATION",
        "REPORT",
        "PORT",
        "BERTH",
        "VESSEL_CLASS",
        "ROUTE",
        "REFERENCE_DATA",
    }
    actual_types = {entity_type.value for entity_type in AuditEntityType}
    assert actual_types == expected_types


def test_audit_event_creation_and_retrieval():
    """Verify recording an audit event persists to repository and is retrievable."""
    audit_repository.clear_mock_logs()
    user_id = uuid4()
    entity_id = str(uuid4())

    try:
        saved = audit_service.record_event(
            user_id=user_id,
            action=AuditAction.CREATE,
            entity_type=AuditEntityType.CARGO_REQUEST,
            entity_id=entity_id,
            details={"cargo_volume_mt": 50000.0, "commodity": "THERMAL_COAL"},
        )
        assert saved["audit_log_id"] is not None
        assert saved["user_id"] == str(user_id)
        assert saved["action"] == "CREATE"
        assert saved["entity_type"] == "CARGO_REQUEST"
        assert saved["entity_id"] == entity_id

        retrieved = audit_repository.get_by_id(saved["audit_log_id"])
        assert retrieved is not None
        assert retrieved["audit_log_id"] == saved["audit_log_id"]
    finally:
        audit_repository.clear_mock_logs()


def test_audit_details_json_serialization():
    """Verify audit details are serialized as valid JSON text in details column."""
    audit_repository.clear_mock_logs()
    user_id = uuid4()
    entity_id = "PORT_PARADIP"
    details_input = {"origin": "NEWCASTLE", "destination": "PARADIP", "draft_limit_m": 14.5}

    try:
        saved = audit_service.record_event(
            user_id=user_id,
            action=AuditAction.UPDATE,
            entity_type=AuditEntityType.PORT,
            entity_id=entity_id,
            details=details_input,
        )
        assert isinstance(saved["details"], str)
        parsed_details = json.loads(saved["details"])
        assert parsed_details["origin"] == "NEWCASTLE"
        assert parsed_details["destination"] == "PARADIP"
        assert parsed_details["draft_limit_m"] == 14.5
    finally:
        audit_repository.clear_mock_logs()


def test_audit_nested_sensitive_field_scrubbing():
    """Verify recursive scrubbing redacts password, token, secret, authorization, and key values."""
    sensitive_payload = {
        "user_email": "user@docktech.com",
        "password": "SuperSecretPassword123!",
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.secret_signature",
        "nested_meta": {
            "access_token": "secret_access_token_abc",
            "refresh_token": "secret_refresh_token_xyz",
            "authorization": "Bearer secret_bearer_token",
            "authorization_header": "Bearer raw_auth_header",
            "jwt": "raw_jwt_string",
            "secret": "super_top_secret_value",
            "api_key": "api_key_secret_12345",
            "service_role_key": "supabase_service_role_key_value",
            "supabase_service_role_key": "another_secret_key",
            "safe_list": [
                {"user_password": "nested_list_password_123"},
                {"safe_field": "allowed_value"},
            ],
        },
    }

    scrubbed = scrub_sensitive_data(sensitive_payload)

    # Verify sensitive fields redacted
    assert scrubbed["password"] == "[REDACTED]"
    assert scrubbed["token"] == "[REDACTED]"
    assert scrubbed["nested_meta"]["access_token"] == "[REDACTED]"
    assert scrubbed["nested_meta"]["refresh_token"] == "[REDACTED]"
    assert scrubbed["nested_meta"]["authorization"] == "[REDACTED]"
    assert scrubbed["nested_meta"]["authorization_header"] == "[REDACTED]"
    assert scrubbed["nested_meta"]["jwt"] == "[REDACTED]"
    assert scrubbed["nested_meta"]["secret"] == "[REDACTED]"
    assert scrubbed["nested_meta"]["api_key"] == "[REDACTED]"
    assert scrubbed["nested_meta"]["service_role_key"] == "[REDACTED]"
    assert scrubbed["nested_meta"]["supabase_service_role_key"] == "[REDACTED]"
    assert scrubbed["nested_meta"]["safe_list"][0]["user_password"] == "[REDACTED]"

    # Verify non-sensitive fields preserved
    assert scrubbed["user_email"] == "user@docktech.com"
    assert scrubbed["nested_meta"]["safe_list"][1]["safe_field"] == "allowed_value"

    # Verify secret string values NEVER appear anywhere in serialized JSON
    serialized = json.dumps(scrubbed)
    forbidden_values = [
        "SuperSecretPassword123!",
        "secret_signature",
        "secret_access_token_abc",
        "secret_refresh_token_xyz",
        "secret_bearer_token",
        "raw_auth_header",
        "raw_jwt_string",
        "super_top_secret_value",
        "api_key_secret_12345",
        "supabase_service_role_key_value",
        "nested_list_password_123",
    ]
    for secret in forbidden_values:
        assert secret not in serialized


def test_invalid_action_or_entity_type_raises_value_error():
    """Verify passing invalid action or entity type raises ValueError."""
    user_id = uuid4()
    with pytest.raises(ValueError, match="Invalid audit action"):
        audit_service.record_event(
            user_id=user_id,
            action="INVALID_ACTION",
            entity_type=AuditEntityType.CARGO_REQUEST,
            entity_id="123",
        )

    with pytest.raises(ValueError, match="Invalid audit entity type"):
        audit_service.record_event(
            user_id=user_id,
            action=AuditAction.CREATE,
            entity_type="INVALID_ENTITY_TYPE",
            entity_id="123",
        )


def test_authenticated_cargo_creation_produces_audit_event():
    """Verify authenticated cargo request creation automatically logs CREATE / CARGO_REQUEST audit event."""
    audit_repository.clear_mock_logs()
    cargo_repository.clear_mock_requests()
    user_repository.clear_mock_profiles()

    token, profile = helper_create_test_user("Cargo Creator", "PLANNER")

    payload = {
        "commodity": "COKING_COAL",
        "cargo_volume_mt": 85000.0,
        "origin_port_id": "GLADSTONE",
        "destination_port_id": "VISAKHAPATNAM",
        "earliest_delivery_date": "2026-11-01",
        "latest_delivery_date": "2026-11-15",
        "contract_horizon": "SPOT",
    }

    try:
        response = client.post(
            "/api/v1/cargo-requests",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        assert response.status_code == 201
        created_cargo = response.json()
        cargo_id = created_cargo["cargo_request_id"]

        # Retrieve audit logs for user
        audit_logs = audit_repository.get_by_user_id(profile["user_id"])
        assert len(audit_logs) >= 1

        matching_log = next(
            (log for log in audit_logs if log["entity_id"] == str(cargo_id)), None
        )
        assert matching_log is not None
        assert matching_log["action"] == "CREATE"
        assert matching_log["entity_type"] == "CARGO_REQUEST"
        assert matching_log["user_id"] == profile["user_id"]

        # Verify details
        details = json.loads(matching_log["details"])
        assert details["commodity"] == "COKING_COAL"
        assert details["origin_port_id"] == "GLADSTONE"
        assert details["destination_port_id"] == "VISAKHAPATNAM"
    finally:
        audit_repository.clear_mock_logs()
        cargo_repository.clear_mock_requests()
        user_repository.clear_mock_profiles()


def test_unauthenticated_cargo_creation_remains_protected_and_no_audit():
    """Verify unauthenticated request fails with 401 and creates no audit log."""
    audit_repository.clear_mock_logs()
    payload = {
        "commodity": "THERMAL_COAL",
        "cargo_volume_mt": 75000.0,
        "origin_port_id": "NEWCASTLE",
        "destination_port_id": "PARADIP",
        "earliest_delivery_date": "2026-10-01",
        "latest_delivery_date": "2026-10-15",
        "contract_horizon": "SPOT",
    }

    try:
        response = client.post("/api/v1/cargo-requests", json=payload)
        assert response.status_code == 401
        assert len(audit_repository._mock_audit_logs) == 0
    finally:
        audit_repository.clear_mock_logs()
