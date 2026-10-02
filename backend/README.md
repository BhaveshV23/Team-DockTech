# DockTech V1 — Backend Service

FastAPI backend application implementing core business logic, domain engines, cost calculation, scenario analysis, and API routing for the DockTech platform.

## Architecture & Layout

```text
backend/
  main.py                 # Authoritative FastAPI application entrypoint
  app/
    main.py               # Compatibility import for backend.main:app
    api/router.py         # Complete API v1 router
    domain/               # Pure domain logic
    schemas/              # Pydantic request and response schemas
    repositories/         # Database and reference data access
    services/             # Business orchestration services
```

## Running the Backend

```bash
uvicorn backend.main:app --reload --port 8000
```

Run this command from the repository root. `backend.main:app` is the
authoritative FastAPI application; it mounts the complete API router from
`backend/app/api/router.py` and applies configured CORS origins.
`backend.app.main:app` remains only as a compatibility alias to this same
application; it does not construct a second app or mount a partial route set.
