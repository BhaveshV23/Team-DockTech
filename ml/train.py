from __future__ import annotations
import argparse
import json
import platform
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import sklearn
from .features import prepare_freight_data, make_features
from .model import train_improved_model, save_model
from .evaluation import evaluate_models, write_evaluation

TRAIN_START = pd.Timestamp("2024-01-01")
TRAIN_END = pd.Timestamp("2025-06-30")
TEST_START = pd.Timestamp("2025-07-01")
TEST_END = pd.Timestamp("2025-12-31")
METRICS = ["mae", "rmse", "mape_pct", "directional_accuracy_pct"]
MODEL_VERSIONS = {
    "ridge_autoregression": "docktech-ridge-ar-v1",
    "seasonal_naive_7d": "docktech-seasonal-naive-7d-v1",
}


def main():
    parser = argparse.ArgumentParser(description="Train and evaluate DockTech freight forecasting models")
    parser.add_argument("--data", default="data/reference/freight_rates.csv")
    parser.add_argument("--artifact", default="models/artifacts/freight_forecaster.joblib")
    parser.add_argument("--metadata", default="models/metadata/freight_forecaster.json")
    parser.add_argument("--metrics", default="models/metadata/evaluation_metrics.csv")
    args = parser.parse_args()
    df = prepare_freight_data(args.data)
    df = df[(df.observation_date >= TRAIN_START) & (df.observation_date <= TEST_END)]
    if df.empty or df.observation_date.min() != TRAIN_START or df.observation_date.max() != TEST_END:
        raise ValueError("Freight data must cover 2024-01-01 through 2025-12-31")
    train_raw = df[(df.observation_date >= TRAIN_START) & (df.observation_date <= TRAIN_END)]
    train_features = make_features(train_raw, include_target=True)
    model = train_improved_model(train_features)
    evaluation = evaluate_models(
        df, model, TRAIN_END.date().isoformat(), TEST_START.date().isoformat(), TEST_END.date().isoformat()
    )
    write_evaluation(evaluation["metrics"], args.metrics)
    trained_series = set(model.models)
    evaluated_series = set(evaluation["selected_models"])
    if trained_series != evaluated_series:
        raise ValueError("Every trained series must have held-out metrics for model selection")
    improved = evaluation["metrics"][evaluation["metrics"].model == "ridge_autoregression"]
    baseline = evaluation["metrics"][evaluation["metrics"].model == "seasonal_naive_7d"]
    selected_mask = [
        evaluation["selected_models"].get(
            "||".join((row.route_id, row.vessel_class_id, row.freight_unit))
        ) == row.model
        for row in evaluation["metrics"].itertuples()
    ]
    selected = evaluation["metrics"].loc[selected_mask]
    residuals = evaluation["residuals"]
    residual_map = {
        f"{r.route_id}||{r.vessel_class_id}||{r.freight_unit}": r.residual_std
        for r in residuals.itertuples()
    }
    metadata = {
        "model_name": "Per-series selected Ridge autoregression or seasonal-naive baseline",
        "model_version": model.version,
        "model_versions": MODEL_VERSIONS,
        "model_config": {"ridge": {"alpha": 1.0}, "baseline": {"type": "seasonal_naive", "lag_days": 7}},
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
        "training_period": {"start": TRAIN_START.date().isoformat(), "end": TRAIN_END.date().isoformat()},
        "evaluation_period": {"start": TEST_START.date().isoformat(), "end": TEST_END.date().isoformat()},
        "series": [
            {"route_id": route_id, "vessel_class_id": vessel_id, "freight_unit": unit}
            for route_id, vessel_id, unit in sorted(
                train_raw[["route_id", "vessel_class_id", "freight_unit"]]
                .drop_duplicates()
                .itertuples(index=False, name=None)
            )
        ],
        "forecast_horizons_days": [7, 30, 90],
        "baseline": "seasonal_naive_7d",
        "selection_metric": "lowest per-series held-out MAE; seasonal_naive_7d selected on ties",
        "selected_model_by_series": evaluation["selected_models"],
        "metrics_summary": {
            "baseline_mean": {k: float(baseline[k].mean()) for k in METRICS},
            "improved_mean": {k: float(improved[k].mean()) for k in METRICS},
            "selected_mean": {k: float(selected[k].mean()) for k in METRICS},
        },
        "metrics_by_freight_unit": {
            unit: {
                "baseline_mean": {k: float(baseline[baseline.freight_unit == unit][k].mean()) for k in METRICS},
                "improved_mean": {k: float(improved[improved.freight_unit == unit][k].mean()) for k in METRICS},
                "selected_mean": {k: float(selected[selected.freight_unit == unit][k].mean()) for k in METRICS},
            } for unit in sorted(df.freight_unit.unique())
        },
        "data_as_of": str(df.observation_date.max().date()),
        "data_type": sorted(df.data_type.unique().tolist()),
        "source": sorted(df.source.unique().tolist()),
        "feature_definition": "lags 1,2,3,7,14,28; rolling mean/std 7,14,28; calendar features",
        "uncertainty": "Approximate 95% uncertainty bounds from selected-model held-out residual standard deviation, scaled by square root of forecast days; not a statistical confidence statement",
        "residual_std_by_series": residual_map,
        "trained_series_count": len(model.models),
    }
    save_model(model, args.artifact, args.metadata, metadata)
    summary = pd.DataFrame(
        [
            metadata["metrics_summary"]["baseline_mean"],
            metadata["metrics_summary"]["improved_mean"],
            metadata["metrics_summary"]["selected_mean"],
        ],
        index=["baseline", "ridge", "selected"],
    )
    print(summary.to_string())

if __name__ == "__main__":
    main()
