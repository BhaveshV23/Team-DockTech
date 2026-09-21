# System Architecture

## Product
**DockTech** is an intelligent freight forecasting and chartering decision-support system for bulk cargo procurement (specifically coal imports) to India’s East Coast ports. The system combines freight forecasting, vessel–berth feasibility checks, voyage-cost estimation, risk scenarios, and explainable chartering recommendations.

DockTech is designed strictly as a **decision-support platform**, not an automated charter execution system.

## Supabase Architecture
DockTech uses **Supabase as the managed data and identity platform**:
- **Supabase Auth** handles user identity, authentication, password security, and session management.
- **Supabase PostgreSQL** provides relational storage for both static/slowly-changing reference data and dynamic application data.
- **Supabase Storage** provides persistent object storage for generated decision summary reports (PDF/CSV) and report templates.
- **FastAPI** remains the authoritative backend for business logic, ML forecasting pipelines, two-ended vessel–berth feasibility checks, multi-voyage cost estimation, risk scenarios, recommendation heuristics, and server-side authorization.
- **React (Vite)** uses the Supabase client library exclusively for identity and session operations (sign-in, token refresh, sign-out).
- **React must NOT directly query application or reference tables in Supabase.** All application workflows and data queries flow through FastAPI APIs.
- **Supabase service-role credentials remain backend-only.** They are never exposed to the client or checked into source control.
- **FastAPI verifies Supabase access tokens server-side** on every protected request before delegating to application services.
- **Application roles (`VIEWER`, `PLANNER`, `MANAGER`, `ADMINISTRATOR`) are enforced server-side** in FastAPI dependencies and services.
- **Row Level Security (RLS)** in PostgreSQL provides defense-in-depth database protection, but is not a substitute for FastAPI application authorization.
- **Redis** is optional for response caching and performance-sensitive lookups, not a mandatory runtime dependency for MVP execution.

## Architecture Goals
- Keep business rules, calculations, and domain models completely independent of the user interface.
- Ensure all datasets, port limits, berth capabilities, vessel classes, fuel prices, and model artifacts are versioned, traceable, and swappable.
- Maintain strict referential integrity, reproducible cost baselines, and failure-safe behaviors across services.
- Deliver transparent, explainable recommendations with key drivers, material assumptions, and risk flags rather than opaque "black-box" predictions.
- Enforce strict separation between identity management (Supabase Auth), API orchestration / authorization (FastAPI), and persistent storage (Supabase PostgreSQL / Storage).

## System Context

The user interacts with the React frontend. Supabase Auth establishes identity and returns an access token (JWT). React attaches this token to API requests sent to FastAPI. The backend validates the token, verifies user authorization, loads data from Supabase PostgreSQL, runs forecasting and feasibility evaluations, executes scenario calculations, and returns a structured recommendation payload.

```text
+------------------------+        HTTPS API Calls       +---------------------------+
| Web Dashboard          | <--------------------------> | Backend API Service       |
| React + Vite           |     (Bearer JWT Auth)        | FastAPI                   |
+-----------+------------+                              +-------------+-------------+
            |                                                         |
            | Supabase Auth                                           |
            | login / session / JWT                                   |
            v                                                         |
+------------------------+                                            |
| Supabase Auth          | <------------------------------------------+
| Identity + Sessions    |      Server-side JWT Verification
+------------------------+                                            |
                                                                      |
                                     +--------------------------------+--------------------------------+
                                     |                                |                                |
                            +--------v---------+             +--------v---------+             +--------v---------+
                            | Auth & Role      |             | Application      |             | Forecast &       |
                            | Dependency Guard |             | Services         |             | Decision Engine  |
                            +------------------+             +--------+---------+             +--------+---------+
                                                                      |                                |
                                                       +--------------v--------------------------------+
                                                       | Repositories / Data Access Adapters           |
                                                       +----------------------+------------------------+
                                                                              |
                                                      +-----------------------v-----------------------+
                                                      | Supabase Managed Platform                     |
                                                      | PostgreSQL (Data) + Storage (Reports)         |
                                                      +-----------------------------------------------+
```

---

## Logical Layers

### 1. Presentation Layer (`frontend/`)
- **Technology:** React + Vite single-page application using modern Vanilla CSS design tokens.
- **Responsibilities:**
  - Render planning forms, forecast trend charts, vessel comparison cards, scenario adjusters, and downloadable reports.
  - Collect user procurement parameters (commodity, parcel volume, origin, destination, delivery window, preferred contract horizon).
  - Manage client-side session state via Supabase Auth client.
  - Invoke backend endpoints via typed API client wrappers.
  - Render explicit units, data freshness badges, assumptions panels, and structured error states.
- **Does NOT do:**
  - Direct SQL queries, ORM sessions, or Supabase PostgreSQL table reads.
  - Secret key or service-role credential storage.
  - Authorization decisions or role enforcement.
  - Domain feasibility checks, voyage duration modeling, or cost calculations.

### 2. API Layer (`backend/app/api/`)
- **Technology:** FastAPI REST router versioned under `/api/v1`.
- **Responsibilities:**
  - Define request and response schemas (Pydantic).
  - Authenticate incoming requests by verifying Supabase access tokens.
  - Enforce role-based access control (`VIEWER`, `PLANNER`, `MANAGER`, `ADMINISTRATOR`).
  - Validate payload constraints and enumerations at the boundary.
  - Delegate use cases to application services and serialize structured JSON responses.
- **Does NOT do:**
  - Embed complex forecasting heuristics, cost formulas, or database queries inside route handlers.
  - Handle UI presentation concerns.

### 3. Application / Service Layer (`backend/app/services/`)
- **Responsibilities:**
  - Orchestrate end-to-end business workflows.
  - Resolve derived dependencies (e.g. resolving a `cargo_request` to its unique `route_id`).
  - Coordinate repository queries to fetch reference constraints and time-series observations.
  - Trigger ML forecasting inference, vessel–berth feasibility filtering, cost/turnaround estimation, and recommendation ranking.
  - Record audit log events for governance and traceability.
- **Key Services:**
  - `RecommendationService`: End-to-end procurement and chartering recommendation workflow.
  - `ForecastService`: Model inference, prediction intervals, and baseline fallback execution.
  - `FeasibilityService`: Two-ended berth and port constraint verification.
  - `CostEngineService`: Multi-voyage turnaround, bunker fuel calculation, and freight hire estimation.
  - `ScenarioService`: Parameter shock evaluations (freight, bunker fuel, port delay).
  - `ReportService`: One-page decision brief generation.
  - `ReferenceDataService`: Ports, berths, vessel classes, and routes retrieval.
  - `AuditService`: Governance and operational action logging.

### 4. Domain / Business Layer (`backend/app/domain/`)
- **Responsibilities:**
  - Contain pure, framework-independent bulk maritime business logic.
  - **Two-Ended Feasibility Rules:** Check vessel dimensions against commodity-specific berth constraints at both loading and discharge ports.
  - **Multi-Voyage Planning:** Compute required voyages $\lceil \text{volume} / \text{capacity} \rceil$ and evaluate part-loading risks.
  - **Cost & Turnaround Formulas:** Compute laden sailing duration, berth handling time, port waiting time, VLSFO fuel consumption, and freight costs.
  - **Decision Heuristics:** Map forecast momentum, delivery deadlines, and uncertainty to market entry timing (`FIX_NOW` vs. `WAIT`) and contract strategy (`SPOT` vs. `SHORT_TERM_MULTIPLE_VOYAGE`).
- **Design Rule:** Pure Python functions and data classes. Zero dependencies on FastAPI, React, SQL, pandas database readers, or external network clients.

### 5. Repository & Data Access Layer (`backend/app/repositories/` & `integrations/`)
- **Responsibilities:**
  - Encapsulate all database queries and mutations against Supabase PostgreSQL.
  - Provide domain repository interfaces and implementations.
  - Maintain the single Supabase client adapter in `backend/app/integrations/`.
  - Handle connection management, transaction boundaries, and query filtering.
- **Does NOT do:**
  - Implement business policy, feasibility logic, or recommendation ranking.
  - Expose raw database connection objects to API controllers or UI components.

### 6. Data Science & Model Layer (`backend/app/ml/`)
- **Responsibilities:**
  - Time-series feature engineering (lags, rolling averages, seasonality indicators).
  - Train, backtest, and evaluate forecasting models (ARIMA, XGBoost, Naive persistence baseline).
  - Model registry metadata tracking (`model_name`, `model_version`, `training_data_end_date`).
  - Generate quantitative prediction intervals (`central_value`, `lower_value`, `upper_value`).
  - Provide safe fallback baseline predictions when history is sparse or advanced models fail.

---

## Important Domain Relationships & Feasibility Hierarchy

### Feasibility Hierarchy
DockTech enforces a strict three-tier physical constraint hierarchy:

```text
Port Planning Envelope (Screening Layer)
       ↓
Berth Physical & Commodity Limits (Authoritative Operational Layer)
       ↓
Commodity-Specific Vessel Feasibility (Origin AND Destination)
```

1. **`ports` (Planning Envelope):** Defines macro-level maximum limits (`max_loa_m`, `max_beam_m`, `max_draft_m`). Serves as an early screening layer. It does **not** guarantee berth feasibility.
2. **`berths` (Authoritative Operational Layer):** Defines actual terminal physical constraints and commodity specialization (`commodity = 'THERMAL_COAL' | 'COKING_COAL'`). A vessel is feasible at a port if and only if at least one berth handling the requested commodity can accommodate the vessel's LOA, beam, and draft.
3. **Two-Ended Feasibility Rule:** A vessel class is operationally feasible if and only if it is compatible at **both** the origin loading port and destination discharge port.
4. **No Invented Compatibility:** If a port has no berth record for the requested commodity, the engine must fail safely with `INSUFFICIENT_FEASIBILITY_DATA` rather than inventing a generic berth.
5. **Recommendation Integrity:** The recommendation engine must **never** recommend a vessel class rejected by feasibility.

### Supporting Reference Data Roles
- **`port_activity`:** Supplies time-varying observed waiting hours and congestion ratings. In V1, waiting hours for cost estimation are strictly queried from `port_activity.average_waiting_hours` on or before the cost reference date.
- **`fuel_prices`:** Supplies bunker fuel market prices. Sea-going transit fuel cost is calculated using **VLSFO only**, retrieved on or before the cost reference date.
- **`scenario_defaults`:** Supplies predefined parameter shock presets (`BASELINE`, `ADVERSE`, `FAVORABLE`).

---

## Cost & Turnaround Architecture (V1 Semantics)

Detailed mathematical formulas are defined in `DATA_DICTIONARY.md`. At the architectural level, the cost and operational engines adhere to these core principles:

1. **Multi-Voyage Parcel Handling:**
   - When requested cargo volume exceeds vessel payload capacity, the engine calculates:
     $$\text{required\_voyages} = \left\lceil \frac{\text{cargo\_volume\_mt}}{\text{cargo\_capacity\_mt}} \right\rceil$$
   - Total shipment turnaround (`recommendations.estimated_turnaround_hours`) accounts for handling total cargo volume across berths plus waiting time and scenario delays on **every voyage call**.
2. **Definition of Vessel-Days & Port-Days:**
   - Per-voyage turnaround hours are converted to port days:
     $$\text{port\_days\_per\_voyage} = \frac{\text{turnaround\_hours\_per\_voyage}}{24}$$
     $$\text{vessel\_days\_per\_voyage} = \text{sailing\_days} + \text{port\_days\_per\_voyage}$$
3. **Freight Hire vs. Total Cost:**
   - **`USD_PER_DAY` Freight:** Waiting and handling times directly expand `port_days_per_voyage` and `vessel_days_per_voyage`, and are therefore accounted for within charter hire freight cost.
   - **`USD_PER_MT` Freight:** Waiting time impacts turnaround duration, delivery window feasibility, and operational risk (`risk_level`), but V1 does **not** calculate an arbitrary separate idle/demurrage monetary charge because no explicit demurrage-rate parameter exists in the V1 schema. Total cost must not invent uncalibrated idle charges.
4. **Reproducible Cost Reference Date:**
   - All reference observations for bunker fuel (VLSFO) and port waiting times use a deterministic cost reference date:
     $$\text{cost\_reference\_date} = \text{forecast\_run}.\text{training\_data\_end\_date}$$
   - This ensures cost estimates and recommendations are 100% reproducible and independent of the execution timestamp.

---

## Core Domain Data Model

The data contract is canonically specified in `DATA_DICTIONARY.md`. ARCHITECTURE.md summarizes the entities and their architectural responsibilities:

### 1. Reference Datasets (Seeded from `data/reference/*.csv`)
| Entity / Dataset | Architectural Role | Key Attributes |
|---|---|---|
| `Port` / `ports` | Macro port planning envelope & baseline turnaround | `port_id`, `port_name`, `country`, `max_loa_m`, `max_beam_m`, `max_draft_m`, `handling_rate_tpd`, `typical_turnaround_hours`, `source`, `data_type` |
| `Berth` / `berths` | Authoritative physical & commodity constraints | `berth_id`, `port_id`, `berth_name`, `commodity`, `max_loa_m`, `max_beam_m`, `max_draft_m`, `handling_rate_tpd`, `source`, `data_type` |
| `VesselClass` / `vessel_classes` | Vessel catalog, dimensions, capacity, fuel burn | `vessel_class_id`, `vessel_class_name`, `dwt_min_mt`, `dwt_max_mt`, `loa_m`, `beam_m`, `draft_m`, `speed_knots`, `cargo_capacity_mt`, `fuel_consumption_mt_day`, `source`, `data_type` |
| `Route` / `routes` | Trade lanes, nautical distance, baseline days | `route_id`, `origin_port_id`, `destination_port_id`, `commodity`, `distance_nm`, `typical_sailing_days`, `source`, `data_type` |
| `FreightRate` / `freight_rates` | Historical/synthetic freight rates for ML & trends | `freight_rate_id`, `observation_date`, `route_id`, `vessel_class_id`, `freight_value`, `freight_unit`, `currency`, `source`, `data_type` |
| `CommodityPrice` / `commodity_prices` | Macro coal benchmark prices for market context | `commodity_price_id`, `observation_date`, `commodity`, `market`, `price_value`, `currency`, `unit`, `source`, `data_type` |
| `FuelPrice` / `fuel_prices` | Marine bunker fuel prices (VLSFO, MGO) | `fuel_price_id`, `observation_date`, `fuel_type`, `price_value`, `currency`, `unit`, `source`, `data_type` |
| `PortActivity` / `port_activity` | Observed waiting hours and daily congestion | `activity_id`, `observation_date`, `port_id`, `vessel_arrivals`, `average_waiting_hours`, `average_turnaround_hours`, `congestion_level`, `source`, `data_type` |
| `ScenarioDefault` / `scenario_defaults` | Presets for scenario evaluation | `scenario_id`, `scenario_name`, `freight_change_pct`, `fuel_change_pct`, `delay_hours`, `port_congestion_level`, `description`, `source`, `data_type` |

### 2. Application Tables (Managed in Supabase PostgreSQL at Runtime)
| Entity / Table | Architectural Role | Key Attributes |
|---|---|---|
| `UserProfile` / `user_profiles` | Profile linked to Supabase Auth `auth.users` | `user_id`, `auth_user_id`, `display_name`, `email`, `role`, `created_at`, `updated_at` |
| `CargoRequest` / `cargo_requests` | User shipment procurement requirement | `cargo_request_id`, `user_id`, `commodity`, `cargo_volume_mt`, `origin_port_id`, `destination_port_id`, `earliest_delivery_date`, `latest_delivery_date`, `contract_horizon`, `created_at` |
| `ForecastRun` / `forecast_runs` | ML execution run metadata, model version, unit | `forecast_run_id`, `cargo_request_id`, `route_id`, `vessel_class_id`, `freight_unit`, `model_name`, `model_version`, `training_data_end_date`, `created_at` |
| `ForecastPoint` / `forecast_points` | Quantitative time-series predictions & bounds | `forecast_point_id`, `forecast_run_id`, `forecast_date`, `central_value`, `lower_value`, `upper_value`, `unit` |
| `Scenario` / `scenarios` | User-adjusted scenario simulations & cost outputs | `scenario_instance_id`, `cargo_request_id`, `scenario_type`, `freight_change_pct`, `fuel_change_pct`, `delay_hours`, `congestion_level`, `estimated_total_cost`, `risk_level`, `created_at` |
| `Recommendation` / `recommendations` | Decision-support chartering output & rationale | `recommendation_id`, `cargo_request_id`, `forecast_run_id`, `recommended_vessel_class_id`, `market_entry_action`, `contract_strategy`, `expected_freight_cost`, `expected_total_cost`, `estimated_turnaround_hours`, `risk_level`, `confidence`, `rationale`, `assumptions`, `created_at` |
| `AuditLog` / `audit_logs` | Traceable governance and compliance event log | `audit_log_id`, `user_id`, `action`, `entity_type`, `entity_id`, `details`, `created_at` |

### 3. Entity Relationships
```text
ports (origin) ───────┐
                      ├──→ routes ────→ freight_rates
ports (destination) ──┘        │               ↑
                               │         vessel_classes
ports ──→ berths               │               │
ports ──→ port_activity        │               │
                               ↓               ↓
                    cargo_requests ──→ forecast_runs ──→ forecast_points
                         │                    │
                         ├──→ scenarios       │
                         │                    │
                         └──→ recommendations ←┘
                               ↑
                         vessel_classes

user_profiles ──→ cargo_requests
user_profiles ──→ audit_logs
```

---

## Synthetic Data Architecture & Provenance

To support development, testing, and SIH demonstration without relying on inaccessible real-world commercial data feeds, V1 uses synthetic reference datasets.

```text
Synthetic Data Generator (scripts/generate_synthetic_data.py)
        ↓
data/reference/*.csv (Version-controlled CSV seeds)
        ↓
Validation Suite (scripts/validate_reference_data.py)
        ↓
Database Seeder (scripts/seed_database.py)
        ↓
Supabase PostgreSQL Reference Tables
        ↓
FastAPI Repositories & Application Services
        ↓
Domain Feasibility, ML Forecasting, & Decision Engine
```

### Governance Rules for Synthetic Data:
1. **Provenance Metadata:** Every synthetic record carries `source = 'SYNTHETIC_GENERATOR_V1'` and `data_type = 'SYNTHETIC'`.
2. **No False Authority:** Synthetic constraints, route distances, handling rates, and freight rates must never be presented in the UI or documentation as official port limits or certified market quotes.
3. **Seamless Transition Path:** The database schema and repository interfaces are designed so that future actual feeds (e.g. Baltic Exchange indices, Clarksons data, live port notices) can be ingested with `data_type = 'ACTUAL'` or `'PROXY'` without modifying any table schema, column names, or foreign keys.

---

## Target Folder Structure

```text
docktech/
├── README.md
├── PRD.md
├── ARCHITECTURE.md
├── DESIGN.md
├── RULES.md
├── DATA_DICTIONARY.md
├── .env.example
├── .gitignore
│
├── data/
│   ├── reference/
│   │   ├── ports.csv
│   │   ├── berths.csv
│   │   ├── vessel_classes.csv
│   │   ├── routes.csv
│   │   ├── freight_rates.csv
│   │   ├── commodity_prices.csv
│   │   ├── fuel_prices.csv
│   │   ├── port_activity.csv
│   │   └── scenario_defaults.csv
│   └── README.md
│
├── models/
│   ├── artifacts/
│   └── metadata/
│
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
│   │   │   ├── berth_repository.py
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
│
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
│
├── scripts/
│   ├── generate_synthetic_data.py
│   ├── validate_reference_data.py
│   ├── seed_database.py
│   ├── train_model.py
│   └── evaluate_model.py
│
└── infra/
    ├── Dockerfile.backend
    ├── Dockerfile.frontend
    └── deployment/
```

---

## Folder Responsibilities

### `backend/app/api/`
FastAPI route controllers. Thin handlers responsible for HTTP parameter mapping, dependency injection, authentication verification, request schema validation, and response serialization. Delegates all business workflows to `services/`.

### `backend/app/schemas/`
Pydantic data validation schemas for incoming requests and serialized responses. Enforces strict types, bounds, and controlled vocabulary enumerations at the API boundary.

### `backend/app/domain/`
Core bulk chartering business models, feasibility matrices, cost calculation engines, multi-voyage estimators, ranking heuristics, and risk models. Pure Python, testable without network, database, or UI dependencies.

### `backend/app/services/`
Application use-case coordinators. Manages transactions, fetches required constraints from repositories, triggers domain calculations, calls ML inference pipelines, constructs recommendation outputs, and writes audit records.

### `backend/app/repositories/`
Persistence abstractions managing queries to Supabase PostgreSQL. Enforces relational integrity, handles parameterized filtering, and converts persistence rows to domain objects.

### `backend/app/integrations/`
**Exactly one integrations directory** containing infrastructure adapters:
- `supabase_client.py`: Singleton Supabase PostgreSQL client initialization.
- `supabase_auth.py`: Server-side JWT token validation and public key verification.
- `storage_client.py`: Supabase Storage adapter for report artifact persistence.
External live ingestion clients (weather, AIS, live broker feeds) are deferred and excluded from the active V1 tree.

### `backend/app/ml/`
Machine learning forecasting sub-system. Contains feature engineering, model training routines, evaluation scripts, runtime inference logic, model registry metadata management, and baseline persistence fallback models.

### `frontend/src/`
React + Vite presentation layer:
- `api/`: Typed HTTP client wrappers calling FastAPI endpoints. Does not access Supabase tables directly.
- `components/`: Reusable, modular UI widgets (charts, tables, parameter forms, badges, alert cards).
- `pages/`: Page-level route views composing layout and domain components.
- `context/` & `hooks/`: Authentication state management (via Supabase Auth client) and custom data hooks.
- `styles/`: Canonical design system tokens and responsive styles (Vanilla CSS).

---

## API Design

All endpoints are versioned under `/api/v1`. Route handlers remain thin, delegating execution to the appropriate service.

| Endpoint | Method | Purpose | Required Role |
|---|---:|---|---|
| `/auth/me` | GET | Return current authenticated user profile & role | Authenticated |
| `/ports` | GET | List supported ports and planning constraints | Authenticated |
| `/vessels` | GET | List vessel classes and technical specifications | Authenticated |
| `/routes` | GET | List supported origin–destination trade lanes | Authenticated |
| `/forecasts` | POST | Generate freight rate forecast for route & vessel class | `PLANNER`, `MANAGER`, `ADMINISTRATOR` |
| `/recommendations` | POST | Run full feasibility, cost ranking, and chartering recommendation | `PLANNER`, `MANAGER`, `ADMINISTRATOR` |
| `/scenarios/evaluate` | POST | Evaluate recommendation sensitivity under parameter shocks | `PLANNER`, `MANAGER`, `ADMINISTRATOR` |
| `/reports/recommendation` | POST | Generate downloadable decision summary brief | `PLANNER`, `MANAGER`, `ADMINISTRATOR` |
| `/admin/ports` | POST/PATCH | Manage port reference constraints | `ADMINISTRATOR` |
| `/admin/vessels` | POST/PATCH | Manage vessel class reference specifications | `ADMINISTRATOR` |

---

## Architectural Rules

1. **Separation of Concerns:** UI components must never contain SQL queries, repository calls, direct Supabase table queries, or secret keys.
2. **FastAPI Authorization Boundary:** React uses Supabase Auth for login, but FastAPI verifies the Supabase access token server-side on every protected API call and enforces application roles (`VIEWER`, `PLANNER`, `MANAGER`, `ADMINISTRATOR`).
3. **No Direct UI Database Access:** The React frontend must never read or write Supabase PostgreSQL application or reference tables directly. All queries pass through FastAPI.
4. **Thin Route Handlers:** API routes only authenticate, validate inputs via Pydantic, call a service, and serialize outputs.
5. **Framework-Independent Domain Logic:** `backend/app/domain/` must never import FastAPI, React, SQLAlchemy sessions, or HTTP clients.
6. **Swappable ML Models:** Business services interact with the forecasting engine through a unified interface (`ForecastService`), enabling seamless model updates without API contract changes.
7. **Two-Ended Feasibility Precedence:** Port constraints serve as an initial screening envelope, but berth constraints are authoritative. A vessel must have at least one compatible berth for the requested commodity at both origin and destination.
8. **Multi-Voyage Cost Accounting:** Calculations must account for required voyages ($\lceil \text{volume} / \text{capacity} \rceil$). For `USD_PER_DAY` rates, turnaround and waiting time expand vessel days and charter hire cost; for `USD_PER_MT`, waiting impacts risk and turnaround, but no artificial idle cost is fabricated.
9. **Reproducible Reference Dates:** Cost estimations and reference-data lookups use `cost_reference_date = forecast_run.training_data_end_date` for deterministic reproducibility.
10. **Data Provenance:** Every reference record must carry `source` and `data_type`. Synthetic data must never be presented as official commercial figures.
11. **Fail-Safe Behavior:** Missing routes, missing berths, missing fuel prices, or sparse freight histories must produce structured errors (e.g., `ERROR_ROUTE_NOT_FOUND`, `INSUFFICIENT_FEASIBILITY_DATA`, `ERROR_INSUFFICIENT_FUEL_PRICE_DATA`) rather than hallucinated estimates.
12. **Secret Isolation:** Supabase service-role keys, database passwords, and JWT secrets reside exclusively in backend environment variables. React only receives the public Supabase URL and anon client key.
13. **Input Validation:** All inputs at the API boundary are validated against strict Pydantic schemas and controlled enumerations.
14. **Safe Logging:** Never write passwords, auth tokens, personally identifiable information, or commercial secrets to application logs.
15. **Explicit Units:** All numeric values must be accompanied by explicit units matching `DATA_DICTIONARY.md`.
16. **No Production Data in Version Control:** Never commit secrets, real fixture contracts, or heavy binary model artifacts into Git.
17. **Time-Aware ML Splits:** Model training and evaluation must use chronological train/validation splits to prevent future-data leakage.
18. **Explainability First:** Every recommendation must return plain-language rationale, key decision drivers, material assumptions, and risk ratings.
19. **Unit Test Coverage:** Pure domain rules (feasibility, multi-voyage cost, ranking heuristics) must be covered by comprehensive unit tests requiring no database or network.
20. **Integration Testing:** Service and repository workflows must be validated using integration tests against test databases.
21. **Single Integrations Adapter:** Infrastructure integrations must be centralized in a single `backend/app/integrations/` directory.
22. **No Overengineered Infrastructure in V1:** Weather routing, real-time AIS telemetry, live broker messaging, and production temporal port notice tables are deferred to future roadmap phases.
23. **Idempotent Data Seeding:** Database seeding scripts must support upsert operations to allow safe, repeatable execution in development and staging environments.
24. **Structured Error Schema:** API errors return standardized payloads containing `code`, `message`, and optional `details`.
25. **Single Source of Truth:** `PRD.md` defines product requirements; `DATA_DICTIONARY.md` defines schemas, units, and formulas; `ARCHITECTURE.md` defines software structure and layer interactions.

---

## Deployment Architecture

### SIH MVP Architecture
```text
User Browser
    ↓
React + Vite Frontend (SPA)
    ↓
Supabase Auth (Identity & JWT Session)
    ↓
FastAPI Backend API (Business Logic & ML Orchestration)
    ↓
Supabase Managed Platform (PostgreSQL Data & Storage Artifacts)
    ↓
Optional Redis Cache (Performance optimization, if enabled)
```

- **Seed Data & Artifacts:** Version-controlled reference CSVs (`data/reference/*.csv`) and model metadata (`models/metadata/`) reside in the repository and are deployed with backend/data services.
- **Secrets Management:** Managed exclusively through environment variables (`.env`).

### Production Direction
In future production deployments:
- Containerized deployment using Docker across services (`Dockerfile.backend`, `Dockerfile.frontend`).
- Reverse proxy / load balancer terminating HTTPS.
- Managed Supabase Enterprise project with automated daily backups and point-in-time recovery.
- Scheduled asynchronous background workers for data ingestion and model retraining.
- Enterprise SSO/OIDC integration through Supabase Auth.

---

## Definition of Done
A feature or pull request is complete only when:
- Its business logic is implemented in `backend/app/domain/` or `services/`, completely outside UI rendering.
- Protected operations are verified server-side through FastAPI dependencies.
- Supabase queries are encapsulated in repositories and use parameterization.
- Pydantic request and response schemas are strictly defined.
- Applicable unit and integration tests pass.
- Assumptions, units, and provenance labels are transparently presented to the user.
- No secrets, credentials, or uncalibrated synthetic data are exposed.
