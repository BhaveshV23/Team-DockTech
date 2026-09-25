from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from app.core.dependencies import get_current_user_profile
from app.schemas.auth import UserProfileResponse
from app.schemas.cargo_request import CargoRequestCreate, CargoRequestResponse
from app.services.cargo_service import cargo_service

router = APIRouter(prefix="/cargo-requests", tags=["Cargo Requests"])


@router.post(
    "",
    response_model=CargoRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Cargo Request",
    description="Submit a new cargo shipment procurement request.",
)
def create_cargo_request(
    payload: CargoRequestCreate,
    current_user: UserProfileResponse = Depends(get_current_user_profile),
) -> CargoRequestResponse:
    """Create a new cargo request associated with the authenticated user."""
    return cargo_service.create_cargo_request(payload, current_user)


@router.get(
    "/{cargo_request_id}",
    response_model=CargoRequestResponse,
    summary="Get Cargo Request by ID",
    description="Retrieve details of a specific cargo request by its unique UUID.",
)
def get_cargo_request(
    cargo_request_id: UUID,
    current_user: UserProfileResponse = Depends(get_current_user_profile),
) -> CargoRequestResponse:
    """Retrieve a cargo request by ID enforcing ownership/role permissions."""
    return cargo_service.get_cargo_request(cargo_request_id, current_user)


@router.get(
    "",
    response_model=List[CargoRequestResponse],
    summary="List User Cargo Requests",
    description="Retrieve all cargo requests created by the authenticated user.",
)
def list_cargo_requests(
    current_user: UserProfileResponse = Depends(get_current_user_profile),
) -> List[CargoRequestResponse]:
    """List cargo requests belonging to the current user."""
    return cargo_service.list_cargo_requests(current_user)
