"""Authenticated application-profile provisioning for Supabase identities."""

from typing import Any, Dict
from uuid import UUID

from backend.app.repositories.user_repository import (
    UserProfileProvisioningError,
    UserRepository,
    user_repository,
)
from backend.app.schemas.auth import UserRole


class ProfileProvisioningService:
    """Create a missing profile from verified identity claims, never request data."""

    def __init__(self, repository: UserRepository | None = None) -> None:
        self.repository = repository or user_repository

    def provision_authenticated_user(self, user_claims: Dict[str, Any]) -> Dict[str, Any]:
        try:
            auth_user_id = UUID(str(user_claims["auth_user_id"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise UserProfileProvisioningError("Authenticated identity is invalid") from exc

        # Reuse a manually provisioned profile exactly as stored, including its
        # server-assigned role and user_id. No profile metadata is overwritten.
        profile = self.repository.get_by_auth_user_id(auth_user_id)
        if profile:
            return profile

        verified_claims = user_claims.get("claims")
        verified_claims = verified_claims if isinstance(verified_claims, dict) else {}
        user_metadata = verified_claims.get("user_metadata")
        user_metadata = user_metadata if isinstance(user_metadata, dict) else {}
        email = user_claims.get("email") or verified_claims.get("email")
        if not isinstance(email, str) or not email.strip():
            raise UserProfileProvisioningError("Authenticated account has no email address")
        email = email.strip()

        display_name = user_metadata.get("display_name") or user_metadata.get("full_name")
        if not isinstance(display_name, str) or not display_name.strip():
            display_name = email.split("@", 1)[0]
        else:
            display_name = display_name.strip()

        # Existing auth/profile code defaults missing application roles to VIEWER.
        # Keep that least-privilege server-side convention; never read a role
        # from signup metadata, request JSON, or user-controlled app metadata.
        return self.repository.provision_if_missing(
            auth_user_id,
            email=email,
            display_name=display_name,
            role=UserRole.VIEWER.value,
        )


profile_provisioning_service = ProfileProvisioningService()
