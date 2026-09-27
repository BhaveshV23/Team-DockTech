from typing import Any, Dict, Union
from uuid import UUID
from fastapi import Depends, HTTPException, Header, status
from app.integrations.supabase_auth import auth_verifier, SupabaseAuthError
from app.repositories.user_repository import user_repository
from app.schemas.auth import UserProfileResponse, UserRole


def get_token_from_header(
    authorization: str = Header(None, alias="Authorization"),
) -> str:
    """Extract Bearer JWT token from Authorization header."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token


def get_current_authenticated_user(
    token: str = Depends(get_token_from_header),
) -> Dict[str, Any]:
    """Verify JWT token and return authenticated Supabase user claims."""
    try:
        user_claims = auth_verifier.verify_token(token)
        return user_claims
    except SupabaseAuthError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_profile(
    user_claims: Dict[str, Any] = Depends(get_current_authenticated_user),
) -> UserProfileResponse:
    """Retrieve application user_profile matching authenticated Supabase user."""
    auth_user_id_raw = user_claims.get("auth_user_id")
    if not auth_user_id_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing auth_user_id claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        auth_user_id = UUID(str(auth_user_id_raw))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid auth_user_id format in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    profile_dict = user_repository.get_by_auth_user_id(auth_user_id)
    if not profile_dict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )

    role = profile_dict.get("role", "VIEWER")
    if role not in ["VIEWER", "PLANNER", "MANAGER", "ADMINISTRATOR"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid user role configuration",
        )

    return UserProfileResponse(
        user_id=profile_dict["user_id"],
        auth_user_id=profile_dict["auth_user_id"],
        display_name=profile_dict["display_name"],
        email=profile_dict["email"],
        role=role,
        created_at=profile_dict["created_at"],
        updated_at=profile_dict["updated_at"],
    )


def require_roles(*allowed_roles: Union[str, UserRole]):
    """FastAPI dependency factory enforcing that the authenticated user possesses one of the allowed application roles."""

    def role_checker(
        current_profile: UserProfileResponse = Depends(get_current_user_profile),
    ) -> UserProfileResponse:
        permitted = {
            r.value if isinstance(r, UserRole) else str(r).upper()
            for r in allowed_roles
        }
        user_role = (
            current_profile.role.upper() if current_profile.role else "VIEWER"
        )

        if user_role not in permitted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access forbidden: user role '{current_profile.role}' is not"
                    " authorized to access this resource"
                ),
            )
        return current_profile

    return role_checker
