from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4
from app.repositories.audit_repository import audit_repository
from app.schemas.audit import AuditAction, AuditEntityType, AuditEventCreate

SENSITIVE_KEYWORDS = [
    "password",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "authorization_header",
    "jwt",
    "secret",
    "api_key",
    "service_role_key",
    "supabase_service_role_key",
]


def scrub_sensitive_data(data: Any) -> Any:
    """Recursively scrub sensitive keys and values from dictionaries, lists, and strings."""
    if isinstance(data, dict):
        scrubbed = {}
        for k, v in data.items():
            key_str = str(k).lower()
            is_sensitive = any(sk in key_str for sk in SENSITIVE_KEYWORDS)
            if is_sensitive:
                scrubbed[k] = "[REDACTED]"
            else:
                scrubbed[k] = scrub_sensitive_data(v)
        return scrubbed
    elif isinstance(data, list):
        return [scrub_sensitive_data(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(scrub_sensitive_data(item) for item in data)
    elif isinstance(data, str):
        if data.strip().lower().startswith("bearer "):
            return "Bearer [REDACTED]"
        if data.strip().startswith("{") or data.strip().startswith("["):
            try:
                parsed = json.loads(data)
                scrubbed_parsed = scrub_sensitive_data(parsed)
                return json.dumps(scrubbed_parsed)
            except Exception:
                pass
        return data
    else:
        return data


class AuditService:
    """Service handling audit event validation, sensitive field scrubbing, and persistence."""

    def record_event(
        self,
        event: Optional[AuditEventCreate] = None,
        *,
        user_id: Optional[UUID] = None,
        action: Optional[Union[AuditAction, str]] = None,
        entity_type: Optional[Union[AuditEntityType, str]] = None,
        entity_id: Optional[str] = None,
        details: Any = None,
    ) -> Dict[str, Any]:
        """Validate, scrub, and record an audit event."""
        if event is not None:
            user_id = event.user_id
            action = event.action
            entity_type = event.entity_type
            entity_id = event.entity_id
            details = event.details

        if user_id is None:
            raise ValueError("user_id is required for audit event recording")
        if action is None:
            raise ValueError("action is required for audit event recording")
        if entity_type is None:
            raise ValueError("entity_type is required for audit event recording")
        if entity_id is None or not str(entity_id).strip():
            raise ValueError("entity_id is required for audit event recording")

        # Validate action enum
        if isinstance(action, str):
            try:
                action = AuditAction(action.upper())
            except ValueError:
                raise ValueError(f"Invalid audit action: {action}")

        # Validate entity_type enum
        if isinstance(entity_type, str):
            try:
                entity_type = AuditEntityType(entity_type.upper())
            except ValueError:
                raise ValueError(f"Invalid audit entity type: {entity_type}")

        # Scrub sensitive fields in details
        scrubbed_details = scrub_sensitive_data(details)

        # Serialize details to JSON text string if not None
        serialized_details: Optional[str] = None
        if scrubbed_details is not None:
            if isinstance(scrubbed_details, str):
                serialized_details = scrubbed_details
            else:
                serialized_details = json.dumps(scrubbed_details, default=str)

        audit_log_id = uuid4()
        now_utc = datetime.now(timezone.utc).isoformat()

        record = {
            "audit_log_id": str(audit_log_id),
            "user_id": str(user_id),
            "action": action.value,
            "entity_type": entity_type.value,
            "entity_id": str(entity_id),
            "details": serialized_details,
            "created_at": now_utc,
        }

        # Persist through repository
        return audit_repository.create(record)


audit_service = AuditService()
