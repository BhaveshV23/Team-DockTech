from typing import List
from fastapi import HTTPException, status
from app.repositories.reference_repository import reference_repository
from app.schemas.reference_data import (
    PortResponse,
    RouteResponse,
    VesselClassResponse,
)


class ReferenceService:
    """Application service for orchestrating reference data requests."""

    def get_ports(self) -> List[PortResponse]:
        try:
            records = reference_repository.get_ports()
            return [PortResponse(**r) for r in records]
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve reference ports",
            )

    def get_vessels(self) -> List[VesselClassResponse]:
        try:
            records = reference_repository.get_vessels()
            return [VesselClassResponse(**r) for r in records]
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve reference vessel classes",
            )

    def get_routes(self) -> List[RouteResponse]:
        try:
            records = reference_repository.get_routes()
            return [RouteResponse(**r) for r in records]
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve reference routes",
            )


reference_service = ReferenceService()
