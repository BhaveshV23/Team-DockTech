"""Authoritative DockTech FastAPI application entrypoint."""

import os
import sys

# Keep existing `app.*` imports used by the route modules working when started
# from the repository root as `uvicorn backend.main:app`.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="DockTech API — Bulk Cargo Chartering Decision Support System",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", summary="Health Check")
def root():
    return {"message": "DockTech API is running"}


app.include_router(api_router, prefix=settings.API_V1_STR)
