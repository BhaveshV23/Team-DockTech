# DockTech V1 — Automated Test Suite & QA

Comprehensive automated test suites for DockTech V1 covering pure domain calculations, service orchestration, database persistence, FastAPI routes, and cross-module end-to-end decision workflows.

## Test Suite Structure

```text
tests/
├── conftest.py                                     # Pytest fixtures and canonical domain objects
├── unit/
│   └── domain/
│       ├── test_scenario.py                        # SC-001 through SC-018 scenario tests
│       ├── test_voyage_cost.py                     # Frozen V1 cost and turnaround math tests
│       └── test_risk.py                            # Qualitative risk heuristics tests
├── services/
│   └── test_scenario_service.py                    # Service orchestration & persistence tests
├── api/
│   └── test_scenarios_api.py                       # FastAPI routes, schemas, and error tests
└── integration/
    ├── test_scenario_cost_integration.py           # Cost and scenario consistency tests
    ├── test_forecast_feasibility_boundaries.py     # Forecast spread & feasibility boundary tests
    ├── test_database_persistence.py                # Supabase schema & scenario defaults tests
    ├── test_e2e_decision_flow.py                   # Full end-to-end decision flow QA
    └── test_failure_modes.py                       # Negative inputs & edge case failure tests
```

## Running the Tests

```bash
# Run all automated tests
python3 -m pytest -v

# Run with coverage report
python3 -m pytest --cov=backend/app tests/
```
