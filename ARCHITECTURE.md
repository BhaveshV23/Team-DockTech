# System Architecture

## Product
**DockTech** is an intelligent freight forecasting and chartering decision-support system for SAIL bulk-cargo procurement to India’s East Coast ports. The system combines freight forecasting, vessel–port feasibility checks, voyage-cost estimation, risk scenarios, and actionable chartering recommendations.

## Supabase Architecture
This version uses **Supabase as the managed data and identity platform**:
- **Supabase Auth** handles authentication and sessions.
- **Supabase PostgreSQL** stores application and reference data.
- **Supabase Storage** can store generated reports and uploaded files.
- **FastAPI** remains responsible for business logic, forecasting, feasibility, recommendations, scenarios, and server-side authorization.
- **React** uses Supabase Auth for identity/session operations but accesses application data through FastAPI APIs.
- **Redis** remains optional for caching.

## Architecture Goals
- Keep business logic independent of the user interface.
- Make data sources, port constraints, vessel specifications, and model artifacts replaceable and traceable.
- Support a fast SIH MVP while preserving a clean path to production deployment.
- Return explainable recommendations, assumptions, and risk flags rather than opaque model outputs.
- Keep application data access behind the FastAPI backend while using Supabase Auth for identity and session management.

## System Context
The user enters cargo and planning details into the dashboard. Supabase Auth establishes identity and session state. The backend validates the authenticated request, verifies authorization, retrieves data from Supabase, runs forecasting and optimization logic, applies scenarios, and returns a recommendation with supporting calculations.

```text
+----------------------+       HTTPS        +---------------------------+
| Web UI / Dashboard   | <--------------->  | Backend API               |
| React                |                    | FastAPI                   |
+----------+-----------+                    +------------+--------------+
           |                                             |
           | Supabase Auth                               |
           | session / JWT                               |
           v                                             |
+----------------------+                                  |
| Supabase Auth       | <--------------------------------+
| Identity + Sessions |
+----------------------+                                  |
                                                         |
                                  +----------------------+----------------------+
                                  |                      |                      |
                         +--------v---------+   +--------v---------+   +--------v---------+
                         | Auth/JWT         |   | Application      |   | Forecast &       |
                         | verification     |   | Services        |   | Decision Engine  |
                         +------------------+   +--------+---------+   +--------+---------+
                                                        |                      |
                                         +--------------v----------------------+
                                         | Repository / Supabase Data Access  |
                                         +----------------+-------------------+
                                                          |
                                      +-------------------v-------------------+
                                      | Supabase                            |
                                      | PostgreSQL + Auth + Storage         |
                                      +-------------------------------------+
```

## Logical Layers

### Presentation layer
**Responsibilities**
- Render forms, charts, tables, alerts, and downloadable reports.
- Collect user input and call backend APIs.
- Display loading, validation, error, and empty states.
- Present explanations, assumptions, and risk warnings returned by the backend.

**Does not do**
- Direct database access.
- SQL queries or ORM calls.
- Secret handling.
- Authorization decisions.
- Freight calculations, forecasting, vessel feasibility, or recommendation rules.

### API layer
**Responsibilities**
- Define request and response contracts.
- Authenticate requests and enforce authorization before protected actions.
- Validate incoming payloads using schemas.
- Map requests to application services.
- Return structured, safe responses and standardized errors.

**Does not do**
- Embed complex forecasting, cost, or optimization algorithms in route handlers.
- Use UI-specific presentation logic.

### Application/service layer
**Responsibilities**
- Coordinate business workflows.
- Fetch and persist data through repositories.
- Invoke forecasting, feasibility, cost, risk, and recommendation modules.
- Enforce business rules that span more than one domain object.
- Build the complete decision result returned to the API.

**Examples**
- `RecommendationService.create_recommendation()`
- `ForecastService.generate_forecast()`
- `PortService.get_port_constraints()`
- `ScenarioService.apply_scenario()`
- `ReportService.generate_decision_summary()`

### Domain/business layer
**Responsibilities**
- Hold pure, testable business logic independent of HTTP, UI, and database technology.
- Check vessel–port compatibility.
- Estimate voyage and turnaround time.
- Compute cost-per-tonne comparison.
- Rank vessel alternatives.
- Derive market-entry recommendation and risk flags.

**Design preference**
- Functions in this layer should accept typed inputs and return typed outputs.
- Domain code should be deterministic wherever possible; external data fetching belongs outside it.

### Data access layer
**Responsibilities**
- Encapsulate all database/file-store access.
- Provide repository interfaces and implementations.
- Convert persistence models to domain/application objects.
- Handle transactions, query efficiency, and data-source details.

**Does not do**
- Return raw database concerns directly to UI components.
- Implement chartering recommendation policy.

### Data science and model layer
**Responsibilities**
- Prepare datasets and features.
- Train, validate, version, and load forecasting models.
- Generate point forecasts and uncertainty ranges.
- Log model/data versions and evaluation metrics.

**MVP approach**
- Use a baseline model and one improved model.
- Keep inference behind a stable `ForecastService` interface so models can change without changing the UI or API contract.

## Major Components

### Dashboard
The dashboard is the interaction point for chartering managers. It includes: 
- Cargo planning form: commodity, cargo volume, origin, destination, delivery window, and contract horizon.
- Freight forecast panel: historical values, forecast trend, and low/base/high range.
- Vessel comparison panel: feasibility, capacity fit, estimated turnaround, cost per tonne, and risk.
- Recommendation card: fix now / wait / consider multi-voyage contract, with reason.
- Scenario panel: freight-rate shock and congestion delay controls.
- Report export action.

### Authentication and authorization
Supabase Auth establishes identity and manages authenticated sessions. FastAPI remains responsible for validating Supabase access tokens and enforcing application-level authorization.

**MVP**
- Use Supabase Auth for email/password authentication and session management.
- React uses the Supabase client for sign-in/sign-out and maintains the authenticated session.
- FastAPI verifies the Supabase access token on every protected request.
- Store application roles/profile metadata in Supabase and enforce role checks server-side.
- Keep Supabase service-role keys and other secrets only in backend environment variables.

**Production direction**
- Use Supabase Auth with enterprise SSO/OIDC where required.
- Enforce role-based access control (RBAC): `viewer`, `planner`, `manager`, `administrator`.
- Maintain audit records for saved scenarios, configuration changes, and exports.

### Reference-data management
Reference data consists of port constraints, vessel specifications, route assumptions, and commodity defaults.

**MVP storage**
- Store operational/reference data in Supabase PostgreSQL.
- Keep version-controlled seed CSV/JSON files for reproducible initialization and fallback/reference inputs.
- Each record must include source, effective date, unit, and data-quality/proxy label.

**Production direction**
- Administration workflow with approval and audit trail.
- Data validation rules and effective-dating for port notices.

### Forecasting engine
- Receives route/vessel-class context and forecast horizon.
- Loads selected model artifact and latest feature values.
- Returns historical observations, forecast timestamps, central estimate, lower bound, upper bound, model version, and data recency.
- Supports a fallback baseline when an advanced model or required data is unavailable.

### Feasibility and optimization engine
- Applies origin and destination restrictions to candidate vessel classes.
- Rejects options that exceed draft, LOA, or beam limits.
- Estimates sailing duration, port handling duration, waiting time, total cost, and cost per tonne.
- Ranks feasible alternatives and produces explanation codes.

### Recommendation engine
Combines forecast, operational feasibility, delivery urgency, expected cost, and scenario results to produce a decision-support recommendation.

**Output contract**
- Recommended action.
- Recommended vessel class/range.
- Ranked alternatives.
- Expected cost range and turnaround.
- Risk flags and confidence/uncertainty.
- Plain-language rationale.
- Assumptions and data/model version metadata.

## End-to-End Request Flow

### Generate a recommendation
1. User signs in through Supabase Auth from the dashboard.
2. UI sends a `POST /api/v1/recommendations` request containing cargo and planning input.
3. API verifies the Supabase access token server-side and checks role permissions.
4. API validates the request schema.
5. `RecommendationService` loads ports, vessel options, route assumptions, and relevant freight series through repositories.
6. The feasibility engine filters invalid vessels and computes operational estimates.
7. `ForecastService` generates the selected freight forecast and uncertainty range.
8. The cost and recommendation engines rank feasible options and determine recommended timing/action.
9. API returns a structured recommendation payload.
10. UI renders returned data only; it does not reproduce domain calculations.

### Apply a scenario
1. User changes freight-shock or congestion-delay controls.
2. UI sends scenario parameters and the planning input to `POST /api/v1/scenarios/evaluate`.
3. Backend authenticates, validates, calculates the scenario, and returns updated costs, recommendation, and risk flags.
4. UI updates the comparison and explanation.

## API Design
All endpoints are versioned under `/api/v1`. API route handlers remain thin: authenticate, validate, invoke a service, and serialize response.

| Endpoint | Method | Purpose | Required Role |
|---|---:|---|---|
| `/auth/me` | GET | Return current authenticated user/profile | Authenticated |
| `/ports` | GET | List supported ports and public planning metadata | Authenticated |
| `/vessels` | GET | List vessel classes/specifications | Authenticated |
| `/routes` | GET | List supported route definitions | Authenticated |
| `/forecasts` | POST | Return a route/vessel forecast | Planner/Manager |
| `/recommendations` | POST | Generate end-to-end chartering recommendation | Planner/Manager |
| `/scenarios/evaluate` | POST | Recalculate recommendation under a scenario | Planner/Manager |
| `/reports/recommendation` | POST | Generate decision report | Planner/Manager |
| `/admin/ports` | POST/PATCH | Create/update port reference data | Administrator |
| `/admin/vessels` | POST/PATCH | Create/update vessel reference data | Administrator |

## Core Domain Data Model

### Main entities
| Entity | Purpose | Key fields |
|---|---|---|
| `UserProfile` | Application profile linked to Supabase Auth user | id, auth_user_id, name, email, role, status |
| `Port` | Origin/destination port reference data | id, name, country, max_draft_m, max_loa_m, max_beam_m, handling_rate_tpd, effective_from, source |
| `VesselClass` | Typical vessel characteristics | id, name, dwt_min, dwt_max, draft_m, loa_m, beam_m, speed_knots, geared |
| `Route` | Origin–destination planning route | id, origin_port_id, destination_port_id, distance_nm, route_notes |
| `FreightSeries` | Observed/proxy freight data | id, route_id, vessel_class_id, date, rate, currency, unit, source, quality_label |
| `ForecastRun` | Traceable forecast output | id, series_id, horizon, model_version, generated_at, data_as_of |
| `ForecastPoint` | Forecast value by date/quantile | forecast_run_id, date, p10, p50, p90 |
| `CargoRequest` | User planning input | id, commodity, quantity_tonnes, origin_port_id, destination_port_id, delivery_start, delivery_end, contract_horizon |
| `Scenario` | User-adjustable planning assumption | id, freight_shock_pct, congestion_delay_days, fuel_shock_pct |
| `Recommendation` | Stored decision result | id, cargo_request_id, action, selected_vessel_id, cost_low, cost_base, cost_high, rationale, created_at |
| `AuditLog` | Security and governance trace | id, user_id, action, entity, entity_id, timestamp, metadata |

### Relationships
```text
Port (origin) ----+
                 |--> Route --> FreightSeries --> ForecastRun --> ForecastPoint
Port (destination)+

CargoRequest --> Recommendation
CargoRequest --> Scenario
VesselClass --> FreightSeries
VesselClass --> Recommendation
User --> CargoRequest / Scenario / AuditLog
```

## Folder Structure
This structure uses a Python FastAPI backend and a React frontend. The frontend is a separate web application that communicates with the backend through APIs.

```text
docktech/
├── README.md
├── PRD.md
├── ARCHITECTURE.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Makefile
├── docs/
│   ├── api-contracts.md
│   ├── data-dictionary.md
│   ├── model-card.md
│   ├── assumptions.md
│   └── demo-script.md
├── data/
│   ├── raw/
│   ├── processed/
│   ├── reference/
│   │   ├── ports.csv
│   │   ├── vessel_classes.csv
│   │   ├── routes.csv
│   │   └── commodity_defaults.csv
│   └── sample/
├── models/
│   ├── artifacts/
│   ├── metadata/
│   └── training/
├── backend/
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   ├── dependencies.py
│   │   │   ├── logging.py
│   │   │   └── exceptions.py
│   │   ├── api/
│   │   │   ├── router.py
│   │   │   └── v1/
│   │   │       ├── auth.py
│   │   │       ├── ports.py
│   │   │       ├── vessels.py
│   │   │       ├── routes.py
│   │   │       ├── forecasts.py
│   │   │       ├── recommendations.py
│   │   │       ├── scenarios.py
│   │   │       ├── reports.py
│   │   │       └── admin.py
│   │   ├── schemas/
│   │   │   ├── auth.py
│   │   │   ├── cargo.py
│   │   │   ├── forecast.py
│   │   │   ├── recommendation.py
│   │   │   ├── scenario.py
│   │   │   └── common.py
│   │   ├── domain/
│   │   │   ├── entities.py
│   │   │   ├── feasibility.py
│   │   │   ├── voyage_cost.py
│   │   │   ├── ranking.py
│   │   │   ├── recommendation_rules.py
│   │   │   ├── risk.py
│   │   │   └── constants.py
│   │   ├── services/
│   │   │   ├── port_service.py
│   │   │   ├── vessel_service.py
│   │   │   ├── route_service.py
│   │   │   ├── forecast_service.py
│   │   │   ├── recommendation_service.py
│   │   │   ├── scenario_service.py
│   │   │   ├── report_service.py
│   │   │   └── audit_service.py
│   │   ├── repositories/
│   │   │   ├── base.py
│   │   │   ├── port_repository.py
│   │   │   ├── vessel_repository.py
│   │   │   ├── route_repository.py
│   │   │   ├── freight_repository.py
│   │   │   ├── recommendation_repository.py
│   │   │   └── audit_repository.py
│   │   ├── integrations/
│   │   │   ├── supabase_client.py
│   │   │   ├── supabase_auth.py
│   │   │   └── storage_client.py
│   │   ├── ml/
│   │   │   ├── features.py
│   │   │   ├── training.py
│   │   │   ├── evaluation.py
│   │   │   ├── inference.py
│   │   │   ├── registry.py
│   │   │   └── fallback.py
│   │   ├── integrations/
│   │   │   ├── supabase_client.py
│   │   │   ├── supabase_auth.py
│   │   │   ├── storage_client.py
│   │   │   ├── freight_data_client.py
│   │   │   ├── commodity_data_client.py
│   │   │   ├── weather_data_client.py
│   │   │   └── ports_data_client.py
│   │   └── utils/
│   │       ├── dates.py
│   │       ├── units.py
│   │       └── exporters.py
│   └── tests/
│       ├── unit/
│       │   ├── domain/
│       │   ├── services/
│       │   └── ml/
│       ├── integration/
│       ├── api/
│       └── fixtures/
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   ├── index.html
│   ├── .env.example
│   ├── public/
│   │   └── assets/
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── api/
│   │   │   ├── client.js
│   │   │   ├── supabase.js
│   │   │   ├── auth.js
│   │   │   ├── ports.js
│   │   │   ├── vessels.js
│   │   │   ├── routes.js
│   │   │   ├── forecasts.js
│   │   │   ├── recommendations.js
│   │   │   ├── scenarios.js
│   │   │   └── reports.js
│   │   ├── components/
│   │   │   ├── common/
│   │   │   ├── layout/
│   │   │   ├── planning/
│   │   │   ├── forecast/
│   │   │   ├── vessels/
│   │   │   ├── recommendation/
│   │   │   ├── scenarios/
│   │   │   └── reports/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Planning.jsx
│   │   │   ├── Forecast.jsx
│   │   │   ├── Scenarios.jsx
│   │   │   ├── Report.jsx
│   │   │   ├── Login.jsx
│   │   │   └── Admin.jsx
│   │   ├── layouts/
│   │   │   └── AppLayout.jsx
│   │   ├── hooks/
│   │   │   ├── useAuth.js
│   │   │   ├── useRecommendation.js
│   │   │   └── useScenario.js
│   │   ├── context/
│   │   │   └── AuthContext.jsx
│   │   ├── utils/
│   │   │   ├── formatters.js
│   │   │   ├── validators.js
│   │   │   └── constants.js
│   │   ├── styles/
│   │   │   ├── index.css
│   │   │   └── app.css
│   │   └── tests/
│   │       ├── components/
│   │       ├── pages/
│   │       └── api/
│   └── README.md
├── scripts/
│   ├── ingest_data.py
│   ├── validate_reference_data.py
│   ├── train_model.py
│   ├── evaluate_model.py
│   └── seed_database.py
└── infra/
    ├── Dockerfile.backend
    ├── Dockerfile.frontend
    ├── nginx/
    └── deployment/
```

## Folder Responsibilities

### `frontend/src/components/`
Contains reusable UI widgets and layouts only. Components receive values and callbacks or API-ready data; they do not import database modules, ORM models, or server secrets.

### `frontend/src/api/`
Contains frontend HTTP client wrappers. A React component or page calls an API module, which calls a backend API. These files must never connect directly to Supabase data tables, backend repositories, CSV reference stores, or model artifact stores. Supabase Auth is used only for identity/session operations.

### `backend/api/`
Contains HTTP endpoints, dependency injection, and response serialization. API handlers must delegate all business workflow logic to `backend/services/`.

### `backend/services/`
Contains use-case orchestration and persistence operations through repositories/Supabase data-access integrations. A service may call repositories and pure domain modules. It must not contain React rendering code.

### `backend/repositories/`
Contains all Supabase queries and persistence operations. Repositories do not decide business policy; they retrieve and store data.

### `backend/domain/`
Contains pure business logic. It must not import FastAPI, React, SQLAlchemy sessions, file clients, or HTTP clients.

### `backend/ml/`
Contains model-training and inference code. It should return stable domain-friendly structures rather than UI-specific chart data.

## Architectural Rules
These rules are mandatory for all contributors.

### Separation of concerns
1. **UI components must not contain database logic.** No SQL, ORM session, repository import, direct CSV/Parquet read, or database connection may appear in `frontend/` UI code.
2. **Database operations belong in backend services and repositories.** Services own use-case workflows; repositories own Supabase query/persistence details. API routes and UI components must not access Supabase data tables directly.
3. **Business logic must remain separate from UI.** Forecasting, vessel feasibility, cost calculation, ranking, and recommendations belong in `backend/domain/` and `backend/services/`, never in React components, pages, or render functions.
4. **Reusable UI belongs in `frontend/components/`.** Do not duplicate forms, charts, badges, cards, or tables across pages. Pages compose reusable components.
5. **API routes must remain thin.** Route handlers authenticate, validate, call a service, and serialize a response. They must not contain complex calculations, direct SQL, or large branching business rules.
6. **Domain logic must be framework-independent.** `backend/domain/` cannot import FastAPI, React, SQLAlchemy, pandas database readers, or external API clients.
7. **Model logic must be swappable.** Business services depend on a forecast interface, not on a particular model library or serialized model format.

### Authentication and security
8. **Authentication must use Supabase Auth and be verified server-side.** React may initiate Supabase Auth sign-in/sign-out and maintain the client session, but FastAPI verifies the Supabase access token on every protected request.
9. **Authorization must be enforced server-side.** Role checks occur in backend dependencies/services using the authenticated Supabase user/profile before returning protected data or modifying reference data.
10. **Never send secrets to the client.** Supabase service-role keys, database credentials, signing secrets, and vendor tokens remain in backend environment variables or secret managers. Only the public Supabase URL and publishable/anon client key may be exposed to React.
11. **Do not implement password storage in FastAPI.** Supabase Auth owns credential storage and authentication flows; the application stores only the profile/role data it needs.
12. **Validate all inputs at the API boundary.** Use typed schemas, allowed ranges, and controlled enumerations for ports, vessel classes, volumes, and dates.
13. **Log safely.** Do not write tokens, passwords, personally identifiable information, or confidential commercial terms to logs.

### Data and model governance
14. **Every external dataset must have provenance.** Store source, retrieval date, units, route/vessel context, and actual/proxy/simulated quality label.
15. **Do not silently manufacture data.** If data is unavailable, show a warning, use an explicit documented fallback, or fail safely.
16. **Keep raw data immutable.** Transformations create processed datasets; never overwrite raw source extracts.
17. **Version models and features.** Every forecast response records model version, data-as-of time, and feature/data version where possible.
18. **Separate training from inference.** Training scripts do not run automatically inside normal API request handling.
19. **Use time-aware evaluation.** Forecast validation must use chronological splits and avoid leakage from future observations.
20. **Expose assumptions.** Recommendations must carry the constraints, rates, scenario inputs, and uncertainty information used to generate them.

### Quality and testing
21. **Write unit tests for pure domain rules.** Test vessel feasibility, turnaround, cost calculation, ranking, and recommendation policy without requiring a database or UI.
22. **Write integration tests for services/repositories.** Verify data retrieval, persistence, authorization, and end-to-end workflows.
23. **Use contract tests for APIs.** Validate request/response schema compatibility between frontend and backend.
24. **No production data in source control.** Keep sensitive data, large model artifacts, and secrets out of Git.
25. **Fail visibly and safely.** Unsupported routes, outdated port data, missing models, and invalid inputs must produce clear errors/warnings instead of guessed recommendations.

## Dependency Direction
Dependencies should point inward toward stable business logic.

```text
Frontend UI -> Frontend API Client -> Backend API -> Services -> Domain
                                              |          |
                                              v          v
                                         Repositories   ML/Integrations
                                              |
                                              v
                                           Database
```

Allowed dependencies:
- React components/pages may depend on frontend API modules, hooks, context, and presentation utilities.
- API handlers may depend on schemas, auth dependencies, and application services.
- Services may depend on repositories, domain modules, ML interfaces, and integrations.
- Repositories may depend on Supabase data-access clients/integration modules only.
- Domain modules may depend only on standard library/shared typed domain structures.

Disallowed dependencies:
- Frontend/React UI to database/repositories.
- Domain to UI, API framework, database, or external network clients.
- Repositories to React/FastAPI route handlers.
- API handlers to direct Supabase data queries except controlled authentication/dependency setup.

## Error Handling
- Use structured error responses: `code`, `message`, `details`, and optional `trace_id`.
- Use domain-specific errors such as `UnsupportedRouteError`, `NoFeasibleVesselError`, `InsufficientDataError`, and `UnauthorizedError`.
- The backend maps internal errors to safe client-facing messages.
- The UI shows actionable errors and never exposes stack traces, secrets, or internal infrastructure details.

## Observability
### MVP
- Structured application logs.
- Request ID/trace ID for API calls.
- Record forecast model version, data-as-of date, and scenario inputs with a recommendation.
- Basic error monitoring and health endpoint.

### Production direction
- Metrics for latency, error rate, forecast failures, missing-data rate, and recommendation usage.
- Data-quality monitoring for stale or missing freight series and port parameters.
- Model drift/performance monitoring after actual outcomes become available.
- Audit logs for reference-data updates, exports, and sensitive planning actions.

## Deployment Architecture

### SIH MVP
```text
Browser
  -> React frontend
  -> Supabase Auth (identity/session)
  -> FastAPI backend
  -> Supabase PostgreSQL / Storage
  -> Redis cache (if enabled)
  -> Local/reference files + model artifacts
```

### Production target
```text
Users
  -> HTTPS Load Balancer / Reverse Proxy
  -> React Frontend Service
  -> Supabase Auth
  -> FastAPI Backend API Service
  -> Supabase PostgreSQL / Storage
  -> Redis Cache
  -> Scheduled data ingestion and model retraining jobs
  -> Licensed market-data and SAIL enterprise integrations
```

Production services should run in containers, receive configuration through environment variables or a secret manager, use managed database backups, and be protected by network controls and HTTPS.

## Development Workflow
1. Define or update request/response schema before changing UI behavior.
2. Implement or update pure domain logic with unit tests.
3. Add repository/service behavior with integration tests.
4. Expose it through a thin API endpoint.
5. Build/reuse UI components that call the API through frontend services.
6. Test the full workflow with representative and infeasible scenarios.
7. Update data dictionary, assumptions, and model card when data/model behavior changes.

## Definition of Done
A feature is complete only when:
- Its business rule is implemented outside the UI.
- Protected operations are authenticated and authorized server-side.
- Supabase data access is performed through services/repositories, not UI or route-handler queries.
- Input validation and error states are implemented.
- Unit/integration/API tests relevant to the change pass.
- Assumptions, source metadata, and user-facing explanations are visible where relevant.
- The feature does not expose secrets, commercial data, or raw internal errors.

