from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user_profile
from app.schemas.auth import UserProfileResponse
from app.schemas.provenance import ProvenanceResponse
from app.services.provenance_service import get_reference_provenance


router = APIRouter(prefix="/provenance", tags=["Data Provenance"])


@router.get("", response_model=ProvenanceResponse)
def get_provenance(
    _current_user: UserProfileResponse = Depends(get_current_user_profile),
) -> ProvenanceResponse:
    return ProvenanceResponse(**get_reference_provenance())
