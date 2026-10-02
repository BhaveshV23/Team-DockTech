from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import platform
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn

from .evaluation import evaluate_final_test, evaluate_models, write_evaluation
from .features import prepare_freight_data, make_features
from .model import train_improved_model, save_model

TRAIN_START = pd.Timestamp("2024-01-01")
SELECTION_TRAIN_END = pd.Timestamp("2025-04-30")
VALIDATION_START = pd.Timestamp("2025-05-01")
VALIDATION_END = pd.Timestamp("2025-08-31")
FINAL_TEST_START = pd.Timestamp("2025-09-01")
FINAL_TEST_END = pd.Timestamp("2025-12-31")
METRICS = ["mae", "rmse", "mape_pct", "directional_accuracy_pct"]
MODEL_VERSIONS = {
    "ridge_autoregression": "docktech-ridge-ar-v1",
    "seasonal_naive_7d": "docktech-seasonal-naive-7d-v1",
}


def _period_summary(metrics: pd.DataFrame, selected_models: dict[str, str]) -> dict:
    baseline = metrics[metrics.model == "seasonal_naive_7d"]
    improved = metrics[metrics.model == "ridge_autoregression"]
    selected_mask = [
        selected_models.get("||".join((row.route_id, row.vessel_class_id, row.freight_unit))) == row.model
        for row in metrics.itertuples()
    ]
    selected = metrics.loc[selected_mask]
    return {
        "baseline_mean": {name: float(baseline[name].mean()) for name in METRICS},
        "improved_mean": {name: float(improved[name].mean()) for name in METRICS},
        "selected_mean": {name: float(selected[name].mean()) for name in METRICS},
    }


def _unit_summary(metrics: pd.DataFrame, selected_models: dict[str, str]) -> dict:
    return {
        unit: _period_summary(metrics[metrics.freight_unit == unit], selected_models)
        for unit in sorted(metrics.freight_unit.unique())
    }


def _write_model_card(metadata: dict, path: str) -> None:
    validation = metadata["validation_metrics_summary"]
    final_test = metadata["final_test_metrics_summary"]

    def row(label: str, summary: dict) -> str:
        return "| " + label + " | " + " | ".join(
            f"{summary[name]:.6f}" for name in METRICS
        ) + " |"

    chosen = metadata["model_selection_counts"]
    card = f"""# DockTech Freight Forecaster - Model Card

## Ownership
- Member: Swaraj (Member 2)
- Responsibility: Freight Forecasting + ML + Model Evaluation
- Model version: `{metadata['model_version']}`

## Purpose
Forecast freight rates for a selected route, vessel class, and freight unit over 7, 30, or 90 days. The forecast is decision-support input for the DockTech backend; it does not execute chartering decisions.

## Data
Primary source: `data/reference/freight_rates.csv`.
The supplied project data is synthetic/demo data. It must not be represented as live SAIL commercial data.

Canonical grain: observation date + route + vessel class + freight unit.
Data coverage used: {metadata['data_as_of']} (source data through this date).

## Chronological periods
- Initial model-fitting period for validation: {metadata['initial_training_period']['start']} through {metadata['initial_training_period']['end']}.
- Validation/model-selection period: {metadata['validation_period']['start']} through {metadata['validation_period']['end']}.
- Final serving Ridge fit uses observations through {metadata['serving_model_training_period']['end']}; this is strictly before the final test.
- Independent final test period: {metadata['final_test_period']['start']} through {metadata['final_test_period']['end']}.
- No random shuffling. The evaluation is a chronological one-step-ahead walk-forward backtest: each scored date uses only prior observations as lag inputs.

## Models and selection
### Baseline
7-day seasonal naive forecast: the observed value from seven days earlier.

### Improved model
A separate Ridge autoregression model is trained for each route/vessel/freight-unit series. Features include lagged values (1, 2, 3, 7, 14, 28), shifted rolling statistics (7, 14, 28), and calendar/trend features. Ridge alpha remains 1.0.

For each series, both candidates are compared using validation MAE only. The candidate with lower validation MAE is selected for serving; `seasonal_naive_7d` wins ties. Selection was finalized before final-test scoring. The Ridge models are then refit using all observations through validation end. Final-test metrics do not change the selection map. Selected counts: {chosen['seasonal_naive_7d']} baseline and {chosen['ridge_autoregression']} Ridge.

## Evaluation results
Values below are macro averages of per-series metrics across {metadata['trained_series_count']} series. Detailed per-series figures and period labels are in `models/metadata/evaluation_metrics.csv`.

| Period / candidate | MAE | RMSE | MAPE (%) | Directional accuracy (%) |
|---|---:|---:|---:|---:|
{row('Validation - seasonal naive (selection)', validation['baseline_mean'])}
{row('Validation - Ridge', validation['improved_mean'])}
{row('Validation - selected by validation', validation['selected_mean'])}
{row('Final test - seasonal naive', final_test['baseline_mean'])}
{row('Final test - Ridge', final_test['improved_mean'])}
{row('Final test - selected by validation', final_test['selected_mean'])}

Evaluation artifacts generated: {metadata['evaluation_generated_at_utc']}.
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
"""
    Path(path).write_text(card, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Train and chronologically evaluate DockTech freight forecasting models")
    parser.add_argument("--data", default="data/reference/freight_rates.csv")
    parser.add_argument("--artifact", default="models/artifacts/freight_forecaster.joblib")
    parser.add_argument("--metadata", default="models/metadata/freight_forecaster.json")
    parser.add_argument("--metrics", default="models/metadata/evaluation_metrics.csv")
    parser.add_argument("--model-card", default="models/metadata/MODEL_CARD.md")
    args = parser.parse_args()

    df = prepare_freight_data(args.data)
    df = df[(df.observation_date >= TRAIN_START) & (df.observation_date <= FINAL_TEST_END)]
    if df.empty or df.observation_date.min() != TRAIN_START or df.observation_date.max() != FINAL_TEST_END:
        raise ValueError("Freight data must cover 2024-01-01 through 2025-12-31")

    selection_training_rows = df[
        (df.observation_date >= TRAIN_START) & (df.observation_date <= SELECTION_TRAIN_END)
    ]
    selection_model = train_improved_model(make_features(selection_training_rows, include_target=True))
    validation = evaluate_models(
        df,
        selection_model,
        SELECTION_TRAIN_END.date().isoformat(),
        VALIDATION_START.date().isoformat(),
        VALIDATION_END.date().isoformat(),
    )
    selected_models = validation["selected_models"]

    # Refit the fixed Ridge candidate with all observations available before
    # the final-test window. This is after selection and cannot use test rows.
    serving_training_rows = df[
        (df.observation_date >= TRAIN_START) & (df.observation_date <= VALIDATION_END)
    ]
    serving_model = train_improved_model(make_features(serving_training_rows, include_target=True))
    final_test = evaluate_final_test(
        df,
        serving_model,
        selected_models,
        VALIDATION_END.date().isoformat(),
        FINAL_TEST_START.date().isoformat(),
        FINAL_TEST_END.date().isoformat(),
    )

    trained_series = set(serving_model.models)
    validation_series = set(selected_models)
    final_test_series = {
        "||".join((row.route_id, row.vessel_class_id, row.freight_unit))
        for row in final_test["metrics"].itertuples()
    }
    if trained_series != validation_series or trained_series != final_test_series:
        raise ValueError("Every trained series must have validation selection and final-test metrics")

    validation_metrics = validation["metrics"]
    final_test_metrics = final_test["metrics"]
    write_evaluation(pd.concat([validation_metrics, final_test_metrics], ignore_index=True), args.metrics)

    residual_map = {
        "||".join((row.route_id, row.vessel_class_id, row.freight_unit)): row.residual_std
        for row in validation["residuals"].itertuples()
    }
    metadata = {
        "model_name": "Per-series selected Ridge autoregression or seasonal-naive baseline",
        "model_version": serving_model.version,
        "model_versions": MODEL_VERSIONS,
        "model_config": {"ridge": {"alpha": 1.0}, "baseline": {"type": "seasonal_naive", "lag_days": 7}},
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
        "initial_training_period": {
            "start": TRAIN_START.date().isoformat(),
            "end": SELECTION_TRAIN_END.date().isoformat(),
        },
        "validation_period": {
            "start": VALIDATION_START.date().isoformat(),
            "end": VALIDATION_END.date().isoformat(),
        },
        "training_period": {
            "start": TRAIN_START.date().isoformat(),
            "end": VALIDATION_END.date().isoformat(),
        },
        "serving_model_training_period": {
            "start": TRAIN_START.date().isoformat(),
            "end": VALIDATION_END.date().isoformat(),
        },
        "final_test_period": {
            "start": FINAL_TEST_START.date().isoformat(),
            "end": FINAL_TEST_END.date().isoformat(),
        },
        # Backward-compatible field; now explicitly denotes the independent final test.
        "evaluation_period": {
            "start": FINAL_TEST_START.date().isoformat(),
            "end": FINAL_TEST_END.date().isoformat(),
        },
        "series": [
            {"route_id": route_id, "vessel_class_id": vessel_id, "freight_unit": unit}
            for route_id, vessel_id, unit in sorted(
                serving_training_rows[["route_id", "vessel_class_id", "freight_unit"]]
                .drop_duplicates()
                .itertuples(index=False, name=None)
            )
        ],
        "forecast_horizons_days": [7, 30, 90],
        "baseline": "seasonal_naive_7d",
        "selection_metric": "lowest per-series MAE on validation (2025-05-01 through 2025-08-31); seasonal_naive_7d selected on ties",
        "selection_procedure": "Select per series using validation only, then refit the fixed Ridge candidate through validation end. Final-test metrics are computed after the selection map is fixed and do not affect it.",
        "selected_model_by_series": selected_models,
        "model_selection_counts": {
            model_name: sum(chosen == model_name for chosen in selected_models.values())
            for model_name in MODEL_VERSIONS
        },
        "validation_metrics_summary": _period_summary(validation_metrics, selected_models),
        "final_test_metrics_summary": _period_summary(final_test_metrics, selected_models),
        "validation_metrics_by_freight_unit": _unit_summary(validation_metrics, selected_models),
        "final_test_metrics_by_freight_unit": _unit_summary(final_test_metrics, selected_models),
        # Keep legacy aggregate keys aligned to final held-out results.
        "metrics_summary": _period_summary(final_test_metrics, selected_models),
        "metrics_by_freight_unit": _unit_summary(final_test_metrics, selected_models),
        "evaluation_generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_as_of": str(df.observation_date.max().date()),
        "data_type": sorted(df.data_type.unique().tolist()),
        "source": sorted(df.source.unique().tolist()),
        "feature_definition": "lags 1,2,3,7,14,28; rolling mean/std 7,14,28; calendar features",
        "uncertainty": "Scenario bounds from canonical scenario_defaults.csv freight_change_pct: BASELINE for central, FAVORABLE for lower, ADVERSE for upper; not a statistical confidence statement",
        "residual_std_by_series": residual_map,
        "trained_series_count": len(serving_model.models),
    }
    save_model(serving_model, args.artifact, args.metadata, metadata)
    _write_model_card(metadata, args.model_card)

    summary = pd.DataFrame(
        [
            metadata["validation_metrics_summary"]["baseline_mean"],
            metadata["validation_metrics_summary"]["improved_mean"],
            metadata["validation_metrics_summary"]["selected_mean"],
            metadata["final_test_metrics_summary"]["baseline_mean"],
            metadata["final_test_metrics_summary"]["improved_mean"],
            metadata["final_test_metrics_summary"]["selected_mean"],
        ],
        index=[
            "validation_baseline", "validation_ridge", "validation_selected",
            "final_test_baseline", "final_test_ridge", "final_test_selected_by_validation",
        ],
    )
    print(summary.to_string())


if __name__ == "__main__":
    main()
