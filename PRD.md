# Product Requirements Document (PRD)

## Product
**DockTech** — Intelligent Freight Forecasting and Chartering Decision Support System

**Problem Statement ID:** 26006  
**Organization:** Ministry of Steel / SAIL  
**Theme:** Transportation & Logistics

## Document Purpose
This PRD defines the first-version product requirements for an AI-assisted decision-support platform for bulk-cargo vessel chartering to India’s East Coast ports. It is designed as an SIH 2026 MVP and provides a clear path to production-scale deployment.

## Technical Architecture Decision
For the SIH MVP, the product uses **Supabase as the managed data and identity platform**:
- **Supabase PostgreSQL** stores application, reference, scenario, and recommendation data.
- **Supabase Auth** handles authentication and authenticated sessions.
- **Supabase Storage** can store generated reports or uploaded files.
- **FastAPI** remains the core backend for business logic, forecasting, vessel-port feasibility, cost/risk calculations, recommendation logic, and server-side authorization.
- **React** remains the frontend and communicates with FastAPI APIs for application data.
- **Redis** remains optional for caching and performance-sensitive operations.

The frontend must not directly access application database tables for core product workflows; protected application operations go through FastAPI.

## Problem
SAIL’s bulk-cargo chartering decisions are often based on daily market exploration, broker inputs, spreadsheets, and manual experience. This reactive approach makes it difficult to predict freight-rate movement, identify favorable contracting windows, select a vessel that is compatible with both origin and destination port constraints, and avoid costly waiting or idle time.

For cargoes such as thermal coal and coking coal sourced from Australia, the US, Mozambique, Indonesia, and Russia, each origin–destination pair has different voyage economics, vessel availability, weather exposure, and port restrictions. India’s East Coast ports have different draft, LOA, beam, berth, and cargo-handling limits. Selecting an unsuitable vessel can result in part-loading, delayed berthing, additional port stay, and higher effective freight cost per tonne.

The product must help move decision-making from repeated single spot-voyage contracting to proactive short-/medium-term multi-voyage planning.

## Target Users
### Primary user: Chartering / vessel procurement manager
- Monitors freight markets and negotiates with brokers or shipowners.
- Needs a recommendation on market-entry timing, vessel type, expected cost, and contract approach.

### Secondary users
- **Logistics and supply-chain planners:** align cargo arrivals with plant consumption, inventory, and production plans.
- **Port and terminal coordinators:** validate vessel compatibility, berth feasibility, and expected turnaround.
- **Management approvers:** review savings, risks, and the rationale before approving chartering strategy.

## Goal
Provide a usable dashboard that forecasts freight trends, recommends feasible vessel classes, compares chartering options, and highlights risk for selected bulk-cargo routes into India’s East Coast.

### Product outcomes
- Reduce dependence on reactive, manual daily rate checks.
- Improve the timing of chartering decisions.
- Avoid infeasible vessel–port combinations.
- Reduce expected waiting, idle time, and effective logistics cost per tonne.
- Support evidence-based movement toward short-/medium-term multi-voyage contracts or Contracts of Affreightment (COA).

## Users’ Jobs To Be Done
- When I have a cargo requirement, I want to know the expected freight-rate direction so I can decide whether to fix now or wait.
- When I select an origin, destination, and parcel size, I want to know which vessel types can legally and operationally call at both ports.
- When I compare contract strategies, I want to see expected cost and downside risk so I can justify my recommendation.
- When congestion or freight volatility rises, I want an early warning and an operational alternative.

## Core Features

### 1. Freight-rate forecasting
- Forecast freight-rate movement for selected vessel classes and trade lanes.
- Support 7-, 30-, and 90-day forecast horizons in the MVP.
- Display a central forecast and a low/base/high range to communicate uncertainty.
- Show recent historical trend alongside the forecast.

### 2. Market-entry recommendation
- Compare three actionable choices: **fix now**, **wait**, and **consider a short-term/multi-voyage contract**.
- Produce a recommendation based on forecast direction, uncertainty, delivery window, and cost comparison.
- Explain the key drivers in plain language, such as rising rate momentum, seasonal risk, or congestion.

### 3. Vessel–port feasibility and vessel recommendation
- Maintain a structured catalogue of vessel-class specifications: capacity/DWT range, typical draft, LOA, beam, speed, and cargo capability.
- Maintain port constraints for selected origin and destination ports: maximum draft, LOA, beam, handling rate, and indicative waiting time.
- Reject infeasible vessel options automatically.
- Rank feasible vessels using estimated cost per tonne, cargo fit, turnaround time, and congestion/idle risk.

### 4. Cost and turnaround estimator
- Estimate voyage duration from route distance and vessel speed assumptions.
- Estimate port handling time using cargo quantity and handling-rate assumptions.
- Include a waiting-time assumption and optional demurrage/idle cost.
- Present estimated total cost and effective cost per tonne by vessel option.

### 5. Risk and scenario analysis
- Provide baseline, adverse, and favorable scenarios.
- Include user-adjustable freight-rate shock and congestion-delay inputs.
- Flag risks such as high forecast uncertainty, port mismatch, high congestion, and delivery-window risk.

### 6. Decision dashboard and report
- Accept user inputs for commodity, cargo volume, origin, destination, required delivery window, and intended contract duration.
- Display forecast chart, recommendation, vessel comparison, assumptions, cost range, and risks in one view.
- Generate a downloadable one-page decision summary for internal review.

## MVP Scope
The MVP proves the complete decision flow for a limited set of representative routes, ports, vessel classes, and one primary cargo category.

### MVP coverage
- **Cargo:** thermal coal and/or coking coal.
- **Origin ports/routes:** at least two representative routes, such as Australia (Newcastle) to Paradip and Indonesia to Vizag.
- **Destination ports:** 2–3 East Coast ports, such as Paradip, Vizag, and Gangavaram.
- **Vessel classes:** Panamax/Kamsarmax, Supramax/Ultramax, and Capesize where port assumptions permit.
- **Forecast data:** historical/open/proxy freight-index data, with clearly labeled assumptions where route-specific commercial data is unavailable.

### MVP user flow
1. User selects origin, destination, commodity, cargo volume, delivery window, and preferred contract horizon.
2. System validates vessel–port feasibility.
3. System displays 30-/90-day freight forecast and uncertainty range.
4. System compares feasible vessels by capacity fit, turnaround, estimated cost per tonne, and risk.
5. System recommends a timing action and contract approach.
6. User adjusts a scenario such as a rate shock or added port delay.
7. User downloads a concise recommendation report.

## Functional Requirements
| ID | Requirement | Priority |
|---|---|---|
| FR-01 | Allow a user to enter commodity, cargo volume, origin, destination, delivery window, and contract horizon through the React interface. | Must |
| FR-02 | Store selected-port infrastructure constraints and selected-vessel specifications in the backend data layer. | Must |
| FR-03 | Filter vessel classes using origin and destination draft, LOA, and beam constraints. | Must |
| FR-04 | Forecast selected freight-rate series for 7, 30, and 90 days. | Must |
| FR-05 | Display historical trend, predicted trend, and low/base/high forecast range in the React interface. | Must |
| FR-06 | Estimate voyage time, port-handling time, waiting time, and cost per tonne. | Must |
| FR-07 | Recommend vessel type and entry decision with an explainable rationale. | Must |
| FR-08 | Allow scenario adjustments for freight shock and additional congestion delay in the React interface. | Must |
| FR-09 | Show key assumptions, data recency, and warning flags clearly in the React interface. | Must |
| FR-10 | Export a decision summary as PDF or CSV, or provide a screen-ready report view if export is implemented through the backend. | Should |
| FR-11 | Preserve a history of user scenarios and expose it through the UI when the backend supports it. | Could |
| FR-12 | Support role-based access through Supabase Auth and application roles; integrate enterprise SSO/OIDC where required. | Future |

## Recommendation Logic
The product recommendation is decision support, not autonomous charter execution.

### Vessel selection
1. Filter out a vessel if its draft, LOA, or beam exceeds a constraint at either port.
2. Calculate required voyages or part-loading risk for the cargo quantity.
3. Estimate sailing and port turnaround time.
4. Estimate total cost using freight/hire proxy, port-time cost, and waiting/idle cost.
5. Rank feasible options by expected cost per tonne, delivery feasibility, and risk.

### Market-entry decision
- **Fix now:** recommended when forecast indicates a likely increase, uncertainty is high, or delivery urgency makes waiting costly.
- **Wait:** recommended when a likely reduction outweighs the estimated waiting risk and delivery window remains feasible.
- **Short-/medium-term multi-voyage / COA:** recommended when recurring requirements and expected volatility make price certainty and capacity assurance valuable.

## Data Requirements
### Required MVP datasets
- Historical freight index or route-rate proxy by vessel class and date.
- Commodity-price proxy, such as coal price, where available.
- Bunker-fuel proxy, where available.
- Static vessel-class specifications.
- Static port-constraint and handling-rate dataset for selected ports.
- Route distances and base voyage-speed assumptions.
- Indicative waiting-time or congestion assumptions.

### Data quality rules
- Every data point must retain source, date, unit, and whether it is actual, proxy, or simulated.
- The dashboard must label proxy or simulated values.
- Missing values must be imputed transparently or excluded with a visible warning.
- Port constraints must be editable by an authorized administrator in a future production version, with changes stored and audited in Supabase PostgreSQL.

## Model Requirements
### Forecasting
- Establish a baseline model, such as naive persistence, moving average, or seasonal model.
- Train at least one improved model, such as ARIMA/Prophet or gradient-boosting regression with lagged features.
- Use time-ordered train/validation/test splits; never randomly shuffle time series.
- Evaluate with MAE and MAPE/RMSE where meaningful, plus directional accuracy.
- Generate an uncertainty range through quantile forecasting, ensemble spread, or scenario bounds.

### Explainability
- Show the user the forecast trend, recent movement, confidence/risk level, and material assumptions.
- Do not present recommendations as certain; display uncertainty and constraints.

## Non-Functional Requirements
### Usability
- A non-technical chartering user must be able to obtain a recommendation within five minutes.
- Important warnings must be visually prominent and understandable without data-science knowledge.

### Performance
- A single recommendation scenario should load within 5 seconds in a demo environment.
- Forecast/model inference should complete within 10 seconds for an MVP request.

### Reliability
- The app must fail safely when a route, port, or data series is unavailable; it should show a clear message rather than invent a result.
- All calculations must expose assumptions used in the result.

### Security and governance
- The MVP contains no sensitive live procurement data.
- The MVP uses Supabase Auth for authentication and session management. Production design should support role-based access, encrypted data storage, audit logs, and SAIL IT-policy compliance.

### Maintainability
- Separate code modules for data loading, forecasting, port/vessel feasibility, cost calculation, recommendation rules, and React UI.
- Store operational and reference data in Supabase PostgreSQL, with version-controlled CSV/JSON seed files where reproducible initialization or fallback data is required.

## Out of Scope for Version 1
- Coverage of every origin port, Indian East Coast port, commodity, and vessel subtype.
- Paid, real-time data feeds from Baltic Exchange, Clarksons, broker platforms, or AIS vendors.
- Automated vessel booking, tender publishing, broker negotiation, or contract execution.
- Direct integration with SAIL ERP, procurement, tendering, or contract-management systems.
- Fleet-wide optimization involving many vessels, many cargo parcels, backhaul matching, and global repositioning.
- Advanced news-sentiment or geopolitical-event NLP.
- Production-grade high availability, full SSO, and enterprise-scale access control.

## Assumptions
- The MVP uses openly available, historical, proxy, or simulated data where commercial freight data cannot be licensed.
- Users will treat system outputs as decision support and validate commercial terms through standard procurement and broker processes.
- Port parameters are representative planning constraints and must be validated against current port notices before live chartering decisions.
- Cost estimates are comparative planning estimates, not binding freight quotations.

## Key Risks and Mitigations
| Risk | Impact | Mitigation |
|---|---|---|
| Route-specific commercial freight data is unavailable | Forecast may be less precise | Use vessel-class indices/proxies; clearly label assumptions; design connectors for licensed data later. |
| Port constraints change due to tide, maintenance, or notices | Incorrect feasibility recommendation | Store constraints separately, show data date, add validation warning, and support updates. |
| External shocks cause structural breaks in freight markets | Forecast error increases | Use uncertainty ranges, scenario analysis, retraining, and human review. |
| Model appears overly authoritative | Poor decision-making | Provide explanations, confidence/risk labels, and explicit decision-support disclaimer. |
| Too much scope for hackathon timeline | Incomplete demo | Limit routes, ports, vessel types, and scenarios; prioritize end-to-end usability. |

## Success Criteria
### MVP demo success
- A user can complete the full input-to-recommendation workflow for at least two routes and two destination ports.
- The system produces a forecast, vessel feasibility result, cost comparison, timing recommendation, and risk scenario in one session.
- The system rejects at least one deliberately infeasible vessel–port combination with a clear reason.
- The system shows a meaningful comparison between at least two feasible vessel options.
- The dashboard generates a usable recommendation report.

### Model success
- Improved forecasting model matches or beats the selected baseline on a held-out time-period metric.
- Forecast output includes a transparent uncertainty band or low/base/high range.
- Back-testing is documented with dates, data source, metric values, and limitations.

### User-value success
- A chartering/logistics reviewer can identify the recommended vessel and recommended market action without reading code or raw data.
- Demo users can explain why the recommendation was made using visible assumptions and drivers.
- The demo demonstrates a plausible lower-cost or lower-risk choice compared with a baseline spot-only decision.

## Metrics
| Metric | Definition | MVP Target |
|---|---|---|
| Forecast MAE/MAPE | Error on held-out historical periods | Improve over baseline; report actual value transparently |
| Directional accuracy | Percentage of correctly predicted up/down movement | Report and compare with baseline |
| Feasibility validation | Correct handling of predefined vessel–port test cases | 100% of curated test cases |
| Scenario response time | Time for UI to recompute scenario output | Under 5 seconds |
| End-to-end task completion | Ability to complete a recommendation workflow | Under 5 minutes |
| Recommendation explainability | Output includes visible rationale and assumptions | 100% of results |

## Proposed Technical Architecture
- **Frontend layer:** React dashboard for the SIH demo, communicating with the backend through APIs. Supabase Auth client integration is used for sign-in/sign-out and authenticated session handling.
- **Backend/API layer:** FastAPI for request validation, server-side Supabase access, business workflows, authorization, forecasting orchestration, feasibility, cost calculation, scenario evaluation, and recommendation generation.
- **Data layer:** Supabase PostgreSQL for freight series, commodity/fuel proxies, vessel specs, ports, routes, scenarios, user profiles, and recommendation history. Supabase Storage may be used for generated reports and uploaded files.
- **Authentication layer:** Supabase Auth for user identity and session management. FastAPI verifies Supabase access tokens and enforces application roles server-side.
- **Model layer:** Python forecasting pipeline using pandas, scikit-learn/statsmodels/Prophet or XGBoost; persisted model artifacts.
- **Decision engine:** Python module for feasibility rules, cost calculation, scenario adjustment, and timing recommendation.
- **Caching layer:** Redis may be used for frequently accessed forecast/reference data and expensive computation results.
- **Visualization:** React chart components and concise decision cards.
- **Deployment:** local/demo cloud environment using React + FastAPI + Supabase; Docker optional.

## Acceptance Criteria
A release is accepted when all conditions below are met:
- Supabase Auth can authenticate an MVP user and establish an authenticated session.
- The React app accepts valid cargo, origin, destination, volume, and date-window inputs.
- It prevents or clearly handles unsupported ports/routes.
- It displays a forecast with date labels and uncertainty range.
- It identifies feasible and infeasible vessel classes with reasons.
- It calculates and displays cost/turnaround assumptions for feasible options.
- It produces one actionable timing recommendation with rationale and risk flags.
- At least two scenario controls update the displayed result.
- It provides an exportable recommendation summary or equivalent screen-ready report.
- Test scenarios and model-evaluation results are documented.

## Future Roadmap
### Phase 2
- Expand to more origins, East Coast ports, commodities, and vessel classes.
- Integrate licensed freight, AIS, bunker, and congestion data feeds.
- Add probabilistic congestion forecasting and weather disruption signals.
- Add richer contract comparison: rolling spot, voyage charter, time charter, and COA.

### Phase 3
- Integrate with SAIL planning, ERP, tendering, and contract workflows.
- Add portfolio-level multi-parcel/multi-voyage optimization.
- Add automated alerts, governance workflows, richer role-based permissions, enterprise SSO/OIDC, and audit trails.
- Add monitoring, drift detection, retraining schedules, and model governance.

## Demo Scenario
A logistics manager needs to import a specified coal parcel from a selected origin to Paradip or Vizag within a stated delivery window. The manager enters the parcel details, views the 30-/90-day freight outlook, compares eligible vessel classes, tests a freight increase and congestion-delay scenario, and exports a summary that states the recommended vessel, market-entry action, expected cost range, and assumptions.

## Open Questions
- Which exact SAIL commodities, routes, and annual volumes should be prioritized after MVP validation?
- Which port parameters should be treated as static planning values versus live operational values?
- What historical chartering outcomes can SAIL share for back-testing and savings validation?
- Which commercial data subscriptions or broker feeds could be licensed for production?
- What approval thresholds and procurement policies should shape the future recommendation workflow?
