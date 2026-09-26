# DockTech V1 — Member 6: QA Test Execution Report
**Module:** Scenario Analysis + Risk + Testing / QA  
**Owner:** Member 6 (Siddhant)  
**Execution Date:** 2026-09-24  
**Test Framework:** Pytest 8.4.2  
**Overall Status:** 100% PASS (50/50 Tests Passed)

---

## 1. Executive Summary

| Test Category | Total Executed | Passed | Failed | Skipped | Pass Rate |
|---|---|---|---|---|---|
| **Scenario Unit Tests (SC-001–SC-018)** | 19 | 19 | 0 | 0 | 100% |
| **Voyage Cost Math Unit Tests** | 6 | 6 | 0 | 0 | 100% |
| **Risk Evaluation Unit Tests** | 6 | 6 | 0 | 0 | 100% |
| **Scenario Service Integration Tests** | 3 | 3 | 0 | 0 | 100% |
| **FastAPI Route & Contract Tests** | 4 | 4 | 0 | 0 | 100% |
| **Cross-Module Integration Tests** | 4 | 4 | 0 | 0 | 100% |
| **Database & Persistence Tests** | 2 | 2 | 0 | 0 | 100% |
| **End-to-End Decision Workflow** | 1 | 1 | 0 | 0 | 100% |
| **Failure Modes & Negative Tests** | 5 | 5 | 0 | 0 | 100% |
| **Total** | **50** | **50** | **0** | **0** | **100%** |

---

## 2. Detailed Test Execution Register

### A. Scenario Unit Tests (`tests/unit/domain/test_scenario.py`)

| Test ID | Test Description | Input Conditions | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|
| `SC-001` | BASELINE zero freight shock | `DecisionInputs` (Panamax, 75k MT) | `freight_change_pct == 0.0` | `0.0` | **PASS** |
| `SC-002` | BASELINE zero fuel shock | `DecisionInputs` | `fuel_change_pct == 0.0` | `0.0` | **PASS** |
| `SC-003` | BASELINE zero delay | `DecisionInputs` | `delay_hours == 0.0` | `0.0` | **PASS** |
| `SC-004` | BASELINE MEDIUM congestion | `DecisionInputs` | `congestion_level == MEDIUM` | `MEDIUM` | **PASS** |
| `SC-005` | ADVERSE +25% freight shock | `DecisionInputs` | `freight_change_pct == +25.0` | `+25.0` | **PASS** |
| `SC-006` | ADVERSE +15% fuel shock | `DecisionInputs` | `fuel_change_pct == +15.0` | `+15.0` | **PASS** |
| `SC-007` | ADVERSE +48h delay | `DecisionInputs` | `delay_hours == 48.0` | `48.0` | **PASS** |
| `SC-008` | ADVERSE HIGH congestion | `DecisionInputs` | `congestion_level == HIGH` | `HIGH` | **PASS** |
| `SC-009` | FAVORABLE -15% freight shock | `DecisionInputs` | `freight_change_pct == -15.0` | `-15.0` | **PASS** |
| `SC-010` | FAVORABLE -10% fuel shock | `DecisionInputs` | `fuel_change_pct == -10.0` | `-10.0` | **PASS** |
| `SC-011` | FAVORABLE zero delay | `DecisionInputs` | `delay_hours == 0.0` | `0.0` | **PASS** |
| `SC-012` | FAVORABLE LOW congestion | `DecisionInputs` | `congestion_level == LOW` | `LOW` | **PASS** |
| `SC-013` | Exactly 3 scenario results | `DecisionInputs` | `len(as_list()) == 3` | `3` | **PASS** |
| `SC-014` | No duplicate scenario types | `DecisionInputs` | Unique `{BASELINE, ADVERSE, FAVORABLE}` | Unique set of 3 | **PASS** |
| `SC-015` | Freight unit semantics | `USD_PER_MT` vs `USD_PER_DAY` | Correct hire & MT cost calculation | Matches expected | **PASS** |
| `SC-016` | VLSFO is used | Speed: 13 kn, 28 MT/day, $620/MT | `sailing_days * 28 * 620` | `$311,589.74` | **PASS** |
| `SC-017` | MGO is excluded | Standard inputs | Total cost excludes auxiliary MGO | Total = freight + VLSFO | **PASS** |
| `SC-018` | Consistency with cost engine | Adverse shock (+25% freight, +15% fuel) | Total cost strictly matches engine math | Matches exactly | **PASS** |
| `SC-019` | Custom scenario comparison | Custom +10% freight, +5% fuel, 24h delay | Delta cost, turnaround, and risk computed | Correct deltas | **PASS** |

---

### B. Voyage Cost Math Unit Tests (`tests/unit/domain/test_voyage_cost.py`)

| Test ID | Test Description | Input Conditions | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|
| `COST-001` | Sailing days calculation | 5600 nm at 13 knots | 17.9487 days | 17.9487 days | **PASS** |
| `COST-002` | Multi-voyage required voyages | 75k MT capacity with 75k, 75.001k, 150k, 160k | 1, 2, 2, 3 voyages | 1, 2, 2, 3 voyages | **PASS** |
| `COST-003` | Multi-voyage scaling & turnaround | 150k MT, 2 berths, 10h scenario delay | 2 voyages, handling: 192h, delay: 20h | Matches | **PASS** |
| `COST-004` | USD_PER_MT zero demurrage rule | Delay 48h vs Delay 0h | Zero change in freight/fuel monetary cost | Identical total cost | **PASS** |
| `COST-005` | USD_PER_DAY charter hire expansion | 4 extra port days at $20,000/day | $80,000 additional hire cost | $80,000 exact | **PASS** |
| `COST-006` | Invalid parameter error raising | Negative speed, cargo volume, or freight | `ValueError` with clear message | `ValueError` raised | **PASS** |

---

### C. Risk Evaluation Unit Tests (`tests/unit/domain/test_risk.py`)

| Test ID | Test Description | Input Conditions | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|
| `RISK-001` | HIGH congestion risk | `CongestionLevel.HIGH` | `RiskLevel.HIGH` | `HIGH` | **PASS** |
| `RISK-002` | Severe delay risk | `delay_hours = 48.0` | `RiskLevel.HIGH` | `HIGH` | **PASS** |
| `RISK-003` | Forecast spread risk | `forecast_spread_pct = 30.0` | `RiskLevel.HIGH` | `HIGH` | **PASS** |
| `RISK-004` | MEDIUM congestion risk | `CongestionLevel.MEDIUM` | `RiskLevel.MEDIUM` | `MEDIUM` | **PASS** |
| `RISK-005` | Moderate delay risk | `delay_hours = 24.0` | `RiskLevel.MEDIUM` | `MEDIUM` | **PASS** |
| `RISK-006` | LOW risk baseline | `CongestionLevel.LOW, delay=0, spread=5%` | `RiskLevel.LOW` | `LOW` | **PASS** |

---

### D. FastAPI Contract & Route Tests (`tests/api/test_scenarios_api.py`)

| Test ID | Test Description | Endpoint & Payload | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|
| `API-001` | Get scenario defaults | `GET /api/v1/scenarios/defaults` | 200 OK, 3 presets | 200 OK, 3 presets | **PASS** |
| `API-002` | Run canonical scenarios | `POST /api/v1/scenarios/run-canonical` | 200 OK, BASELINE, ADVERSE, FAVORABLE | 200 OK, complete set | **PASS** |
| `API-003` | Evaluate custom scenario | `POST /api/v1/scenarios/evaluate` | 200 OK, comparison deltas | 200 OK, deltas returned | **PASS** |
| `API-004` | Negative input validation | `POST /api/v1/scenarios/evaluate` (volume=-500) | 422 Unprocessable Entity | 422 Unprocessable Entity | **PASS** |

---

### E. End-to-End & Integration Tests

| Test ID | Test Description | Scope | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|
| `INT-001` | Scenario Cost Integration (MT) | Shocks vs. cost breakdown | Shocks apply to correct components | Perfect match | **PASS** |
| `INT-002` | Scenario Cost Integration (DAY) | Shocks vs. daily charter hire | Shocks expand vessel-days & rate | Perfect match | **PASS** |
| `INT-003` | Forecast boundary integration | Quantile spread $\to$ scenario risk | Spread widens risk rating | Risk elevates to HIGH | **PASS** |
| `INT-004` | Feasibility boundary integration | Feasible vessel filter $\to$ scenario inputs | Feasible vessels calculate cleanly | Successful evaluation | **PASS** |
| `E2E-001` | Full decision workflow lifecycle | Cargo $\to$ Feasibility $\to$ Forecast $\to$ Cost $\to$ Scenario $\to$ Recommendation | Complete decision result with risk | Valid decision payload | **PASS** |
| `DB-001` | Scenario persistence & query | Scenario repository insert & query | Stored scenarios match input IDs | 3 records retrieved | **PASS** |
| `DB-002` | Scenario defaults CSV integrity | `scenario_defaults.csv` integrity | Exact 3 canonical rows present | Exact match | **PASS** |
| `NEG-001` | Zero cargo volume edge case | `cargo_volume_mt = 0` | Safe failure, `ValueError` | `ValueError` raised | **PASS** |
| `NEG-002` | Negative cargo volume edge case | `cargo_volume_mt = -50000` | Safe failure, `ValueError` | `ValueError` raised | **PASS** |
| `NEG-003` | Zero vessel speed edge case | `speed_knots = 0` | Safe failure, `ValueError` | `ValueError` raised | **PASS** |
| `NEG-004` | Negative waiting hours edge case | `origin_waiting_hours = -10` | Safe failure, `ValueError` | `ValueError` raised | **PASS** |
| `NEG-005` | Large multi-voyage parcel (250k MT) | 250,000 MT parcel on Panamax | 4 voyages, 144h wait, 96h delay | Perfect 4-voyage math | **PASS** |
