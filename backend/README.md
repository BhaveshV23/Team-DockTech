# DockTech V1 — Backend Service

FastAPI backend application implementing core business logic, domain engines, cost calculation, scenario analysis, and API routing for the DockTech platform.

## Architecture & Layout

```text
backend/app/
├── main.py                     # FastAPI application entrypoint
├── domain/                     # Pure domain logic (zero external framework dependencies)
│   ├── constants.py            # Controlled vocabularies, enums, units
│   ├── entities.py             # Dataclasses (CargoRequest, VesselClass, ScenarioResult, etc.)
│   ├── voyage_cost.py          # Frozen V1 voyage cost and turnaround calculation engine
│   ├── risk.py                 # Qualitative explainable risk assessment engine
│   └── scenario.py             # Scenario parameter shocks and comparison models
├── schemas/                    # Pydantic request & response schemas
│   ├── common.py               # Standard APIResponse and error schemas
│   └── scenario.py             # Scenario API contract models
├── repositories/               # Database and reference data access layer
│   └── scenario_repository.py  # Repository for scenario_defaults and scenarios
├── services/                   # Business orchestration services
│   └── scenario_service.py     # Scenario sensitivity service
└── api/                        # FastAPI route controllers
    └── v1/
        └── scenarios.py        # /api/v1/scenarios endpoints
```

## Running the Backend

```bash
uvicorn backend.app.main:app --reload --port 8000
```
