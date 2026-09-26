import numpy as np
import pandas as pd

from ml.baseline import seasonal_naive_predict
from ml.evaluation import evaluate_models
from ml.features import make_features
from ml.model import predict, train_improved_model


def _history():
    rows = []
    start = pd.Timestamp("2024-01-01")
    for series, offset in (("R1", 10), ("R2", 1000)):
        for i in range(100):
            rows.append({
                "observation_date": start + pd.Timedelta(days=i),
                "route_id": series,
                "vessel_class_id": "V",
                "freight_value": offset + 0.25 * i + (i % 7) * 0.2,
                "freight_unit": "USD_PER_MT",
            })
    return pd.DataFrame(rows)


def test_seasonal_naive_predicts_seven_days_back_recursively():
    history = pd.DataFrame({
        "observation_date": pd.date_range("2024-01-01", periods=14, freq="D"),
        "freight_value": list(range(1, 15)),
    })
    dates = pd.date_range("2024-01-15", periods=10, freq="D")

    predictions = seasonal_naive_predict(history, dates)

    assert predictions.tolist() == [8, 9, 10, 11, 12, 13, 14, 8, 9, 10]
    assert predictions.index.equals(dates)


def test_chronological_evaluation_scores_both_models_and_selects_by_measured_mae():
    data = _history()
    train_end = "2024-03-10"
    test_start = "2024-03-11"
    test_end = "2024-04-09"
    train_data = data[data.observation_date <= pd.Timestamp(train_end)]
    train_features = make_features(train_data)
    assert train_features.observation_date.max() <= pd.Timestamp(train_end)
    model = train_improved_model(train_features)

    result = evaluate_models(data, model, train_end, test_start, test_end)
    metrics = result["metrics"]

    assert set(metrics["model"]) == {"seasonal_naive_7d", "ridge_autoregression"}
    assert len(metrics) == 4
    assert set(metrics["route_id"]) == {"R1", "R2"}
    assert metrics[["mae", "rmse", "mape_pct", "directional_accuracy_pct"]].notna().all().all()
    for row in metrics.drop_duplicates(["route_id", "vessel_class_id", "freight_unit"]).itertuples():
        series_key = "||".join((row.route_id, row.vessel_class_id, row.freight_unit))
        series_metrics = metrics[
            (metrics.route_id == row.route_id)
            & (metrics.vessel_class_id == row.vessel_class_id)
            & (metrics.freight_unit == row.freight_unit)
        ].set_index("model")
        expected = min(
            ("seasonal_naive_7d", "ridge_autoregression"),
            key=lambda name: (series_metrics.loc[name, "mae"], name != "seasonal_naive_7d"),
        )
        assert result["selected_models"][series_key] == expected

    test_rows = data[
        (data.observation_date >= pd.Timestamp(test_start))
        & (data.observation_date <= pd.Timestamp(test_end))
    ]
    assert test_rows.observation_date.min() == pd.Timestamp(test_start)
    assert test_rows.observation_date.max() == pd.Timestamp(test_end)


def test_training_same_features_is_reproducible():
    features = make_features(_history())
    training_rows = features[features.observation_date <= pd.Timestamp("2024-03-10")]
    first = train_improved_model(training_rows)
    second = train_improved_model(training_rows)
    sample = training_rows.head(20)

    np.testing.assert_array_equal(predict(first, sample), predict(second, sample))
    for key in first.models:
        np.testing.assert_array_equal(first.models[key].coef_, second.models[key].coef_)
        assert first.models[key].alpha == second.models[key].alpha == 1.0
