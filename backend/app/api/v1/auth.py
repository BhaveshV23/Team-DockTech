from fastapi import APIRouter, Depends, HTTPException, status
from app.core.dependencies import get_current_authenticated_user, get_current_user_profile
from backend.app.repositories.user_repository import UserProfileProvisioningError
from app.schemas.auth import UserProfileResponse
from backend.app.services.profile_service import ProfileProvisioningService, profile_provisioning_service

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
