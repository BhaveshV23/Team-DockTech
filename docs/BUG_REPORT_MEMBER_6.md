# DockTech V1 — Member 6: Bug & Issue Report
**Module:** Scenario Analysis + Risk + Testing / QA  
**Owner:** Member 6 (Siddhant)  
**Date:** 2026-09-24

---

### Bug & Issue Register

| Bug ID | Title | Module | Severity | Root Cause | Fix / Resolution | Retest Status |
|---|---|---|---|---|---|---|
| `BUG-001` | Floating-point rounding discrepancy on USD_PER_DAY vessel days charter hire | Scenario & Cost Integration | Low | Intermediate display rounding of `vessel_days_per_voyage` to 4 decimal places resulted in a minor sub-dollar ($0.56) variance when multiplied by high day-rate ($31,250/day). | Calculated charter hire using full floating-point precision before applying rounding to final currency outputs. | **RESOLVED / PASS** |
| `BUG-002` | Double-rounding divergence on percentage fuel cost assertions | Integration Tests | Low | Multiplying already-rounded base currency strings by shock percentages caused a 1-cent rounding variance ($358,328.21 vs $358,328.20). | Updated currency test comparisons to compute exact float products or use `pytest.approx(..., abs=0.05)`. | **RESOLVED / PASS** |

---

### Cross-Module Observations (For Other Team Members)

1. **Feasibility Module:** Ensure the feasibility engine returns an explicit rejection reason token (`REJECTED_DRAFT_EXCEEDED_DESTINATION_BERTH`, `REJECTED_LOA_EXCEEDED_ORIGIN_BERTH`, etc.) whenever a vessel class fails screening, so the decision dashboard can render transparent explanations.
2. **Forecast Module:** Ensure the forecast run record always includes `training_data_end_date` so the cost engine can deterministically lock the `cost_reference_date`.
3. **Recommendation Module:** When aggregating the recommendation payload, consume `ScenarioResultSet.baseline.cost_breakdown` directly to ensure 100% mathematical consistency across baseline costs, vessel alternatives, and sensitivity scenarios.
