# DockTech Freight Forecaster - Model Card

## Ownership
- Member: Swaraj (Member 2)
- Responsibility: Freight Forecasting + ML + Model Evaluation
- Model version: `docktech-ridge-ar-v1`

## Purpose
Forecast freight rates for a selected route, vessel class, and freight unit over 7, 30, or 90 days. The forecast is decision-support input for the DockTech backend; it does not execute chartering decisions.

## Data
Primary source: `data/reference/freight_rates.csv`.
The supplied project data is synthetic/demo data. It must not be represented as live SAIL commercial data.

Canonical grain: observation date + route + vessel class + freight unit.
Data coverage used: 2025-12-31 (source data through this date).

## Chronological periods
- Initial model-fitting period for validation: 2024-01-01 through 2025-04-30.
- Validation/model-selection period: 2025-05-01 through 2025-08-31.
- Final serving Ridge fit uses observations through 2025-08-31; this is strictly before the final test.
- Independent final test period: 2025-09-01 through 2025-12-31.
- No random shuffling. The evaluation is a chronological one-step-ahead walk-forward backtest: each scored date uses only prior observations as lag inputs.

## Models and selection
### Baseline
7-day seasonal naive forecast: the observed value from seven days earlier.

### Improved model
A separate Ridge autoregression model is trained for each route/vessel/freight-unit series. Features include lagged values (1, 2, 3, 7, 14, 28), shifted rolling statistics (7, 14, 28), and calendar/trend features. Ridge alpha remains 1.0.

For each series, both candidates are compared using validation MAE only. The candidate with lower validation MAE is selected for serving; `seasonal_naive_7d` wins ties. Selection was finalized before final-test scoring. The Ridge models are then refit using all observations through validation end. Final-test metrics do not change the selection map. Selected counts: 0 baseline and 336 Ridge.

## Evaluation results
Values below are macro averages of per-series metrics across 336 series. Detailed per-series figures and period labels are in `models/metadata/evaluation_metrics.csv`.

| Period / candidate | MAE | RMSE | MAPE (%) | Directional accuracy (%) |
|---|---:|---:|---:|---:|
| Validation - seasonal naive (selection) | 551.840882 | 802.796111 | 6.245189 | 29.498161 |
| Validation - Ridge | 126.314795 | 239.773783 | 1.464900 | 43.435443 |
| Validation - selected by validation | 126.314795 | 239.773783 | 1.464900 | 43.435443 |
| Final test - seasonal naive | 562.997585 | 635.808284 | 5.588699 | 21.667642 |
| Final test - Ridge | 77.887823 | 96.948548 | 0.734140 | 77.859094 |
| Final test - selected by validation | 77.887823 | 96.948548 | 0.734140 | 77.859094 |

Evaluation artifacts generated: 2026-09-29T09:55:42.722149+00:00.
These results use the supplied synthetic dataset and are not commercial performance claims.

## Uncertainty
The service produces scenario bounds from the frozen `data/reference/scenario_defaults.csv` freight adjustments. `BASELINE` (0% freight change) maps to the central forecast, `FAVORABLE` (the existing negative freight adjustment) maps to the lower forecast, and `ADVERSE` (the existing positive freight adjustment) maps to the upper forecast. These bounds are scenario uncertainty, not statistical confidence, and are floored at zero for non-negative freight rates.

## Forecast point contract
Each point includes `forecast_date`, `central`, `lower`, `upper`, `freight_unit`, `model_version`, and `training_data_end_date`. The serialized `date` key remains as a backward-compatible alias for `forecast_date`.

## Limitations
- Synthetic freight observations are not live market data.
- No paid broker/index/AIS feeds are used.
- Evaluation covers the available 2025-05-01 through 2025-12-31 holdout span, split into validation and final test; longer market regimes are not represented.
- Forecast quality can change when data distribution changes.
- A forecast is not a chartering instruction; human review remains required.
