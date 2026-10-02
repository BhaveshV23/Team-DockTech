from __future__ import annotations

from pathlib import Path

import pandas as pd

from .features import make_features
from .metrics import mae, rmse, mape, directional_accuracy
from .model import ImprovedModel, predict


def _evaluate_period(
    df: pd.DataFrame,
    model: ImprovedModel,
    period_start: str,
    period_end: str,
    *,
    select_models: bool,
) -> dict:
    start = pd.Timestamp(period_start)
    end = pd.Timestamp(period_end)
    rows = []
    residual_rows = []
    selected_models = {}

    for keys, group in df.groupby(["route_id", "vessel_class_id", "freight_unit"], sort=False):
        route_id, vessel_id, unit = keys
        group = group.sort_values("observation_date")
        features = make_features(group, include_target=True)
        period_features = features[
            (features.observation_date >= start) & (features.observation_date <= end)
        ]
        if period_features.empty:
            continue

        observed_by_date = group.set_index("observation_date")["freight_value"]
        dates = period_features.observation_date
        baseline = pd.Series(
            [observed_by_date.get(day - pd.Timedelta(days=7), float("nan")) for day in dates],
            index=period_features.index,
        )
        if baseline.isna().any():
            continue

        improved = predict(model, period_features)
        actual = period_features["freight_value"]
        previous = period_features["lag_1"]
        candidates = {
            "seasonal_naive_7d": baseline,
            "ridge_autoregression": improved,
        }
        candidate_mae = {}
        for name, prediction in candidates.items():
            candidate_mae[name] = mae(actual, prediction)
            rows.append({
                "route_id": route_id,
                "vessel_class_id": vessel_id,
                "freight_unit": unit,
                "model": name,
                "mae": candidate_mae[name],
                "rmse": rmse(actual, prediction),
                "mape_pct": mape(actual, prediction),
                "directional_accuracy_pct": directional_accuracy(actual, prediction, previous),
            })

        if select_models:
            selected_name = min(
                candidate_mae,
                key=lambda name: (candidate_mae[name], name != "seasonal_naive_7d"),
            )
            selected_models["||".join((route_id, vessel_id, unit))] = selected_name
            residual = actual.to_numpy() - candidates[selected_name].to_numpy()
            residual_rows.append({
                "route_id": route_id,
                "vessel_class_id": vessel_id,
                "freight_unit": unit,
                "residual_std": float(pd.Series(residual).std(ddof=1)),
            })

    return {
        "metrics": pd.DataFrame(rows),
        "residuals": pd.DataFrame(residual_rows),
        "selected_models": selected_models,
    }


def evaluate_models(
    df: pd.DataFrame,
    model: ImprovedModel,
    train_end: str,
    validation_start: str,
    validation_end: str,
) -> dict:
    """Evaluate model candidates on validation data and select by validation MAE only."""
    train_end_ts = pd.Timestamp(train_end)
    start_ts = pd.Timestamp(validation_start)
    end_ts = pd.Timestamp(validation_end)
    if not train_end_ts < start_ts <= end_ts:
        raise ValueError("Training must end before the chronological validation period")

    result = _evaluate_period(
        df, model, validation_start, validation_end, select_models=True,
    )
    result["metrics"]["evaluation_period"] = "validation"
    result["metrics"]["period_start"] = start_ts.date().isoformat()
    result["metrics"]["period_end"] = end_ts.date().isoformat()
    return result


def evaluate_final_test(
    df: pd.DataFrame,
    model: ImprovedModel,
    serving_selection: dict[str, str],
    serving_training_end: str,
    final_test_start: str,
    final_test_end: str,
) -> dict:
    """Score both fixed candidates on final test data without changing selection."""
    train_end_ts = pd.Timestamp(serving_training_end)
    start_ts = pd.Timestamp(final_test_start)
    end_ts = pd.Timestamp(final_test_end)
    if not train_end_ts < start_ts <= end_ts:
        raise ValueError("Serving model training must end before the chronological final test period")

    result = _evaluate_period(
        df, model, final_test_start, final_test_end, select_models=False,
    )
    result["metrics"]["evaluation_period"] = "final_test"
    result["metrics"]["period_start"] = start_ts.date().isoformat()
    result["metrics"]["period_end"] = end_ts.date().isoformat()
    result["selected_models"] = dict(serving_selection)
    return result


def write_evaluation(metrics: pd.DataFrame, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(path, index=False)
