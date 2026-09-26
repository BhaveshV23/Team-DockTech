# DockTech Freight Forecaster — Model Card

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

## Time split
- Training: 2024-01-01 to 2025-06-30
- Validation/test: 2025-07-01 to 2025-12-31
- No random shuffling.

## Models and selection
### Baseline
7-day seasonal naive forecast: the value from seven days earlier.

### Improved model
A separate Ridge autoregression model is trained for each route/vessel/freight-unit series. Features include lagged values (1, 2, 3, 7, 14, 28), shifted rolling statistics (7, 14, 28), and calendar/trend features.

For each series, the baseline and Ridge model are evaluated on the same chronological held-out period. The candidate with the lower held-out MAE is selected for serving; the baseline is selected on ties. The chosen model for each series and metrics for the selected candidates are recorded in `freight_forecaster.json`. No cross-unit aggregate is used for the per-series decision.

## Evaluation
Metrics:
- MAE
- RMSE
- MAPE
- Directional Accuracy

The current aggregate results are stored in `models/metadata/evaluation_metrics.csv` and were produced from the supplied synthetic dataset. They are not commercial performance claims.

## Uncertainty
The service returns central/lower/upper values using the selected model's route/vessel/unit held-out residual standard deviation, scaled by the square root of the forecast day. If that residual value is unavailable, historical daily-change variability is used. Bounds are floored at zero for non-negative freight rates. These are approximate uncertainty bounds, not statistical confidence statements; no fixed percentage band is used.

## Forecast point contract
Each point includes `forecast_date`, `central`, `lower`, `upper`, `freight_unit`, `model_version`, and `training_data_end_date`. The serialized `date` key remains as a backward-compatible alias for `forecast_date`.

## Limitations
- Synthetic freight observations are not live market data.
- No paid broker/index/AIS feeds are used.
- Forecast quality can change when data distribution changes.
- A forecast is not a chartering instruction; human review remains required.
