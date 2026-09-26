from __future__ import annotations
from pathlib import Path
import pandas as pd
from .features import make_features
from .metrics import mae, rmse, mape, directional_accuracy
from .model import ImprovedModel, predict


def evaluate_models(df: pd.DataFrame, model: ImprovedModel, train_end: str, test_start: str, test_end: str) -> dict:
    train_end_ts = pd.Timestamp(train_end)
    test_start_ts = pd.Timestamp(test_start)
    test_end_ts = pd.Timestamp(test_end)
    rows = []
    residual_rows = []
    selected_models = {}
    for keys, group in df.groupby(["route_id", "vessel_class_id", "freight_unit"], sort=False):
        route_id, vessel_id, unit = keys
        group = group.sort_values("observation_date")
        train = group[group.observation_date <= train_end_ts]
        test = group[(group.observation_date >= test_start_ts) & (group.observation_date <= test_end_ts)]
        if len(train) < 28 or test.empty:
            continue
        # One-step chronological backtest: each prediction only uses information
        # available before that observation date.
        test_dates = test.observation_date
        observed_by_date = group.set_index("observation_date")["freight_value"]
        baseline_preds = pd.Series(
            [observed_by_date.get(d - pd.Timedelta(days=7), float("nan")) for d in test_dates],
            index=test.index,
        )
        feature_df = make_features(group, include_target=True)
        test_features = feature_df[(feature_df.observation_date >= test_start_ts) & (feature_df.observation_date <= test_end_ts)]
        if test_features.empty or baseline_preds.loc[test_features.index].isna().any():
            continue
        improved_preds = predict(model, test_features)
        actual = test_features["freight_value"]
        previous = test_features["lag_1"]
        candidates = {
            "seasonal_naive_7d": baseline_preds.loc[test_features.index],
            "ridge_autoregression": improved_preds,
        }
        candidate_mae = {}
        for name, pred in candidates.items():
            candidate_mae[name] = mae(actual, pred)
            rows.append({
                "route_id": route_id, "vessel_class_id": vessel_id, "freight_unit": unit,
                "model": name, "mae": mae(actual, pred), "rmse": rmse(actual, pred),
                "mape_pct": mape(actual, pred), "directional_accuracy_pct": directional_accuracy(actual, pred, previous),
            })
        selected_name = min(candidate_mae, key=lambda name: (candidate_mae[name], name != "seasonal_naive_7d"))
        selected_models["||".join((route_id, vessel_id, unit))] = selected_name
        residual = actual.to_numpy() - candidates[selected_name].to_numpy()
        residual_rows.append({
            "route_id": route_id, "vessel_class_id": vessel_id, "freight_unit": unit,
            "residual_std": float(pd.Series(residual).std(ddof=1)),
        })
    return {
        "metrics": pd.DataFrame(rows),
        "residuals": pd.DataFrame(residual_rows),
        "selected_models": selected_models,
    }


def write_evaluation(metrics: pd.DataFrame, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(path, index=False)
