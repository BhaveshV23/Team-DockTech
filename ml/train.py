from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd
from .features import prepare_freight_data, make_features
from .model import train_improved_model, save_model
from .evaluation import evaluate_models, write_evaluation


def main():
    parser = argparse.ArgumentParser(description="Train and evaluate DockTech freight forecasting models")
    parser.add_argument("--data", default="data/reference/freight_rates.csv")
    parser.add_argument("--artifact", default="models/artifacts/freight_forecaster.joblib")
    parser.add_argument("--metadata", default="models/metadata/freight_forecaster.json")
    parser.add_argument("--metrics", default="models/metadata/evaluation_metrics.csv")
    args = parser.parse_args()
    df = prepare_freight_data(args.data)
    train_raw = df[df.observation_date <= pd.Timestamp("2025-06-30")]
    train_features = make_features(train_raw, include_target=True)
    model = train_improved_model(train_features)
    evaluation = evaluate_models(df, model, "2025-06-30", "2025-07-01", "2025-12-31")
    write_evaluation(evaluation["metrics"], args.metrics)
    improved = evaluation["metrics"][evaluation["metrics"].model == "ridge_autoregression"]
    baseline = evaluation["metrics"][evaluation["metrics"].model == "seasonal_naive_7d"]
    residuals = evaluation["residuals"]
    residual_map = {
        f"{r.route_id}||{r.vessel_class_id}||{r.freight_unit}": r.residual_std
        for r in residuals.itertuples()
    }
    metadata = {
        "model_name": "Ridge autoregression",
        "model_version": model.version,
        "training_period": {"start": str(df.observation_date.min().date()), "end": "2025-06-30"},
        "evaluation_period": {"start": "2025-07-01", "end": "2025-12-31"},
        "forecast_horizons_days": [7, 30, 90],
        "baseline": "seasonal_naive_7d",
        "metrics_summary": {
            "baseline_mean": {k: float(baseline[k].mean()) for k in ["mae", "rmse", "mape_pct", "directional_accuracy_pct"]},
            "improved_mean": {k: float(improved[k].mean()) for k in ["mae", "rmse", "mape_pct", "directional_accuracy_pct"]},
        },
        "metrics_by_freight_unit": {
            unit: {
                "baseline_mean": {k: float(baseline[baseline.freight_unit == unit][k].mean()) for k in ["mae", "rmse", "mape_pct", "directional_accuracy_pct"]},
                "improved_mean": {k: float(improved[improved.freight_unit == unit][k].mean()) for k in ["mae", "rmse", "mape_pct", "directional_accuracy_pct"]},
            } for unit in sorted(df.freight_unit.unique())
        },
        "data_as_of": str(df.observation_date.max().date()),
        "data_type": sorted(df.data_type.unique().tolist()),
        "source": sorted(df.source.unique().tolist()),
        "feature_definition": "lags 1,2,3,7,14,28; rolling mean/std 7,14,28; calendar features",
        "uncertainty": "95% prediction interval from route/vessel/unit validation residual standard deviation; not a confidence statement",
        "residual_std_by_series": residual_map,
        "trained_series_count": len(model.models),
    }
    save_model(model, args.artifact, args.metadata, metadata)
    summary = pd.DataFrame([metadata["metrics_summary"]["baseline_mean"], metadata["metrics_summary"]["improved_mean"]], index=["baseline", "improved"])
    print(summary.to_string())

if __name__ == "__main__":
    main()
