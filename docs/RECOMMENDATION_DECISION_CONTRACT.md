# Recommendation Decision Contract — Proposed V1

Status labels: **SOURCE-DEFINED** means stated by PRD, ARCHITECTURE, DATA_DICTIONARY, or current code. **V1 IMPLEMENTATION POLICY** is a deterministic choice needed to implement an unspecified rule; it is proposed, not an existing source requirement. **UNSPECIFIED / REQUIRES TEAM DECISION** means available inputs or rules do not support a defensible policy.

## A. Proposed V1 Decision Contract

### 1. Vessel eligibility

- **SOURCE-DEFINED** — A candidate is eligible only when feasibility returns `FEASIBLE` for the requested cargo, commodity, origin and destination; both ends must have a commodity berth meeting LOA, beam and draft constraints.
- **SOURCE-DEFINED** — Cargo exceeding vessel cargo capacity is not itself a rejection. Use `required_voyages = ceil(cargo_volume_mt / cargo_capacity_mt)`; capacity means cargo capacity, not DWT.
- **V1 IMPLEMENTATION POLICY** — Exclude `INFEASIBLE` and `INSUFFICIENT_DATA` results from ranking. If no candidate remains, fail without a recommendation.

### 2. Forecast

- **V1 IMPLEMENTATION POLICY** — Sort valid points by `forecast_date`; define direction by comparing the first and final available `central_value`: final greater than first = **RISING**, final less = **FALLING**, equal = **FLAT**. No minimum percentage or numeric threshold is applied.
- **V1 IMPLEMENTATION POLICY** — Use the first chronological forecast point’s `central_value` as expected freight for the cost calculation. It is the nearest forecast point to the forecast run’s training-data end date. Persisted run/point freight units must agree.
- **SOURCE-DEFINED** — Represent forecast uncertainty with the point’s `lower_value`, `central_value`, and `upper_value`, retaining the run’s freight unit. This contract adds no uncertainty cutoff or confidence percentage.
- **UNSPECIFIED / REQUIRES TEAM DECISION** — Whether the first point is the commercially appropriate freight point for every delivery window is not defined by sources; first-point use above is a provisional V1 implementation choice.

### 3. Risk

- **V1 IMPLEMENTATION POLICY** — Aggregate the three canonical scenario risk labels by worst case: `LOW < MEDIUM < HIGH`; recommendation risk is the maximum of baseline, adverse, and favorable.
- **SOURCE-DEFINED** — These labels are categorical and use the existing `RiskLevel` values. Current `RiskEvaluator` produces them using documented scenario rules, including congestion, delay, laycan-duration comparison, and forecast-spread thresholds.

### 4. Vessel selection

- **SOURCE-DEFINED** — Rank only eligible vessels; PRD identifies expected cost per tonne, delivery feasibility, and risk as comparison dimensions.
- **V1 IMPLEMENTATION POLICY** — Use lexicographic ordering, with no weighted or hidden score: (1) lower `effective_cost_per_mt`; (2) lower aggregate risk (`LOW`, then `MEDIUM`, then `HIGH`); (3) lower `estimated_turnaround_hours`; (4) fewer `required_voyages`; (5) lexicographically smaller `vessel_class_id`. Cost and turnaround come from the canonical cost result; voyage count is the feasibility/cost result.
- **UNSPECIFIED / REQUIRES TEAM DECISION** — Date-specific delivery feasibility cannot be ranked from current contracts: no departure/market-entry date or arrival-date rule is defined. The existing risk check compares operation duration with laycan duration, but does not establish an arrival date. The proposed ordering therefore does not claim date-specific delivery feasibility.

### 5. Market entry

- **SOURCE-DEFINED** — `FIX_NOW` and `WAIT` are independent of contract strategy. PRD says rising rates, high uncertainty, or delivery urgency favor `FIX_NOW`; falling rates may favor `WAIT` when reduction outweighs waiting risk and delivery remains feasible.
- **V1 IMPLEMENTATION POLICY** — **RISING → `FIX_NOW`**. **FALLING → `WAIT`** only when aggregate risk is below `HIGH` and modeled operation duration does not exceed laycan duration; otherwise `FIX_NOW`. **FLAT → `FIX_NOW`** as a conservative no-delay default. These rules use no new numeric threshold.
- **V1 IMPLEMENTATION POLICY** — If fewer than two valid points exist, direction is insufficient; use `FIX_NOW` as the conservative no-delay default and explain the missing directional evidence. This does not assert that rates will rise.
- **UNSPECIFIED / REQUIRES TEAM DECISION** — A source-defined threshold for “high uncertainty,” “urgent,” or “likely” movement is absent. This contract does not create one.

### 6. Contract strategy

- **SOURCE-DEFINED** — `contract_horizon` is user preference, while `contract_strategy` is an engine recommendation; they are distinct and the recommendation may differ. `SPOT` and `SHORT_TERM_MULTIPLE_VOYAGE` are independent from market timing.
- **V1 IMPLEMENTATION POLICY** — Recommend `SHORT_TERM_MULTIPLE_VOYAGE` when `required_voyages > 1`; otherwise recommend `SPOT`. Required voyages, not DWT or horizon, determine whether the selected vessel needs multiple voyages.
- **V1 IMPLEMENTATION POLICY** — Treat `cargo.contract_horizon` as advisory context, not a hard constraint. Record a divergence (including `SPOT` preference with multiple required voyages) in rationale/assumptions; do not change the voyage-based mapping.

### 7. Confidence

- **SOURCE-DEFINED** — `confidence` is categorical `LOW`, `MEDIUM`, or `HIGH`, never a probability or percentage.
- **V1 IMPLEMENTATION POLICY** — `HIGH` only when direction is rising/falling, all three scenario risks agree, and required inputs are complete; `MEDIUM` when inputs are complete but direction is flat or scenario risks differ; `LOW` when direction is insufficient (one point). This label describes evidence consistency, not forecast accuracy or probability.

### 8. Failure behavior

- **V1 IMPLEMENTATION POLICY** — Fail the recommendation operation and do not persist a partial recommendation if there are no feasible vessels, no valid forecast points, incomplete cost results for the selected candidate, or incomplete baseline/adverse/favorable risk results.
- **SOURCE-DEFINED** — Fail safely with a structured domain error for missing/contradictory route, berth, forecast, fuel, port activity, or other required inputs; do not invent compatibility, forecasts, or cost inputs.
- **SOURCE-DEFINED** — Reject inconsistent provenance: cargo ID must match the forecast run; forecast route must match the cargo’s resolved route; run vessel must match the recommended vessel; forecast points must belong to that run and use its unit. Do not persist a recommendation on mismatch.
- **V1 IMPLEMENTATION POLICY** — Preserve the underlying error category/context for callers; never silently drop a candidate with missing required data and then present the remaining result as complete.

### 9. Forecast-run invariant

- **SOURCE-DEFINED** — A persisted recommendation’s `forecast_run_id` must reference a run whose `cargo_request_id` equals the recommendation cargo, whose `route_id` equals the cargo’s resolved route, and whose `vessel_class_id` equals `recommended_vessel_class_id`. Validate before persistence.
- **SOURCE-DEFINED** — Current forecast generation is per vessel class, so obtain/use the run for the ultimately selected vessel; a run for a different candidate cannot be attached to the recommendation.

### 10. Output fields

The frozen recommendation field set matches the `recommendations` table in DATA_DICTIONARY and the Supabase migration. There is **no current Python Recommendation response schema** to verify against; API schema remains to be introduced separately. Persist all fields as required:

| Field | Existing frozen definition / source |
|---|---|
| `recommendation_id` | UUID primary key; generated ID / database UUID default. |
| `cargo_request_id` | Required UUID foreign key to `cargo_requests`. |
| `forecast_run_id` | Required UUID foreign key to `forecast_runs`; obey provenance invariant above. |
| `recommended_vessel_class_id` | Required text foreign key to `vessel_classes`; must be feasible. |
| `market_entry_action` | Required controlled text: `FIX_NOW` or `WAIT`. |
| `contract_strategy` | Required controlled text: `SPOT` or `SHORT_TERM_MULTIPLE_VOYAGE`. |
| `expected_freight_cost` | Required positive numeric USD; selected vessel’s canonical cost result using the chosen forecast rate. |
| `expected_total_cost` | Required positive numeric USD; selected vessel’s canonical cost result. |
| `estimated_turnaround_hours` | Required positive numeric hours; total shipment turnaround across required voyages. |
| `risk_level` | Required controlled text: `LOW`, `MEDIUM`, or `HIGH`. |
| `confidence` | Required controlled text: `LOW`, `MEDIUM`, or `HIGH`; qualitative only. |
| `rationale` | Required text explaining decision drivers. |
| `assumptions` | Required text documenting material assumptions. |
| `created_at` | Required timestamp; database default is UTC-capable `TIMESTAMPTZ`. |

## B. Source-defined vs implementation-defined decisions

- **SOURCE-DEFINED:** two-ended feasibility gate; capacity overflow handled through required voyages; canonical forecast point bounds and units; scenario risk labels and existing risk rules; recommendation field names/types/controlled values; confidence categorical semantics; forecast-to-cargo/route/vessel integrity; fail-safe treatment of missing required data; qualitative direction of PRD market guidance; contract horizon is a preference distinct from strategy.
- **V1 IMPLEMENTATION POLICY:** first-to-final central-point trend comparison and strict rising/falling/flat definitions; first-point expected freight; worst-case scenario risk aggregation; lexicographic vessel ranking and tie-break; flat/insufficient trend defaults; voyage-count strategy mapping; categorical confidence evidence mapping; fail-without-persist behavior for incomplete results.
- **UNSPECIFIED / REQUIRES TEAM DECISION:** numeric/qualitative cutoff for high forecast uncertainty or urgency; date-specific delivery feasibility and a departure/arrival anchor; whether first forecast point is the right expected-cost point for all cargo windows. No undocumented thresholds are introduced here.

## C. Remaining blockers

1. Team approval of the explicitly marked V1 implementation policies before they are treated as product rules.
2. A source-backed or team-approved definition of delivery-window feasibility for vessel ranking and `WAIT`; current inputs do not define an actionable departure/arrival date.
3. A team decision on any desired high-uncertainty or urgency trigger. Until defined, this contract uses no invented cutoff.
4. Add a Python/API Recommendation schema during implementation and verify its serialization against the frozen database fields; only the database/data-dictionary schema exists today.
