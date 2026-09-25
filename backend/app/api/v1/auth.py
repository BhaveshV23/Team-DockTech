from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user_profile
from app.schemas.auth import UserProfileResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


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
