# Synthetic Data Design — DockTech V1

## 1. Purpose

This document defines the architecture, mathematical principles, configuration structure, and generation methodology for the synthetic reference datasets of **DockTech V1**.

DockTech relies on representative synthetic data for its SIH 2026 prototype evaluation, algorithm validation, and end-to-end demonstration. Because real-world commercial freight fixtures, proprietary port telemetry, and confidential chartering contracts are not publicly accessible at the required resolution, synthetic data provides a realistic, internally coherent, and reproducible planning environment.

The core design mandate is:
> **"V1 data must be small, controlled, and representative, but the generation architecture must support adding new ports, berths, routes, vessel classes, commodities, historical periods, and future proxy/actual data without redesigning the generator, data contracts, or database foundation."**

This document specifies **how** data is to be generated. It does not implement code or generate CSV files.

---

## 2. Source-of-Truth Hierarchy

All data generation designs must strictly adhere to the project source-of-truth hierarchy:

```text
PRD.md (Product Requirements & Business Goals)
  ↓
DATA_DICTIONARY.md (Frozen Canonical Data Contract & Semantics)
  ↓
ARCHITECTURE.md (System Architecture, Boundaries & Workflows)
  ↓
SYNTHETIC_DATA_DESIGN.md (Data Generation Architecture & Math Models)
  ↓
Generated Synthetic Datasets (data/reference/*.csv)
```

- **`PRD.md`** governs product goals, user personas, operational scope, and functional requirements.
- **`DATA_DICTIONARY.md`** is the frozen canonical contract for dataset schemas, column names, data types, canonical units, controlled vocabularies, relational integrity, multi-voyage turnaround formulas, and provenance labels.
- **`ARCHITECTURE.md`** governs system layers, service boundaries, file organization, Supabase PostgreSQL usage, and generator/validator/seeder lifecycle separation.
- **`SYNTHETIC_DATA_DESIGN.md`** defines the stochastic and structural processes that produce datasets satisfying the above three specifications. It must never alter schemas, rename columns, or introduce contradictory domain rules.

---

## 3. Synthetic Data Design Principles

1. **Deterministic & Fully Reproducible:** Given the same generator version, dependency versions, configuration, master seed, and deterministic ordering rules, the generator is designed to produce identical dataset values and deterministic row ordering. Checksums can verify the integrity of a specific generated artifact.
2. **Configuration-Driven:** All structural dimensions (ports, berths, vessels, routes, parameters, coefficients, dates) reside in structured configuration rather than hardcoded logic.
3. **Internally & Referentially Consistent:** Every foreign key must resolve. Route distances, sailing days, vessel speeds, handling rates, and multi-voyage requirements must be mathematically and physically aligned.
4. **Temporally Coherent:** Time-series datasets (freight rates, commodity benchmarks, bunker fuel, port activity) must reflect realistic market dynamics—including autocorrelation, seasonality, cyclical regimes, and controlled volatility—rather than white noise.
5. **Physically Plausible (Not Claimed as Real):** Vessel dimensions must scale logically with DWT. Route distances must reflect approximate nautical planning benchmarks. However, all data is explicitly synthetic and must never be presented as official hydrographic or commercial figures.
6. **Provenance-Aware:** Every generated record carries mandatory metadata (`source = 'SYNTHETIC_GENERATOR_V1'` and `data_type = 'SYNTHETIC'`).
7. **Decoupled Architecture:** The generator is an offline batch utility. It has zero runtime dependencies on Supabase, FastAPI, React, SQL databases, or active ML training scripts.
8. **Scalable & Extensible:** Adding a new port, vessel subclass, or trade lane requires updating configuration definitions, not refactoring generation algorithms.

---

## 4. V1 Dataset Inventory

The generation pipeline targets exactly the 9 canonical reference CSV datasets defined in `DATA_DICTIONARY.md`:

```text
data/reference/
├── ports.csv                # Port planning constraints & baseline turnaround
├── berths.csv               # Berth physical limits & commodity specialization
├── vessel_classes.csv       # Vessel technical specs, dimensions & fuel burn
├── routes.csv               # Trade lanes, nautical distances & sailing baselines
├── freight_rates.csv        # Historical time-series freight rate observations
├── commodity_prices.csv     # Historical coal benchmark market price series
├── fuel_prices.csv          # Historical marine bunker fuel price series
├── port_activity.csv        # Daily port congestion, arrivals & waiting hours
└── scenario_defaults.csv    # Predefined stress-testing scenario presets
```

---

## 5. Dataset Categories

The 9 reference datasets are organized into three distinct architectural categories:

| Category | Datasets | Nature & Update Frequency | Primary Role in System |
|---|---|---|---|
| **Static Reference Data** | `ports.csv`<br>`berths.csv`<br>`vessel_classes.csv`<br>`routes.csv` | Static infrastructure specifications and navigational baselines; versioned via repository releases. | Governs physical feasibility, trade lane validation, and baseline voyage planning. |
| **Time-Series Data** | `freight_rates.csv`<br>`commodity_prices.csv`<br>`fuel_prices.csv`<br>`port_activity.csv` | Historical daily observations across routes, commodities, fuels, and ports. | Primary input for ML forecasting models, backtesting, cost lookups, and congestion risk scoring. |
| **Scenario Configuration** | `scenario_defaults.csv` | Predefined parameter adjustment presets (`BASELINE`, `ADVERSE`, `FAVORABLE`). | Baseline configurations for sensitivity analysis and operational stress testing. |

---

## 6. Configuration Architecture

The generator must consume a unified, hierarchical configuration object (`SyntheticDataConfig`). Adding entities or modifying simulation behavior is achieved through configuration adjustments:

```text
SyntheticDataConfig
├── global_seed: int (26006)
├── history:
│   ├── start_date: "2024-01-01"
│   ├── end_date: "2025-12-31"
│   └── frequency: "DAILY"
├── geography:
│   ├── origin_ports: list[PortConfig]
│   └── destination_ports: list[PortConfig]
├── berths: list[BerthConfig]
├── vessel_classes: list[VesselClassConfig]
├── commodities: list[CommodityConfig]
├── routes: list[RouteConfig]
├── time_series_models:
│   ├── freight_rates: FreightModelConfig
│   ├── commodity_prices: CommodityModelConfig
│   ├── fuel_prices: FuelModelConfig
│   └── port_activity: PortActivityModelConfig
└── scenarios: list[ScenarioConfig]
```

Algorithms read this configuration structure sequentially. No entity attributes, baseline values, or distribution parameters may be hardcoded inside procedural generation loops.

---

## 7. Deterministic ID Strategy & Seed Specification

### Canonical Seed
- **Fixed V1 Master Seed:** `26006` (derived from SIH Problem Statement ID `26006`).
- **Rule:** Given the same generator version, runtime dependencies, configuration parameters, and master seed `26006`, the generation script deterministically outputs identical dataset records and deterministic row ordering. Altering the seed produces an alternate, statistically sound realization of the synthetic universe.

### ID Conventions (Strictly Aligned with `DATA_DICTIONARY.md`)
1. **Reference Entities (Stable Natural Keys):**
   - Ports: Uppercase snake_case string (`PARADIP`, `NEWCASTLE`, `SAGAR_SANDHEADS`).
   - Berths: Port-prefixed identifier (`PARADIP_BERTH_1`, `NEWCASTLE_BERTH_2`).
   - Vessel Classes: Controlled class token (`HANDYSIZE`, `SUPRAMAX`, `ULTRAMAX`, `PANAMAX`, `KAMSARMAX`, `CAPESIZE`).
   - Routes: Uppercase composite descriptor (`NEWCASTLE_PARADIP_THERMAL`).
   - Scenarios: Controlled scenario token (`BASELINE`, `ADVERSE`, `FAVORABLE`).
2. **Time-Series Records (Deterministic Sequential Keys):**
   - `freight_rates`: Formatted sequential identifier `FR_000001`, `FR_000002`, ...
   - `commodity_prices`: Formatted sequential identifier `CP_000001`, `CP_000002`, ...
   - `fuel_prices`: Formatted sequential identifier `FP_000001`, `FP_000002`, ...
   - `port_activity`: Formatted sequential identifier `PA_000001`, `PA_000002`, ...
3. **No Non-Deterministic UUIDs:** Python `uuid.uuid4()` must **never** be used during reference dataset generation, as it destroys run-to-run reproducibility.

---

## 8. Geographic Scope

The V1 geographic scope models critical international coal procurement corridors connecting major overseas export terminals to steel plants and power utilities on India's East Coast.

> [!NOTE]
> **V1 Default Configuration Scope vs. Architectural Capability:**  
> The 15 ports (8 origin ports and 7 destination ports) and 28 trade routes defined below represent the **Default V1 Synthetic Data Configuration**. These choices provide a rich, representative universe for SIH 2026 evaluation and algorithm benchmarking; they are **not architectural, schema, or database limits**. The canonical schemas, generator architecture, and downstream services are designed to support adding, removing, or modifying ports, routes, commodities, and vessel classes purely via configuration files, without requiring database schema redesign or application refactoring.

### Origin Loading Ports (Overseas)
| Port ID | Port Name | Country | Geographic Region |
|---|---|---|---|
| `NEWCASTLE` | Newcastle | Australia | Oceania / Pacific |
| `GLADSTONE` | Gladstone | Australia | Oceania / Pacific |
| `HAMPTON_ROADS` | Hampton Roads | USA | North America / Atlantic |
| `BALTIMORE` | Baltimore | USA | North America / Atlantic |
| `MAPUTO` | Maputo | Mozambique | East Africa / Indian Ocean |
| `NACALA` | Nacala | Mozambique | East Africa / Indian Ocean |
| `TABONEO` | Taboneo | Indonesia | Southeast Asia / Pacific |
| `SAMARINDA` | Samarinda | Indonesia | Southeast Asia / Pacific |

### Destination Discharge Ports (India East Coast)
| Port ID | Port Name | Country | Geographic Region |
|---|---|---|---|
| `PARADIP` | Paradip | India | East Coast India (Odisha) |
| `VISAKHAPATNAM` | Visakhapatnam | India | East Coast India (Andhra Pradesh) |
| `GANGAVARAM` | Gangavaram | India | East Coast India (Andhra Pradesh) |
| `GOPALPUR` | Gopalpur | India | East Coast India (Odisha) |
| `DHAMRA` | Dhamra | India | East Coast India (Odisha) |
| `SAGAR_SANDHEADS` | Sagar-Sandheads | India | East Coast India (West Bengal anchorage) |
| `HALDIA` | Haldia | India | East Coast India (West Bengal dock) |

*Note: In accordance with `DATA_DICTIONARY.md`, the canonical identifier for the Hooghly anchorage is `SAGAR_SANDHEADS`.*

---

## 9. Commodity Scope

DockTech V1 models the two bulk energy and metallurgical commodities critical to Indian steelmakers and thermal power utilities:

| Commodity Token | Description | Benchmark Market Series |
|---|---|---|
| `THERMAL_COAL` | Non-coking steam coal for power generation | `NEWCASTLE_BENCHMARK` |
| `COKING_COAL` | Metallurgical coal for blast furnace steelmaking | `PREMIUM_COKING` |

### Extensibility Rule:
Adding a future commodity (e.g., `IRON_ORE` or `LIMESTONE`) requires adding the token to the configuration vocabulary, provisioning compatible berths in `berths.csv`, adding route records in `routes.csv`, and configuring its benchmark series in `commodity_prices.csv`. No database schema or code modifications are required.

---

## 10. Vessel Scope

The generator models six canonical dry-bulk carrier classes:

| Vessel Class ID | Class Name | Representative DWT Range (MT) | Representative Cargo Capacity (MT) | Typical Draft (m) | Service Speed (kn) | Daily Fuel Burn (MT/day) |
|---|---|---|---|---|---|---|
| `HANDYSIZE` | Handysize | 28,000 – 38,000 | 32,000 | 10.2 | 13.0 | 22.0 |
| `SUPRAMAX` | Supramax | 50,000 – 58,000 | 53,000 | 12.2 | 14.0 | 28.0 |
| `ULTRAMAX` | Ultramax | 60,000 – 65,000 | 61,000 | 13.0 | 14.0 | 30.0 |
| `PANAMAX` | Panamax | 68,000 – 78,000 | 72,000 | 14.2 | 14.0 | 34.0 |
| `KAMSARMAX` | Kamsarmax | 80,000 – 85,000 | 79,000 | 14.5 | 14.0 | 36.0 |
| `CAPESIZE` | Capesize | 160,000 – 185,000 | 170,000 | 18.2 | 14.5 | 52.0 |

*Rules:*
- In all classes: $\text{cargo\_capacity\_mt} < \text{dwt\_max\_mt}$.
- Representative specifications must align with `DATA_DICTIONARY.md`.

---

## 11. Port and Berth Generation Architecture

### Feasibility Hierarchy
Generation must reflect the three-tier feasibility logic defined in `ARCHITECTURE.md`:
$$\text{Port Planning Envelope} \longrightarrow \text{Berth Commodity & Limits} \longrightarrow \text{Two-Ended Vessel Feasibility}$$

```text
ports.csv (General Planning Envelope: max LOA, beam, draft, handling rate)
   │
   └── berths.csv (Authoritative Operational Layer: commodity-specific limits)
```

### Operational Rules for Generator:
1. **Berth Draft $\le$ Port Draft:** For every berth, `berths.max_draft_m <= ports.max_draft_m`.
2. **Commodity Specialization:** Each berth record explicitly specifies `commodity = 'THERMAL_COAL'` or `'COKING_COAL'`. Multipurpose berths are represented as separate distinct berth rows per handled commodity.
3. **Intentional Feasibility Diversity:**
   - Deepwater ports (`GANGAVARAM`, `DHAMRA`) must have berths with draft $\ge 18.5\text{ m}$ to accommodate `CAPESIZE`.
   - Shallow/riverine ports (`HALDIA`, `SAGAR_SANDHEADS`) must have draft constraints between $10.5\text{ m}$ and $12.5\text{ m}$, ensuring that `CAPESIZE` and `KAMSARMAX` are rejected.
   - This intentional contrast is mandatory so automated tests and product demos can exercise both acceptance and rejection pathways.
4. **Failure-Safe Behavior:** The generator must include ports where certain commodities have no assigned berth, allowing validation of the `INSUFFICIENT_FEASIBILITY_DATA` response.

---

## 12. Route Generation Architecture

Routes represent viable trade corridors connecting loading origins to Indian discharge terminals. In the default V1 synthetic data configuration, exactly 28 routes are defined across the 15-port geography. As with the port universe, this 28-route scope is a configuration choice for V1, not a permanent system or architectural limit.

### Route Grain Standard
- **Grain:** Exactly one row per unique `origin_port_id + destination_port_id + commodity`.
- **Integrity Rule:** `origin_port_id != destination_port_id`.
- Multiple commodities between the same port pair yield separate route records (e.g., `NEWCASTLE_PARADIP_THERMAL` and `NEWCASTLE_PARADIP_COKING`).

### Navigational Plausibility Targets
Route distances (`distance_nm`) must reflect approximate realistic nautical waypoints rather than arbitrary numbers:
- Australia East Coast (`NEWCASTLE`, `GLADSTONE`) to India East Coast: $\approx 5,200 - 5,600\text{ nm}$.
- Indonesia (`TABONEO`, `SAMARINDA`) to India East Coast: $\approx 2,100 - 2,600\text{ nm}$.
- Southern Africa (`MAPUTO`, `NACALA`) to India East Coast: $\approx 3,900 - 4,400\text{ nm}$.
- US East Coast (`HAMPTON_ROADS`, `BALTIMORE`) via Cape of Good Hope: $\approx 11,500 - 12,200\text{ nm}$.

### Sailing Baseline Calculation:
$$\text{typical\_sailing\_days} = \text{round}\left(\frac{\text{distance\_nm}}{14.0 \times 24}, 1\right)$$

*Note: Distances and typical sailing days are representative planning targets, not certified hydrographic measurements.*

---

## 13. Freight-Rate Generation Requirements

Freight rates are the primary training dataset for the ML forecasting models.

### Operational Requirements:
- **Canonical Units:** Rates are generated in `USD_PER_MT` (voyage freight) and `USD_PER_DAY` (Time Charter Equivalent).
- **No Mixed Observation Series:** For a given `(observation_date, route_id, vessel_class_id, freight_unit)`, there is exactly one observation.
- **Support for Forecasting Horizons:** Data must provide sufficient temporal continuity and signal richness to train and evaluate 7-day, 30-day, and 90-day predictive models.
- **Chronological Split Support:** Data must allow seamless partitioning into training, validation, and test segments without data leakage.

### Expected Record Count Derivation:
The freight-rate dataset represents the full Cartesian combination across all operational dimensions:
$$\text{Total Records} = 28\text{ routes} \times 6\text{ vessel classes} \times 2\text{ freight units} \times 731\text{ observation dates} = 245,616\text{ records}$$
- **Routes:** 28 configured trade lanes.
- **Vessel Classes:** 6 bulk carrier classes (`HANDYSIZE`, `SUPRAMAX`, `ULTRAMAX`, `PANAMAX`, `KAMSARMAX`, `CAPESIZE`).
- **Freight Units:** 2 units (`USD_PER_MT` voyage freight, `USD_PER_DAY` TCE).
- **Date Range:** 731 continuous calendar days (2024-01-01 through 2025-12-31, comprising 366 days in leap year 2024 and 365 days in 2025).
- **Cartesian Completeness:** Every valid combination of `(route_id, vessel_class_id, freight_unit, observation_date)` possesses exactly one observation, guaranteeing complete time-series slices for forecasting models.

---

## 14. Freight Time-Series Mathematical Model

To produce realistic, learnable time series without independent white noise, freight rates are generated via an additive-multiplicative structural decomposition:

$$R(t) = \left[ B_0 + T(t) + S(t) + E(t) \right] \times M_v \times M_r + \epsilon(t)$$

### Model Components:
1. **Base Level ($B_0$):** Baseline freight rate determined by route distance and vessel class efficiency (e.g., $\$12.00\text{/MT}$ for Panamax on Australia-India).
2. **Deterministic Trend ($T(t)$):** Low-frequency macro cycle capturing global dry-bulk demand expansion and fleet supply balance:
   $$T(t) = A_{\text{trend}} \sin\left(\frac{2\pi t}{P_{\text{macro}}}\right) + \beta t$$
3. **Seasonal Cycle ($S(t)$):** Captures seasonal weather and procurement peaks (e.g., monsoon impact in India during Q3, winter power demand peaks in Q1):
   $$S(t) = A_{\text{annual}} \cos\left(\frac{2\pi d_{\text{year}}}{365.25} + \phi\right)$$
4. **Controlled Market Regime Shocks ($E(t)$):** Regime-switching jump process simulating periodic freight market tightness or geopolitical rerouting:
   $$E(t) = \sum_k J_k \cdot \exp\left(-\frac{t - t_k}{\tau_k}\right) \cdot \mathbb{I}(t \ge t_k)$$
5. **Cross-Sectional Multipliers ($M_v, M_r$):**
   - Vessel efficiency multiplier $M_v$ (economies of scale reduce Capesize rate per tonne relative to Supramax).
   - Route canal/congestion multiplier $M_r$.
6. **Autoregressive Residual Noise ($\epsilon(t)$):**
   $$\epsilon(t) = \rho \epsilon(t-1) + \sigma \sqrt{1 - \rho^2} \cdot \eta(t), \quad \eta(t) \sim \mathcal{N}(0, 1)$$
   Autocorrelation parameter $\rho \approx 0.85 - 0.92$ ensures day-to-day rate continuity rather than jagged noise.

---

## 15. Freight Cross-Sectional Relationships

The synthetic generator must enforce economic realism across classes and routes:

1. **Economies of Scale ($/MT):**
   $$\text{Rate}_{\text{CAPESIZE}} (\$/\text{MT}) < \text{Rate}_{\text{PANAMAX}} (\$/\text{MT}) < \text{Rate}_{\text{SUPRAMAX}} (\$/\text{MT})$$
   A Capesize vessel transports cargo at a lower cost per metric tonne than smaller bulk carriers.
2. **Daily Charter Hire ($/day TCE):**
   $$\text{Rate}_{\text{CAPESIZE}} (\$/\text{day}) > \text{Rate}_{\text{PANAMAX}} (\$/\text{day}) > \text{Rate}_{\text{SUPRAMAX}} (\$/\text{day})$$
   A Capesize commands a significantly higher daily time charter rate than a Supramax.
3. **Volatility Hierarchy:**
   Capesize freight rates must exhibit higher daily percentage volatility ($\sigma \approx 2.5\%$) than Panamax ($\sigma \approx 1.8\%$) and Supramax ($\sigma \approx 1.2\%$), replicating real shipping market behavior.

---

## 16. Historical Time Range & Temporal Continuity

- **Configured V1 Window:** 24 continuous calendar months (exactly 731 daily observations):
  - `start_date`: `2024-01-01`
  - `end_date`: `2025-12-31`
  - `frequency`: `DAILY`
  - **Date Count Calculation:** 2024 is a leap year with 366 days; 2025 contains 365 days. Total window length is $366 + 365 = 731$ calendar days.
- **Continuity Standard:** Zero missing dates across the simulation window. Time-series entries exist for all 731 days for every configured route, vessel class, and unit combination.
- **Evaluation Split Guidance:**
  - Training set: `2024-01-01` to `2025-06-30` (547 daily observations: 366 days in 2024 + 181 days in H1 2025)
  - Validation/Test set: `2025-07-01` to `2025-12-31` (184 daily observations in H2 2025)
  - Total: $547 + 184 = 731$ days.

---

## 17. Controlled Market Shock Regimes

To test model adaptiveness and recommendation heuristics (`FIX_NOW` vs. `WAIT`), the generation window includes four controlled synthetic regimes:

| Regime Period | Target Dates | Regime Description | Impact on Freight Rates |
|---|---|---|---|
| **Regime 1: Baseline** | 2024-01-01 to 2024-07-31 | Balanced supply and demand; normal seasonal patterns. | Baseline drift $\pm 5\%$. |
| **Regime 2: Freight Spike** | 2024-08-01 to 2024-11-30 | Simulated vessel capacity shortage and port congestion shock. | Sharp surge (+30% to +45% over 60 days). |
| **Regime 3: Market Easing** | 2024-12-01 to 2025-05-31 | Supply easing, fleet repositioning, softening industrial demand. | Gradual downward correction (-25%). |
| **Regime 4: Volatile Sideways** | 2025-06-01 to 2025-12-31 | Range-bound freight market with heightened short-term volatility. | Rapid oscillation within $\pm 12\%$. |

*Note: Shocks are synthetic algorithmic scenarios designed for model validation; they do not represent real-world geopolitical events.*

---

## 18. Commodity Price Generation Architecture

Commodity prices serve as macroeconomic explanatory features for forecasting and procurement cost context.

### Generation Specifications:
- **Canonical Markets:**
  - `NEWCASTLE_BENCHMARK` for `THERMAL_COAL` (representative range: $\$120 - \$160\text{/MT}$).
  - `PREMIUM_COKING` for `COKING_COAL` (representative range: $\$220 - \$310\text{/MT}$).
- **Dynamics:** Commodity prices move slower than spot freight rates. They follow an autoregressive mean-reverting jump diffusion process:
  $$P_c(t) = P_c(t-1) + \theta (\mu_c - P_c(t-1)) + \sigma_c \epsilon_c(t)$$
  with mean reversion speed $\theta = 0.02$ and lower daily volatility ($\sigma_c \approx 0.6\%$).
- **Correlation:** Coal prices share a positive macro correlation ($\rho \approx 0.40$) with global freight cycles.
- **Expected Record Count:**
  $$\text{Total Records} = 2\text{ commodities} \times 1\text{ market series} \times 731\text{ dates} = 1,462\text{ records}$$

---

## 19. Fuel Price Generation Architecture

Marine bunker fuel prices drive the sea-going voyage cost engine.

### Generation Specifications:
- **Canonical Fuel Types:**
  - `VLSFO` (Very Low Sulphur Fuel Oil): Primary sea-going transit fuel (representative price range: $\$540 - \$680\text{/MT}$).
  - `MGO` (Marine Gas Oil): Auxiliary port operations and maneuvering fuel (representative price range: $\$720 - \$890\text{/MT}$).
- **V1 Cost Scope & MGO Status (Strict Demarcation):**
  - **Authoritative V1 Fuel Input:** In accordance with `DATA_DICTIONARY.md` and `ARCHITECTURE.md`, the V1 voyage cost calculation engine uses **`VLSFO` as its sole authoritative sea-going bunker fuel input**.
  - **MGO is Reference-Only:** `MGO` records are generated purely as an auxiliary, reference-only time series to support future port-emission or auxiliary-engine modeling.
  - **Exclusion Guarantees:**
    1. `MGO` is **NOT** used by the V1 voyage cost engine.
    2. `MGO` is **NOT** used by V1 scenario calculations (e.g., bunker fuel stress percentage applies exclusively to VLSFO).
    3. `MGO` is **NOT** used by V1 recommendation heuristics or charter evaluation logic.
  - Future developers and algorithms must never incorporate MGO into V1 cost formulas.
- **Cost Reference Date Lookup:**
  $$\text{Price}_{\text{VLSFO}} = \text{fuel\_prices.price\_value where fuel\_type = 'VLSFO' on or immediately before } \text{cost\_reference\_date}$$
  where $\text{cost\_reference\_date} = \text{forecast\_run.training\_data\_end\_date}$.
- **Expected Record Count:**
  $$\text{Total Records} = 2\text{ fuel types (VLSFO active, MGO reference-only)} \times 731\text{ observation dates} = 1,462\text{ records}$$

---

## 20. Port Activity Generation Architecture

Port activity captures time-varying operational congestion and vessel waiting times.

### Structural Relationships:
The generator models operational correlation across daily activity metrics:
$$\text{Arrivals } A(t) \longrightarrow \text{Waiting Hours } W(t) \longrightarrow \text{Turnaround Hours } T(t) \longrightarrow \text{Congestion Level}$$

1. **Daily Vessel Arrivals ($A(t)$):** Poisson distribution conditioned on port capacity:
   $$A(t) \sim \text{Poisson}(\lambda_{\text{port}}), \quad \lambda_{\text{port}} \in [4, 14]$$
2. **Average Waiting Time ($W(t)$):** Non-linear queuing function of arrival surge relative to baseline:
   $$W(t) = W_{\text{base}} \times \left( \frac{A(t)}{\lambda_{\text{port}}} \right)^{1.5} + \epsilon_w(t), \quad W(t) \ge 0$$
3. **Turnaround Time ($T(t)$):**
   $$T(t) = W(t) + T_{\text{handling\_base}} + \epsilon_t(t)$$
4. **Categorical Congestion Level:**
   $$\text{congestion\_level} = \begin{cases} \text{'LOW'}, & W(t) < 24.0\text{ h} \\ \text{'MEDIUM'}, & 24.0\text{ h} \le W(t) < 60.0\text{ h} \\ \text{'HIGH'}, & W(t) \ge 60.0\text{ h} \end{cases}$$
- **Expected Record Count:**
  $$\text{Total Records} = 15\text{ ports} \times 731\text{ observation dates} = 10,965\text{ records}$$

---

## 21. Scenario Defaults Generation Architecture

Predefined parameter sets for scenario analysis are generated into `scenario_defaults.csv`.

| Scenario ID | Scenario Name | Freight Change (%) | Fuel Change (%) | Delay Hours (h) | Port Congestion Level | Narrative Intent |
|---|---|---|---|---|---|---|
| `BASELINE` | Baseline | `0.0` | `0.0` | `0.0` | `MEDIUM` | Standard forward market expectations; zero applied stress. |
| `ADVERSE` | Adverse Market Shock | `25.0` | `15.0` | `48.0` | `HIGH` | Market spike, bunker fuel inflation, and severe port congestion. |
| `FAVORABLE` | Favorable Easing | `-15.0` | `-10.0` | `0.0` | `LOW` | Softening freight rates, lower bunker costs, and clear berths. |

*Storage Standard:* Percentage adjustments are stored as face values (`25.0` represents $+25\%$, `-15.0` represents $-15\%$).
*Expected Record Count:* Exactly 3 records.

---

## 22. Cross-Dataset Consistency & Dependency Graph

Generated datasets form an interconnected relational ecosystem. Generation must proceed according to the strict topological dependency graph:

```text
       [vessel_classes]     [ports]
              │             ┌──┴─────────────┐
              │             │                │
              │         [berths]          [routes]
              │                              │
              └─────────────┬────────────────┘
                            │
                     [freight_rates]

   [ports]                 [commodities]              [fuel]
      │                          │                       │
      ↓                          ↓                       ↓
[port_activity]          [commodity_prices]        [fuel_prices]

                     [scenario_defaults]
```

### Relational Integrity Invariants:
1. Every `berths.port_id` must exist in `ports.port_id`.
2. Every `routes.origin_port_id` and `routes.destination_port_id` must exist in `ports.port_id`.
3. Every `freight_rates.route_id` must exist in `routes.route_id`.
4. Every `freight_rates.vessel_class_id` must exist in `vessel_classes.vessel_class_id`.
5. Every `port_activity.port_id` must exist in `ports.port_id`.
6. For every route, `routes.commodity` must have compatible berths at both origin and destination.

---

## 23. Provenance Standards

Every synthetic dataset record carries two immutable provenance attributes:
- `data_type`: Explicitly set to string literal `'SYNTHETIC'`.
- `source`: Explicitly set to string literal `'SYNTHETIC_GENERATOR_V1'`.

No supplementary metadata columns may be added to reference CSV files, as this would violate the frozen table schema in `DATA_DICTIONARY.md`.

---

## 24. Reproducibility & Generation Manifest (Illustrative Template)

> [!IMPORTANT]
> **Illustrative Manifest Template:**  
> The JSON snippet below is an **illustrative manifest template** demonstrating the exact structure that the future generator utility (`generate_synthetic_data.py`) will produce upon execution:
> - **No synthetic dataset has been generated yet.**
> - The record counts shown are expected design values calculated deterministically from the V1 configuration parameters.
> - Actual generation timestamps and SHA-256 checksums will only exist after the generator script executes.
> - Actual generated record counts produced by the generator must be validated against these expected counts.

```json
{
  "generator_name": "DockTech Synthetic Generator",
  "generator_version": "1.0.0",
  "master_seed": 26006,
  "generation_timestamp": "<GENERATION_TIMESTAMP_ISO8601>",
  "history_start_date": "2024-01-01",
  "history_end_date": "2025-12-31",
  "record_counts": {
    "ports": 15,
    "berths": 32,
    "vessel_classes": 6,
    "routes": 28,
    "freight_rates": 245616,
    "commodity_prices": 1462,
    "fuel_prices": 1462,
    "port_activity": 10965,
    "scenario_defaults": 3
  },
  "checksums_sha256": {
    "ports.csv": "<CHECKSUM_SHA256>",
    "berths.csv": "<CHECKSUM_SHA256>",
    "vessel_classes.csv": "<CHECKSUM_SHA256>",
    "routes.csv": "<CHECKSUM_SHA256>",
    "freight_rates.csv": "<CHECKSUM_SHA256>",
    "commodity_prices.csv": "<CHECKSUM_SHA256>",
    "fuel_prices.csv": "<CHECKSUM_SHA256>",
    "port_activity.csv": "<CHECKSUM_SHA256>",
    "scenario_defaults.csv": "<CHECKSUM_SHA256>"
  }
}
```

### Deterministic Record Count Summary Table:

| Dataset | Generation Dimensions & Multipliers | Expected Rows | Primary Role / Semantics |
|---|---|---|---|
| `ports.csv` | 8 origin ports + 7 destination ports | **15** | Default V1 geography configuration |
| `berths.csv` | Specialized coal berths across all 15 ports | **32** | Authoritative operational feasibility layer |
| `vessel_classes.csv` | Dry-bulk carrier classes (Handysize to Capesize) | **6** | Technical vessel specifications & fuel burn |
| `routes.csv` | Active trade lanes across origin-destination-commodity | **28** | Trade corridors & nautical distance baselines |
| `freight_rates.csv` | 28 routes × 6 vessel classes × 2 units × 731 dates | **245,616** | Primary time-series for ML forecasting models |
| `commodity_prices.csv` | 2 commodities (Thermal & Coking Coal) × 731 dates | **1,462** | Macroeconomic benchmark feature series |
| `fuel_prices.csv` | 2 fuel types (VLSFO active, MGO reference-only) × 731 dates | **1,462** | VLSFO: active voyage cost; MGO: reference-only |
| `port_activity.csv` | 15 ports × 731 observation dates | **10,965** | Congestion, arrivals, and waiting time series |
| `scenario_defaults.csv` | Baseline, Adverse, Favorable stress presets | **3** | Predefined sensitivity & stress parameters |
| **Total Reference Records** | Across all 9 canonical reference datasets | **259,561** | Frozen V1 Synthetic Universe |

---

## 25. Validation Requirements (`validate_reference_data.py`)

A standalone validation utility must verify the generated CSV files before they can be committed or seeded into Supabase PostgreSQL.

### Mandatory Validation Checks:
1. **Schema & Header Completeness:** Every CSV file must possess exact headers matching `DATA_DICTIONARY.md` (no extra or missing columns).
2. **Zero Nulls in Required Fields:** No empty cells, `NaN`, or whitespace strings in required columns.
3. **Data Type & Format Validation:** Dates match `YYYY-MM-DD`; numeric fields parse cleanly as floating-point decimals or integers.
4. **Controlled Vocabulary Compliance:** Enum values strictly match canonical sets (`THERMAL_COAL`, `COKING_COAL`, `USD_PER_MT`, `USD_PER_DAY`, `VLSFO`, `MGO`, `LOW`, `MEDIUM`, `HIGH`, `SYNTHETIC`).
5. **Foreign Key Integrity:** Zero orphan records in `berths`, `routes`, `freight_rates`, or `port_activity`.
6. **Grain Uniqueness:** Zero duplicate rows at the declared natural grain (e.g., `(observation_date, route_id, vessel_class_id, freight_unit)` in `freight_rates`).
7. **Physical Dimension Bounds:** Positive dimensions (`max_loa_m > 0`, `max_beam_m > 0`, `max_draft_m > 0`, `speed_knots > 0`).
8. **Capacity Bounds:** For all vessel classes, `cargo_capacity_mt < dwt_max_mt`.
9. **Feasibility Precedence:** For all berths, `berths.max_draft_m <= ports.max_draft_m`.
10. **Temporal Continuity:** Exactly 731 continuous daily records per complete time-series slice (e.g., per route-vessel-unit combination, per commodity, per fuel, and per port) with zero missing dates across 2024-01-01 to 2025-12-31.
11. **Feasibility Coverage:** At least one vessel class is feasible, and at least one vessel class is infeasible, across configured test routes.
12. **Provenance Labels:** All rows carry `data_type = 'SYNTHETIC'` and `source = 'SYNTHETIC_GENERATOR_V1'`.
13. **Deterministic Record Count Verification:** Total row counts in generated CSVs must match exact expected design counts (e.g., exactly 245,616 rows in `freight_rates.csv`, 1,462 in `commodity_prices.csv`, 1,462 in `fuel_prices.csv`, 10,965 in `port_activity.csv`).

---

## 26. Scalability & Extension Rules

The architecture guarantees seamless expansion without altering the core schema, database migrations, or API contracts. The 15-port / 28-route / 6-vessel universe constitutes the V1 default dataset configuration; the underlying schemas, database structures, and generator algorithms impose no hard upper bounds on geography, fleet diversity, or temporal range:

| Extension Action | Required Configuration Changes | Architectural Impact |
|---|---|---|
| **Add a New Port** | Add port entry to `ports` configuration; add compatible berths in `berths` configuration; add trade lanes in `routes` configuration. | Zero schema or backend code changes. Automatically populated on re-seed. |
| **Add a New Berth** | Add berth configuration referencing existing `port_id` with specified dimensions and commodity. | Zero schema changes. Feasibility engine picks it up immediately. |
| **Add a Vessel Class** | Add vessel specs to `vessel_classes` configuration; include in time-series generator. | Zero schema changes. Feasibility and ranking evaluate the new class automatically. |
| **Add a Commodity** | Add commodity token to controlled vocabulary; add compatible berths, routes, and price benchmark series. | Zero schema changes. Normalized joins operate across the new token. |
| **Add a Route** | Add origin, destination, and commodity entry to `routes` configuration with nautical distance. | Zero schema changes. Model generates rates for the new lane. |
| **Extend History Window** | Adjust `history.start_date` or `end_date` in configuration and re-run generator. | Zero schema changes. Enables longer model training horizons. |
| **Alter Random Realization** | Update `global_seed` from `26006` to another integer. | Produces an independent statistical realization for stress testing. |
| **Replace with Actual Data** | Load real market observations with `data_type = 'ACTUAL'` and a specific `source` identifier. | Zero schema changes. Downstream models ingest identical column contracts. |

---

## 27. Generator and System Separation

The synthetic data pipeline operates strictly outside runtime services:

```text
[Offline Batch Pipeline]
generate_synthetic_data.py
       ↓
data/reference/*.csv
       ↓
validate_reference_data.py
       ↓
seed_database.py
       ↓
[Runtime Database]
Supabase PostgreSQL (public schema)
       ↓
[Runtime Application]
FastAPI Repositories & Services
       ↓
React + Vite UI Dashboard
```

- **Generator Independence:** The generator has no imports of FastAPI, Supabase client libraries, Pydantic API schemas, or frontend assets.
- **Persistence Boundary:** The generator outputs raw CSV files into `data/reference/`. Database insertion is the exclusive responsibility of `seed_database.py`.

---

## 28. Future Actual / Proxy Data Transition

DockTech V1 is deliberately architected for graceful evolution from synthetic demonstration to enterprise deployment:

```text
Phase 1: V1 Synthetic Prototype
data_type: 'SYNTHETIC' | source: 'SYNTHETIC_GENERATOR_V1'
       ↓
Phase 2: Hybrid / Proxy Validation
data_type: 'PROXY'     | source: 'BALTIC_EXCHANGE_INDEX' | 'PLATTS_COAL'
       ↓
Phase 3: Production Commercial System
data_type: 'ACTUAL'    | source: 'SAIL_FIXTURE_DATABASE' | 'PORT_AUTHORITY_API'
```

Because column definitions, natural keys, and units are strictly standardized, external ingestion scripts simply map real feeds into the canonical CSV format or insert them directly into Supabase PostgreSQL. Downstream forecasting engines and recommendation heuristics require zero re-engineering.

---

## 29. Recommended Generator Architecture & Execution Order

When implemented, `generate_synthetic_data.py` should follow a modular pipeline:

```text
1. Load & Validate SyntheticDataConfig
2. Initialize Master Random Number Generator (Seed = 26006)
3. Generate Static Reference Data:
   ├── Step 3.1: Generate ports.csv
   ├── Step 3.2: Generate berths.csv (depends on ports)
   ├── Step 3.3: Generate vessel_classes.csv
   └── Step 3.4: Generate routes.csv (depends on ports)
4. Generate Time-Series Data:
   ├── Step 4.1: Generate freight_rates.csv (depends on routes, vessel_classes)
   ├── Step 4.2: Generate commodity_prices.csv
   ├── Step 4.3: Generate fuel_prices.csv
   └── Step 4.4: Generate port_activity.csv (depends on ports)
5. Generate Scenario Presets:
   └── Step 5.1: Generate scenario_defaults.csv
6. Perform In-Memory Cross-Dataset Referential Integrity Check
7. Write Version-Controlled CSV Files to data/reference/
8. Generate data/reference/manifest.json (Checksums & Provenance)
```

---

## 30. V1 Scope Boundaries

To prevent scope creep and maintain development momentum, V1 synthetic data generation explicitly **excludes**:
- Modeling all global ports or non-Indian discharge destinations (the 15-port / 28-route scope serves as the V1 configuration baseline).
- Real-time AIS vessel trajectory simulations or transponder telemetry.
- Meteorological, hydrodynamic, or typhoon weather routing models.
- Individual vessel-level shipowner registries or IMO numbers.
- Automated charter party execution, escrow, or digital signatures.
- Fleet-wide repositioning or global multi-vessel fleet optimization.
- Live broker chat scraping or unstructured fixture text parsing.
- Temporal port-notice versioning (`effective_from` / `effective_to` tables).

---

## 31. Acceptance Criteria Checklist

The synthetic data design is complete and ready for implementation when:
- [x] All 9 canonical reference datasets are fully specified.
- [x] Exact schemas, data types, and units are delegated to `DATA_DICTIONARY.md`.
- [x] Fixed master seed `26006` is defined for deterministic reproducibility under matching runtime environments.
- [x] Configuration-driven architecture is established without hardcoded procedural logic.
- [x] Stable, deterministic natural ID strategy is established across all entities.
- [x] Multi-voyage turnaround and cost reference date standards from `DATA_DICTIONARY.md` are respected.
- [x] Time-series mathematical models combine base, trend, seasonality, shocks, and autocorrelated noise.
- [x] Cross-dataset relational dependency graph is formally mapped.
- [x] Strict provenance attributes (`data_type = 'SYNTHETIC'`, `source = 'SYNTHETIC_GENERATOR_V1'`) are enforced.
- [x] Standalone validation criteria (`validate_reference_data.py`) are detailed (including 731-day temporal continuity and 245,616 freight rate record counts).
- [x] Scalability rules for expanding ports, berths, vessels, and commodities are documented without architectural limits.
- [x] Smooth evolutionary path to actual/proxy commercial data is defined.
- [x] Complete separation between generator, database seeder, and runtime application is guaranteed.
- [x] Zero extraneous V1 infrastructure or unsupported external dependencies are introduced.
