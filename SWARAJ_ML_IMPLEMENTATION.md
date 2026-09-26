# Swaraj — Member 2 Implementation Summary

## Responsibility
Freight Forecasting + ML + Model Evaluation.

## What was implemented
- Leakage-safe freight data preparation and validation.
- 7-day seasonal-naive baseline.
- Improved Ridge autoregression model trained separately for each route/vessel/freight-unit series.
- Chronological evaluation using the frozen project split.
- Per-series model selection using the lower held-out MAE; the seasonal-naive baseline wins ties. The selected candidate is the one served for that series.
- MAE, RMSE, MAPE, and directional accuracy.
- 7/30/90-day recursive forecasts.
- Central/lower/upper forecast values using selected-model validation residual variability, scaled by the square root of the forecast day. If residual metadata is unavailable, historical daily-change variability is used; no fixed percentage band is applied.
- Versioned model artifact and reproducibility metadata.
- Metadata records model configuration and Python/ML-library versions used to train the artifact.
- Backend-facing `ForecastService.forecast(...)` interface.
- Unit tests for metrics, feature leakage, per-series evaluation and model selection, reproducibility, artifact/metadata behavior, and forecast service contracts.

## Frozen split
- Training: 2024-01-01 through 2025-06-30
- Validation/test: 2025-07-01 through 2025-12-31
- No random shuffling.

## Current evaluation on the supplied synthetic dataset
Aggregate mean across the 336 route/vessel/unit series:

| Metric | Seasonal naive | Ridge autoregression |
|---|---:|---:|
| MAE | 553.34 | 108.79 |
| RMSE | 628.36 | 133.49 |
| MAPE | 5.66% | 1.10% |
| Directional accuracy | 22.05% | 50.22% |

MAE/RMSE combine USD/MT and USD/day and therefore should not be interpreted as a single commercial-unit score. Unit-specific results are stored in `models/metadata/evaluation_metrics.csv`.

These results are on the project's synthetic dataset only and must not be presented as live SAIL commercial performance.

## Run training

```bash
python -m ml.train
```

Outputs:
- `models/artifacts/freight_forecaster.joblib`
- `models/metadata/freight_forecaster.json`
- `models/metadata/evaluation_metrics.csv`

## Backend interface

```python
from ml.service import ForecastService

service = ForecastService()
result = service.forecast(
    route_id="NEWCASTLE_PARADIP_THERMAL",
    vessel_class_id="PANAMAX",
    freight_unit="USD_PER_MT",
    horizon=30,
)
```

The service returns structured forecast points containing date, central, lower, upper, freight unit, model version, and training-data end date.
Each point exposes `forecast_date` and retains `date` as a backward-compatible alias. Model selection is recorded in `models/metadata/freight_forecaster.json`; per-series metrics remain in `models/metadata/evaluation_metrics.csv`.

## Important boundary
This module does not implement React, recommendation logic, vessel-port feasibility, scenario definitions, database creation, or live freight APIs. Those remain outside Member 2's responsibility.
