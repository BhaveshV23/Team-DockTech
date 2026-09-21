# AI Development Rulebook

## Purpose
This file is the mandatory rulebook for any AI assistant or developer generating, modifying, reviewing, or refactoring code for **DockTech**.

The goal is to preserve a secure, maintainable, tested, consistent application while implementing the freight forecasting and chartering decision-support product described in `PRD.md`, `ARCHITECTURE.md`, and `DESIGN.md`.

## Rule Priority
When rules conflict, follow this order:
1. Security, privacy, data protection, and server-side authorization.
2. Correctness, data integrity, and decision-support safety.
3. Architecture boundaries in `ARCHITECTURE.md`.
4. Design and accessibility requirements in `DESIGN.md`.
5. Tests, documentation, maintainability, and delivery conventions.
6. Local code-style preferences.

If a request conflicts with a higher-priority rule, do not implement it as requested. Explain the conflict and use a safe alternative.

## Required Project Documents
Before making changes, treat these files as the source of truth:
- `PRD.md` — product scope, requirements, MVP boundaries, success criteria.
- `ARCHITECTURE.md` — system layers, folder responsibilities, Supabase boundaries, data flow, and security boundaries.
- `DESIGN.md` — visual system, Professional Data-Driven Minimalism + Structured Bento Grid direction, reusable component expectations, UX, and accessibility requirements.
- `RULES.md` — development guardrails in this document.

### AI IDE context rule
An AI assistant must understand the project from the complete document set before making non-trivial changes. Do not treat this file as a replacement for `PRD.md`, `ARCHITECTURE.md`, or `DESIGN.md`.

For non-trivial work, inspect:
1. `RULES.md`
2. `PRD.md`
3. `ARCHITECTURE.md`
4. `DESIGN.md`
5. The relevant source code, configuration, tests, and API contracts

The documents are complementary:
- `PRD.md` answers **what the product must do and what is in scope**.
- `ARCHITECTURE.md` answers **how the system is structured and where logic belongs**.
- `DESIGN.md` answers **how the product should look, behave, and remain accessible**.
- `RULES.md` answers **what implementation practices are mandatory or prohibited**.

If documentation conflicts with current code, do not silently choose one. Inspect the implementation, identify the mismatch, and make the smallest safe change consistent with the intended architecture. If the conflict changes a product requirement or architecture decision, flag it explicitly rather than inventing a new decision.

# 1. General Development Rules

1. **Reuse existing components, utilities, hooks, services, types, and patterns before creating new ones.** Search the codebase first.
2. **Do not duplicate logic.** Extract shared behavior into an appropriate utility, hook, domain function, service, or reusable component.
3. **Keep functions small and focused.** A function should have one clear responsibility and a descriptive name. Split deeply nested or multi-purpose functions.
4. **Do not modify unrelated files.** Change only files required for the requested feature, bug fix, test, documentation update, or necessary integration.
5. **Make the smallest correct change.** Avoid opportunistic rewrites, broad formatting changes, dependency upgrades, or folder reorganizations unless explicitly requested or necessary for correctness/security.
6. **Prefer clarity over cleverness.** Use readable names, explicit control flow, typed data structures, and predictable behavior.
7. **Do not introduce dead code.** Remove unused imports, unreachable branches, obsolete comments, and unused helpers created by the change.
8. **Avoid premature abstraction.** Create an abstraction only when it clearly reduces repeated logic or establishes a documented architecture boundary.
9. **Do not invent domain facts or data.** Never fabricate freight rates, vessel specifications, port constraints, model results, users, credentials, or data sources. Use API data, documented seed data, or clearly labelled mocks.
10. **Preserve units and provenance.** Freight, cost, dimensions, dates, and assumptions must retain explicit units, source/quality labels, and data-as-of metadata where applicable.
11. **Fail safely.** If required data, model artifacts, authorization, or route support is unavailable, return a clear error or warning. Never silently return a guessed recommendation.
12. **Keep code consistent with surrounding conventions.** Match established linting, formatting, naming, import order, error handling, and test patterns.

# 2. Before Coding

Before editing code, complete the following steps.

1. **Read relevant documentation.**
   - Read `PRD.md` for product scope and expected behavior.
   - Read `ARCHITECTURE.md` for the affected layer and ownership boundary.
   - Read `DESIGN.md` before changing React UI, layout, interactions, charts, or accessibility behavior.
   - Read this `RULES.md` every time.

2. **Inspect existing implementation.**
   - Find the route/page/component/service/domain module/repository closest to the requested change.
   - Inspect related types, API contracts, tests, data models, and existing error states.
   - Search for an existing implementation that can be reused or extended.

3. **Confirm scope.**
   - Identify the intended user, input, output, authorization requirement, data source, and failure behavior.
   - Check whether the request is in MVP scope. If it is explicitly out of scope, state that and propose a safe scoped alternative.

4. **Plan large changes.**
   For multi-file, cross-layer, data-model, or security-sensitive work, write a concise plan before coding that includes:
   - Files/layers to change.
   - API or schema changes.
   - Data migration/compatibility impact.
   - Test strategy.
   - Security/authorization implications.
   - Rollback or safe-failure approach if relevant.

5. **Ask for clarification when required.**
   Ask before coding if a key decision is ambiguous, especially for: business rules, cost formulas, port constraints, data source authority, user roles, destructive behavior, or production credentials. Do not make hidden assumptions that change business outcomes.

# 3. Architecture Rules

These rules are non-negotiable and align with `ARCHITECTURE.md`.

## 3.1 Separation of responsibilities

1. **UI components must not contain database logic.**
   - No SQL, ORM session, repository import, database connection, direct file-store read, or database credentials in React components.
   - React must never read `CSV`, `Parquet`, model artifacts, or reference tables directly as a substitute for backend APIs.

2. **Database operations belong in backend services and repositories.**
   - Services coordinate use cases and call repositories.
   - Repositories encapsulate Supabase/PostgreSQL query and persistence details.
   - API route handlers and frontend code must not perform direct database operations.

3. **Business logic must remain separate from UI.**
   - Forecasting, vessel feasibility, cost calculation, ranking, risk scoring, and contract recommendation logic belong in backend domain/service modules.
   - UI renders results and collects input; it does not recreate chartering rules in JavaScript/TypeScript.

4. **API route handlers must remain thin.**
   - Authenticate.
   - Authorize.
   - Validate request schema.
   - Call a service.
   - Serialize a safe response.
   - Do not embed SQL, complex calculations, model code, or large business-rule branches in endpoints.

5. **Domain code must remain framework-independent.**
   - Domain modules must not import React, FastAPI route objects, Supabase SDK clients, database sessions/ORM, HTTP clients, or UI libraries.
   - Prefer pure functions with typed input/output for feasibility, cost, ranking, and recommendation rules.

6. **Keep data-source details replaceable.**
   - External provider access belongs in integration/data-client modules.
   - Data services should depend on interfaces/adapters where practical.
   - Do not bind UI or domain rules to one paid provider or one file format.

## 3.2 Frontend architecture

1. Put generic reusable visual primitives in `components/ui/`.
2. Put reusable FreightWise-specific presentation components in `components/domain/`.
3. Put page composition and routing concerns in `pages/`.
4. Put feature state, query hooks, API-to-view-model mapping, and feature orchestration in `features/`.
5. Put HTTP/API clients in `services/`; do not scatter `fetch` calls across low-level components.
6. Use shared formatters for dates, currency, ranges, quantities, durations, dimensions, and percentages.
7. Do not calculate business-critical values on the client when the backend is authoritative.
8. Treat frontend route guards and hidden controls as usability features only; they are not security controls.

## 3.3 Backend architecture

1. Validate request and response data using typed schemas.
2. Keep request DTOs, persistence models, domain entities, and response DTOs distinct where the distinction improves safety and clarity.
3. Use services for workflow orchestration.
4. Use repositories for persistence access.
5. Put model training outside normal request handling. API requests may load models and perform inference, but must not retrain models.
6. Version model artifacts, data inputs, and feature definitions where possible.
7. Return structured domain-safe errors; do not leak stack traces, database details, tokens, or vendor messages.

# 4. Supabase Rules

Supabase is the project's managed backend infrastructure for PostgreSQL, Authentication, and Storage. These rules are mandatory wherever Supabase is used.

## 4.1 Supabase responsibilities

1. **Supabase PostgreSQL is the application/reference/scenario/recommendation data store.**
2. **Supabase Auth is the identity and session system.**
3. **Supabase Storage is used for approved reports/uploads and related file objects.**
4. **FastAPI remains the core application backend and business-logic boundary.**
5. Redis is optional and may be used for caching where the architecture requires it; Redis does not replace Supabase as the system of record.
6. Do not introduce a second primary database, legacy standalone PostgreSQL setup, SQLite database, or parallel authentication system unless `ARCHITECTURE.md` is intentionally changed first.

## 4.2 Frontend and Supabase

1. React may use the Supabase client for **authentication/session operations** required by the approved architecture.
2. React must not directly read or write FreightWise application tables as a substitute for FastAPI.
3. Core application data, forecasting, feasibility, cost, recommendation, scenario, report, and administrative operations must go through the FastAPI API.
4. Never expose the Supabase `service_role` key, database credentials, private signing keys, or other privileged secrets to the browser.
5. Do not put privileged Supabase operations in React components, hooks, or client-side utility modules.
6. Keep Supabase Auth session handling centralized rather than scattering authentication calls throughout UI components.
7. Frontend route protection is a UX feature; FastAPI must independently verify authentication and authorization.

## 4.3 FastAPI and Supabase

1. FastAPI must verify Supabase Auth access tokens for protected requests.
2. FastAPI must enforce application roles/permissions server-side for protected reads, writes, exports, and administrative actions.
3. Supabase access from FastAPI must be centralized in dedicated infrastructure/client modules rather than scattered through route handlers.
4. Keep database access behind repositories/data-access services. Route handlers must not contain raw Supabase queries.
5. Prefer typed schemas and explicit repository methods over passing arbitrary table names, filters, or user-controlled query fragments through the application.
6. If a privileged Supabase server credential is used, treat it as equivalent to a database superuser credential: server-side only, never logged, never returned to clients, and never committed.
7. Do not rely on frontend-supplied `user_id`, role, ownership, or permission fields. Derive identity from the verified authentication context and authorize against server-side data.
8. Keep Supabase-specific SDK details out of domain logic where practical. Domain services should operate on domain-level interfaces/data rather than Supabase response objects.

## 4.4 Supabase Row Level Security and authorization

1. Use Row Level Security (RLS) where it provides an additional database-level protection appropriate to the data and access path.
2. RLS does not replace FastAPI authorization. Server-side authorization remains mandatory.
3. If FastAPI uses a privileged/service-role Supabase credential that bypasses RLS, every protected operation must still perform explicit server-side authorization before access.
4. Never disable RLS merely to make a feature work without documenting the security reason and reviewing the affected access path.
5. Define ownership/role policies explicitly for user-owned or role-restricted data before exposing direct Supabase access to any client.
6. Test authorization boundaries, including attempts to access another user's scenarios, reports, saved analyses, or administrative data.

## 4.5 Supabase Storage

1. Store only approved report/upload artifacts in Supabase Storage.
2. Do not expose private buckets or unrestricted objects without an explicit security decision.
3. Use server-authorized access for protected files when required by the architecture.
4. Validate file type, size, naming, and content expectations before storing uploads.
5. Do not store secrets, credentials, raw confidential procurement data, or arbitrary executable content in Storage.
6. Keep storage paths deterministic and authorization-aware; do not use client-controlled paths as the sole access control.
7. Do not commit downloaded production files or generated confidential artifacts to Git.

## 4.6 Supabase migrations and schema changes

1. Treat Supabase PostgreSQL schema as a controlled, versioned contract.
2. Before changing tables, columns, constraints, indexes, RLS policies, or relationships, inspect the current schema and existing migration/history mechanism.
3. Use the project's established Supabase migration workflow; do not introduce Alembic or another parallel migration system unless the architecture explicitly changes.
4. Every schema change must consider existing data, backward compatibility, indexes, constraints, RLS policies, and rollback/recovery.
5. Keep seed/reference data separate from production secrets and clearly label synthetic/demo data.
6. Do not change Supabase schema directly in production as an undocumented one-off fix.

## 4.7 Supabase configuration

Use environment variables for Supabase configuration. Names may follow the project's actual implementation, but the intended separation is:

- Frontend: Supabase project URL and the publishable/anon client key only, when required for Auth.
- Backend: Supabase project URL plus privileged server credentials only on the server.
- Never expose backend-only environment variables through Vite/React public environment prefixes or equivalent client bundles.
- `.env.example` may contain placeholder names/values only.

# 4. UI and UX Rules

All frontend work must follow `DESIGN.md`.

## 4.1 Visual consistency

1. Use design tokens for color, typography, spacing, radius, shadows, and motion. Do not hard-code arbitrary styling values in isolated components.
2. Reuse existing shared components before creating a new button, card, badge, input, modal, chart wrapper, table, alert, or layout pattern.
3. Follow sentence case for labels, buttons, titles, and headings.
4. Keep units visible: `USD/tonne`, `tonnes`, `days`, `m`, `DWT`, `nm`, and `%`.
5. Use semantic colors consistently. Never rely on color alone; include text labels and icons for status/risk.
6. Keep the visual hierarchy decision-first: recommended action, vessel feasibility, expected cost/range, risk, then supporting detail.
7. Avoid decorative gradients, unnecessary animation, excessive shadows, and dashboard clutter.

## 4.2 Responsive design

1. Every UI change must work on mobile, tablet, and desktop.
2. Use responsive layout primitives; do not hard-code desktop-only widths.
3. On narrow screens, show the recommendation before large charts and comparison tables.
4. Convert wide tables to responsive cards or allow clear horizontal scroll with meaningful frozen/visible identifiers.
5. Ensure sticky controls do not cover content or browser UI on mobile.
6. Test at representative widths: approximately 375px, 768px, 1024px, and 1440px.

## 4.3 Required states

Every data-driven screen/component must implement appropriate states:

1. **Loading state**
   - Use skeletons for structured content and inline progress for triggered actions.
   - Preserve layout while results are loading.
   - Prevent duplicate submissions.

2. **Error state**
   - Explain what failed in user language.
   - State the next action when possible: retry, correct input, choose supported route, or contact an administrator.
   - Do not expose stack traces, credentials, raw SQL, or internal implementation details.

3. **Empty state**
   - Explain why there is no content.
   - Provide the next useful action.
   - Do not show a blank white area when no forecasts, reports, or scenarios exist.

4. **Success/confirmation state**
   - Clearly confirm completed user actions such as saving a scenario or exporting a report.
   - Use a persistent status when the action has material business significance.

5. **Unauthorized/forbidden state**
   - Show a clear access message.
   - Do not reveal protected data, even partially.

## 4.4 Accessibility

1. Use semantic HTML and logical heading order.
2. Every input must have a visible associated label. Placeholders are not labels.
3. All interactive controls must be keyboard reachable and have visible focus states.
4. Icon-only buttons require accessible names.
5. Modals must trap focus, support Escape to close where appropriate, and restore focus on close.
6. Maintain target contrast ratios and do not use color as the only indicator.
7. Charts require text summaries and accessible table/data alternatives for critical information.
8. Form errors must be announced to assistive technologies.
9. Support browser zoom to 200% without breaking essential functionality.
10. Respect reduced-motion preferences.

## 4.5 Decision-support safety in UI

1. Do not represent recommendations as guaranteed outcomes.
2. Always show forecast uncertainty, risk, assumptions, and data recency where relevant.
3. Clearly label actual, proxy, simulated, stale, or missing data.
4. Show the reason when a vessel is rejected or recommended.
5. Include the decision-support disclaimer on recommendation/report surfaces: current market terms and port notices must be validated before fixing a vessel.
6. Never display a status implying a charter has been executed unless the backend confirms a future real transaction workflow.

# 5. Security Rules

## 6.1 Secrets and credentials

1. **Never expose API keys, database credentials, tokens, signing keys, Supabase service-role keys, or provider secrets.**
2. Never commit `.env` files, private certificates, real passwords, production exports, or secret-bearing configuration to Git.
3. Use environment variables or an approved secret manager on the server. Commit only `.env.example` with placeholder values.
4. The frontend may contain only the Supabase public project URL and publishable/anon client key when required by the architecture. Treat even public configuration as non-secret and never place privileged credentials there.
5. Supabase `service_role` keys and other privileged credentials are backend-only.
6. Never send secrets from backend to frontend.
7. Never log secrets, authorization headers, cookies, passwords, full access/refresh tokens, or raw Supabase error payloads that may contain sensitive information.

## 6.2 Input validation

1. Validate all untrusted input at the server boundary using typed schemas and strict constraints.
2. Validate allowed origin/destination ports, vessel classes, commodity values, date ranges, numeric ranges, units, and enum values.
3. Use parameterized queries/ORM-safe methods. Never interpolate untrusted input into SQL.
4. Treat all client-provided IDs, roles, prices, feasibility flags, model results, and permissions as untrusted.
5. Sanitize/escape user-generated text before rendering if user-authored content is introduced.
6. Limit upload types, sizes, and parsing behavior if file upload is added.

## 6.3 Authentication and authorization

1. **Supabase Auth is the project's authentication/session authority.**
2. **Authentication must be verified server-side on every protected request.**
3. **Authorization must be enforced server-side before protected reads, exports, writes, configuration changes, and administrative actions.**
4. FastAPI must validate the Supabase access token and derive the authenticated user identity from the verified token/session.
5. Do not trust frontend roles, hidden buttons, route guards, client-provided user IDs, or unverified client-side claims.
6. Apply least privilege: users receive only the permissions required for their application role.
7. Use secure session/token handling and appropriate cookie protections if cookies are used.
8. Require re-authentication or explicit confirmation for sensitive future actions when appropriate.
9. Record audit events for administrative data changes, sensitive exports, and future procurement-related actions.

## 6.4 Data protection

1. Do not include real confidential procurement data in test fixtures, screenshots, seed files, logs, or public repositories.
2. Use sanitized or synthetic data for local demos unless approved data access exists.
3. Minimize data returned to the frontend. Return only fields required by the UI.
4. Do not expose internal model internals, vendor contracts, or unnecessary user data through APIs.
5. Use HTTPS in deployed environments.
6. Define retention and access rules before storing saved scenarios, reports, or user activity at production scale.

# 6. Data, Forecasting, and Domain Rules

1. Treat forecasting and recommendations as decision support, not automatic contract execution.
2. Preserve source, timestamp, units, route/vessel context, and quality label for externally sourced data.
3. Clearly distinguish actual, proxy, estimated, and simulated values.
4. Do not silently backfill missing data with fabricated values. Use documented imputation, a fallback model, a visible warning, or an error.
5. Use time-aware validation for forecasting; never randomly shuffle chronological data for train/test evaluation.
6. Keep model training separate from online inference.
7. Record model version, data-as-of date, forecast horizon, and confidence/uncertainty output with recommendations.
8. Validate port constraints and vessel dimensions using consistent units before feasibility calculations.
9. Make business assumptions configurable and visible rather than scattering unexplained constants through code.
10. Return reasons/explanation codes with vessel feasibility, risk flags, cost estimates, and market-entry recommendations.
11. If live/authoritative port data is unavailable, state that the result relies on planning data and must be confirmed against current notices.
12. Do not claim savings, forecast accuracy, or optimization performance unless backed by documented calculations and evaluation data.

# 7. Testing Rules

## 7.1 Required test behavior

1. **Add tests for important functionality.** Every non-trivial feature, bug fix, domain rule, security condition, or API contract change requires appropriate automated tests.
2. **Run relevant tests after implementation.** Do not consider a change complete without running the affected test suite.
3. **Fix failing tests before continuing.** Do not ignore, skip, weaken, or delete a failing test merely to make CI pass unless the test is demonstrably obsolete and its replacement is included.
4. Keep tests deterministic. Do not rely on live external APIs, current time without control, random values without seeds, or shared mutable state.
5. Use fixtures that are minimal, explicit, and safe for public/local development.

## 7.2 Test levels

### Unit tests
Write unit tests for pure, high-value logic including:
- Vessel–port feasibility checks.
- Draft/LOA/beam boundary conditions.
- Voyage and turnaround-time calculations.
- Cost-per-tonne calculation.
- Vessel ranking/tie-breaking.
- Risk flagging.
- Recommendation policy.
- Formatters and data transformations with important business impact.

### Service and repository tests
Write tests for:
- Service orchestration with repository/model mocks or test database.
- Data persistence and retrieval.
- Transaction/rollback behavior where relevant.
- Missing/stale data behavior.
- Model fallback behavior.

### API tests
Write tests for:
- Request validation failures.
- Correct successful response schema.
- Authentication and authorization enforcement.
- Safe error responses.
- Unsupported route/port handling.
- Admin-only mutation protections.

### Frontend tests
Write tests for:
- Important interaction flows.
- Loading, error, empty, and unauthorized states.
- Required validation and disabled-submit behavior.
- Accessible labels and keyboard interactions for key controls.
- Rendering of API-provided recommendation/risk/assumption data.

### End-to-end tests
Add E2E coverage for critical flows when test infrastructure is available:
- Sign in -> plan shipment -> generate recommendation -> apply scenario -> export report.
- Unauthorized user blocked from admin actions.
- Infeasible vessel shown with a clear reason.

## 7.3 Test quality

1. Test behavior, not internal implementation details.
2. Include edge cases and boundary values.
3. Include negative tests for invalid/unsafe input.
4. Mock external integrations at boundaries, not internal business logic unnecessarily.
5. Keep test names descriptive: `rejects_vessel_when_draft_exceeds_destination_limit`.
6. Update tests and documentation whenever intentional behavior changes.

# 8. Git and Change Management Rules

1. **Make small, focused commits.** Each commit should represent one logical change.
2. **Use descriptive commit messages.** Prefer imperative, meaningful messages such as:
   - `feat: add vessel feasibility result to recommendation API`
   - `fix: reject cargo delivery windows with invalid end date`
   - `test: cover high congestion scenario cost calculation`
   - `docs: clarify forecast uncertainty display rules`
3. Do not mix unrelated refactors, formatting churn, dependency upgrades, and feature changes in the same commit.
4. Review `git diff` before committing. Confirm no secrets, generated artifacts, unrelated files, or confidential data are included.
5. Do not commit local environment files, node modules, virtual environments, test output, or large unapproved model artifacts.
6. Keep branch names descriptive, such as `feat/recommendation-card`, `fix/port-draft-validation`, or `docs/design-tokens`.
7. Rebase/resolve conflicts carefully; rerun tests after conflict resolution.
8. If a change introduces a migration, include migration files, rollback considerations, and test coverage.

# 9. Documentation Rules

1. Update documentation when an API contract, feature behavior, data assumption, architecture boundary, model behavior, or setup step changes.
2. Keep `PRD.md`, `ARCHITECTURE.md`, and `DESIGN.md` aligned with material product changes.
3. Document all assumptions that affect cost, forecast, feasibility, or recommendation results.
4. Add source and effective-date metadata for reference data changes.
5. Keep README setup instructions accurate and runnable.
6. Add comments only when they explain non-obvious intent, tradeoffs, domain reasoning, or constraints. Do not restate obvious code.
7. Never document secrets, real tokens, or confidential operational values in public files.

# 10. Performance and Reliability Rules

1. Do not block UI rendering with expensive calculations. Run forecasting, optimization, and data access on the backend.
2. Avoid N+1 database queries; use efficient repository queries and batch loading where appropriate.
3. Paginate or filter large report/audit/reference-data lists.
4. Cache stable reference data at appropriate layers, but define invalidation when admins update it.
5. Use request timeouts and graceful fallbacks for external integrations.
6. Show data freshness and degraded-mode status when external data is unavailable or stale.
7. Preserve user-entered form values on retryable errors.
8. Do not optimize prematurely; profile before introducing complexity.

# 11. Prohibited Practices

An AI assistant or developer must not:
- Put database queries or database credentials in React components.
- Expose API keys, secrets, tokens, passwords, or signed URLs in client code or logs.
- Trust client-side role checks as authorization.
- Implement critical business rules only in frontend code.
- Bypass validation because “the UI already validates it.”
- Invent freight data, port limits, vessel details, forecast outputs, cost savings, or accuracy claims.
- Make recommendations appear certain when data is proxy, stale, missing, or uncertain.
- Delete/skip tests to hide failures.
- Change unrelated files without reason.
- Introduce a new UI pattern when an existing component can be reused.
- Commit generated dependencies, secrets, private data, or unrelated build output.
- Make destructive admin changes without clear user confirmation and server-side authorization.

# 13. AI Response and Delivery Protocol

When asked to implement a change, the AI should follow this sequence:

### Required project-context verification

Before non-trivial implementation, the AI should be able to answer these questions from the project documents and code:
- What requirement in `PRD.md` is being implemented?
- Which architectural layer in `ARCHITECTURE.md` owns the change?
- Which UI/UX rules in `DESIGN.md` apply?
- Which `RULES.md` constraints affect security, data, testing, and delivery?
- Is Supabase Auth, PostgreSQL, Storage, or RLS involved?
- Which existing API, service, repository, component, hook, type, or test should be reused?
- What data is authoritative, and what is proxy/simulated/estimated?
- What must happen when required data or authorization is unavailable?

If the AI cannot answer these questions from the available project context, it must inspect the relevant files/code before implementing. It must not invent missing architecture or product decisions.

### Implementation sequence

1. **Inspect** relevant docs and existing code.
2. **Summarize** the intended change, affected layers, and assumptions for non-trivial work.
3. **Plan** multi-file or cross-layer work before editing.
4. **Implement** the smallest correct change in the proper architectural layer.
5. **Test** the changed behavior and relevant regression paths.
6. **Fix** all failures caused by the change.
7. **Review** security, accessibility, responsive behavior, loading/error/empty states, and documentation impact.
8. **Report** what changed, tests run, and any remaining assumptions/limitations.

For simple isolated changes, the plan may be brief. For security, database, model, API-contract, or multi-layer changes, the plan and verification must be explicit.

# 14. Completion Checklist

Before declaring work complete, verify:

## Scope and architecture
- [ ] The request is within intended scope or its limitation is documented.
- [ ] Relevant product, architecture, and design documents were reviewed.
- [ ] Existing functionality was inspected and reused where possible.
- [ ] No unrelated files were changed.
- [ ] UI, API, service, repository, and domain responsibilities remain separated.

## UI and UX
- [ ] The implementation follows `DESIGN.md` and uses shared components/tokens.
- [ ] Responsive behavior was considered for mobile, tablet, and desktop.
- [ ] Loading, error, empty, success, and unauthorized states are handled where relevant.
- [ ] Labels, units, assumptions, data freshness, and risk/uncertainty are visible where relevant.
- [ ] Accessibility basics are satisfied.

## Security and data
- [ ] No secrets, credentials, Supabase service-role keys, or confidential data are exposed.
- [ ] All server inputs are validated.
- [ ] Supabase Auth authentication is verified server-side.
- [ ] Authorization is enforced server-side and, where appropriate, reinforced with RLS.
- [ ] Supabase Storage access is appropriately protected.
- [ ] Data provenance and actual/proxy/simulated labels are preserved where relevant.
- [ ] Errors fail safely without leaking internals.

## Quality
- [ ] Important logic has appropriate tests.
- [ ] Relevant tests were run after implementation.
- [ ] Failing tests were fixed rather than ignored.
- [ ] Lint/type checks/build checks were run when available.
- [ ] Documentation was updated if behavior, contracts, assumptions, or architecture changed.
- [ ] Commit(s) are small, focused, and descriptively named.

# 15. AI IDE Compatibility

This rulebook is intentionally written as plain Markdown with explicit numbered rules, source-of-truth documents, architectural boundaries, security constraints, and implementation checklists.

It is intended to be usable by:
- Gemini / Gemini CLI or Gemini-powered IDE agents
- Cursor
- Claude Code
- Codex-based coding agents
- GitHub Copilot / Copilot coding agents
- Antigravity or other repository-aware AI IDE agents
- Human developers

An AI IDE should not be expected to understand the entire project from `RULES.md` alone. The repository should keep `PRD.md`, `ARCHITECTURE.md`, `DESIGN.md`, and `RULES.md` together at the project root. The agent should load or inspect all four before substantial work and then inspect the relevant source code.

For maximum reliability, keep these documents synchronized. When a major architecture decision changes, update the affected source-of-truth document(s) rather than adding contradictory instructions only to this file.
