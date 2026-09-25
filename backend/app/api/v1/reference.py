from typing import List
from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user_profile
from app.schemas.auth import UserProfileResponse
from app.schemas.reference_data import (
    PortResponse,
    RouteResponse,
    VesselClassResponse,
)
from app.services.reference_service import reference_service

router = APIRouter(tags=["Reference Data"])


@router.get(
    "/ports",
    response_model=List[PortResponse],
    summary="Get Reference Ports",
    description="Retrieve canonical reference list of ports.",
)
def get_ports(
    current_user: UserProfileResponse = Depends(get_current_user_profile),
) -> List[PortResponse]:
    """Retrieve reference ports for authenticated users."""
    return reference_service.get_ports()


@router.get(
    "/vessels",
    response_model=List[VesselClassResponse],
    summary="Get Reference Vessel Classes",
    description="Retrieve canonical reference list of bulk carrier vessel classes.",
)
def get_vessels(
    current_user: UserProfileResponse = Depends(get_current_user_profile),
) -> List[VesselClassResponse]:
    """Retrieve reference vessel classes for authenticated users."""
    return reference_service.get_vessels()


@router.get(
    "/routes",
    response_model=List[RouteResponse],
    summary="Get Reference Routes",
    description="Retrieve canonical reference list of trade routes.",
)
def get_routes(
    current_user: UserProfileResponse = Depends(get_current_user_profile),
) -> List[RouteResponse]:
    """Retrieve reference trade routes for authenticated users."""
    return reference_service.get_routes()
