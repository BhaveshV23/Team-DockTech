"""DockTech V1 backend application root."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.scenarios import router as scenarios_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="DockTech V1 Decision Support API",
        description="Intelligent Freight Forecasting & Chartering Decision Support System",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API v1 routers
    app.include_router(scenarios_router, prefix="/api/v1")

    @app.get("/health", tags=["Health"])
    def health_check():
        return {"status": "healthy", "service": "docktech-backend"}

    return app


app = create_app()
