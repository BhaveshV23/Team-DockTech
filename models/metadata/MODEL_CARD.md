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

## Models
### Baseline
7-day seasonal naive forecast: the value from seven days earlier.

### Improved model
A separate Ridge autoregression model is trained for each route/vessel/freight-unit series. Features include lagged values (1, 2, 3, 7, 14, 28), shifted rolling statistics (7, 14, 28), and calendar/trend features.

## Evaluation
Metrics:
- MAE
- RMSE
- MAPE
- Directional Accuracy

The current aggregate results are stored in `models/metadata/evaluation_metrics.csv` and were produced from the supplied synthetic dataset. They are not commercial performance claims.

## Uncertainty
The service returns central/lower/upper values using route/vessel/unit validation residual variability. These are prediction bounds for the demo and are not confidence statements.

## Limitations
- Synthetic freight observations are not live market data.
- No paid broker/index/AIS feeds are used.
- Forecast quality can change when data distribution changes.
- A forecast is not a chartering instruction; human review remains required.
