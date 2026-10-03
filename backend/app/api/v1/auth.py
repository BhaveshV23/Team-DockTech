from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from app.core.dependencies import (
    get_current_authenticated_user,
    get_current_user_profile,
    require_roles,
)
from backend.app.repositories.user_repository import (
    UserProfileNotFoundError,
    UserProfileProvisioningError,
    UserProfileStorageError,
)
from app.schemas.auth import RoleUpdateRequest, UserProfileResponse, UserProfileSummary
from backend.app.services.profile_service import (
    ProfileProvisioningService,
    ProfileSelfRoleAssignmentError,
    profile_provisioning_service,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_profile_provisioning_service() -> ProfileProvisioningService:
    return profile_provisioning_service


@router.post(
    "/provision",
    response_model=UserProfileResponse,
    summary="Provision Current User Profile",
    description="Create or return the application profile for the verified Supabase identity.",
)
def provision_current_user_profile(
    user_claims: dict = Depends(get_current_authenticated_user),
    service: ProfileProvisioningService = Depends(get_profile_provisioning_service),
) -> UserProfileResponse:
    try:
        profile = service.provision_authenticated_user(user_claims)
    except UserProfileProvisioningError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application profile provisioning is unavailable",
        ) from exc
    return UserProfileResponse.model_validate(profile)


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get Current User Profile",
    description=(
        "Retrieve the currently authenticated user's application profile"
        " linked to their Supabase identity."
    ),
)
def get_current_user_me(
    profile: UserProfileResponse = Depends(get_current_user_profile),
) -> UserProfileResponse:
    """Return the application profile for the authenticated request."""
    return profile


@router.get(
    "/users",
    response_model=list[UserProfileSummary],
    summary="List User Profiles",
    description="List user profiles for administrator role-management workflows.",
)
def list_user_profiles(
    _current_user: UserProfileResponse = Depends(require_roles("ADMINISTRATOR")),
    service: ProfileProvisioningService = Depends(get_profile_provisioning_service),
) -> list[UserProfileSummary]:
    try:
        profiles = service.list_user_profiles()
    except UserProfileStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application profile storage is unavailable",
        ) from exc
    return [UserProfileSummary.model_validate(profile) for profile in profiles]


@router.patch(
    "/users/{user_id}/role",
    response_model=UserProfileResponse,
    summary="Assign Application Role",
    description="Change another user's application role; administrator access required.",
)
def assign_user_role(
    user_id: UUID,
    payload: RoleUpdateRequest,
    current_user: UserProfileResponse = Depends(require_roles("ADMINISTRATOR")),
    service: ProfileProvisioningService = Depends(get_profile_provisioning_service),
) -> UserProfileResponse:
    try:
        profile = service.assign_role(
            target_user_id=user_id,
            role=payload.role,
            caller_profile=current_user,
        )
    except ProfileSelfRoleAssignmentError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except UserProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found") from exc
    except UserProfileStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application profile role update is unavailable",
        ) from exc
    return UserProfileResponse.model_validate(profile)
