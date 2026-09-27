from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.services.feasibility_service import FeasibilityService


router = APIRouter(
    prefix="/feasibility",
    tags=["Feasibility"],
)

feasibility_service = FeasibilityService()


class FeasibilityRequest(BaseModel):
    origin_port_id: str = Field(..., min_length=1)
    destination_port_id: str = Field(..., min_length=1)
    commodity: str = Field(..., min_length=1)
    vessel_class_id: str = Field(..., min_length=1)
    cargo_volume_mt: float = Field(..., gt=0)


class FeasibilityResponse(BaseModel):
    is_feasible: bool
    status: str
    vessel_class_id: str
    origin_port_id: str
    destination_port_id: str
    commodity: str
    cargo_volume_mt: float
    required_voyages: int
    rejection_reason_code: str | None = None
    rejection_reason: str | None = None


@router.post(
    "",
    response_model=FeasibilityResponse,
)
def check_feasibility(
    request: FeasibilityRequest,
) -> FeasibilityResponse:

    try:
        result = feasibility_service.check_feasibility(
            origin_port_id=request.origin_port_id,
            destination_port_id=request.destination_port_id,
            commodity=request.commodity,
            vessel_class_id=request.vessel_class_id,
            cargo_volume_mt=request.cargo_volume_mt,
        )

        return FeasibilityResponse(
            is_feasible=result.is_feasible,
            status=str(result.status),
            vessel_class_id=request.vessel_class_id,
            origin_port_id=request.origin_port_id,
            destination_port_id=request.destination_port_id,
            commodity=request.commodity,
            cargo_volume_mt=request.cargo_volume_mt,
            required_voyages=result.required_voyages,
                        rejection_reason_code=(
                result.rejection_codes[0]
                if result.rejection_codes
                else None
            ),
            rejection_reason=(
                result.rejection_reasons[0]
                if result.rejection_reasons
                else None
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc