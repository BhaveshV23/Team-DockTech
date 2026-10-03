"""Authenticated API for persisted cargo recommendations."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.core.dependencies import get_current_user_profile, require_roles
from backend.app.core.timing import log_timing, timing_start
from backend.app.domain.recommendation.errors import RecommendationError
from backend.app.repositories.recommendation_repository import RecommendationPersistenceError
from backend.app.schemas.auth import UserProfileResponse
from backend.app.schemas.common import APIResponse
from backend.app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from backend.app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


def get_recommendation_service() -> RecommendationService:
    return RecommendationService()


@router.post("", response_model=APIResponse[RecommendationResponse])
def create_recommendation(
    payload: RecommendationRequest,
    service: RecommendationService = Depends(get_recommendation_service),
    current_user: UserProfileResponse = Depends(
        require_roles("PLANNER", "MANAGER", "ADMINISTRATOR")
    ),
):
    started_at = timing_start()
    try:
        try:
            result = service.recommend(
                cargo_request_id=payload.cargo_request_id,
                user_profile=current_user,
                forecast_horizon=payload.forecast_horizon,
                freight_unit=payload.freight_unit,
            )
        except RecommendationPersistenceError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "ERROR_RECOMMENDATION_DATA_UNAVAILABLE", "message": str(exc)},
            ) from exc
        except RecommendationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "ERROR_RECOMMENDATION_INVALID", "message": str(exc)},
            ) from exc
        except HTTPException:
            raise
        return APIResponse(success=True, data=RecommendationResponse(**{
            field: getattr(result, field)
            for field in RecommendationResponse.model_fields
        }))
    finally:
        log_timing("recommendation.endpoint", started_at)
