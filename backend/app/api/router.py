from fastapi import APIRouter
from app.api.v1 import (
    auth,
    cargo,
    reference,
    forecast,
    feasibility,
    cost,
    provenance,
)
from backend.app.api.v1 import (
    scenarios,
    recommendations,
)
api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(cargo.router)
api_router.include_router(reference.router)
api_router.include_router(forecast.router)

api_router.include_router(feasibility.router)

api_router.include_router(cost.router)
api_router.include_router(provenance.router)

api_router.include_router(scenarios.router)
api_router.include_router(recommendations.router)
