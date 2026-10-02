import numpy as np
import pandas as pd

from ml.baseline import seasonal_naive_predict
from ml.evaluation import evaluate_final_test, evaluate_models
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


def test_chronological_validation_scores_both_models_and_selects_by_validation_mae():
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
    assert set(metrics["evaluation_period"]) == {"validation"}
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


def test_final_test_changes_do_not_change_validation_model_selection():
    rows = []
    dates = pd.date_range("2024-01-01", "2024-12-31", freq="D")
    for series, offset in (("R1", 10), ("R2", 1000)):
        for index, day in enumerate(dates):
            rows.append({
                "observation_date": day,
                "route_id": series,
                "vessel_class_id": "V",
                "freight_unit": "USD_PER_MT",
                "freight_value": offset + 0.25 * index + (index % 7) * 0.2,
            })
    data = pd.DataFrame(rows)
    train_end = "2024-04-30"
    validation_start = "2024-05-01"
    validation_end = "2024-08-31"
    model = train_improved_model(make_features(data[data.observation_date <= pd.Timestamp(train_end)]))
    selected_before = evaluate_models(data, model, train_end, validation_start, validation_end)

    changed_test = data.copy()
    final_start = pd.Timestamp("2024-09-01")
    changed_test.loc[changed_test.observation_date >= final_start, "freight_value"] *= 20
    selected_after = evaluate_models(changed_test, model, train_end, validation_start, validation_end)

    assert selected_before["selected_models"] == selected_after["selected_models"]
    final_model = train_improved_model(make_features(data[data.observation_date < final_start]))
    test_before = evaluate_final_test(
        data, final_model, selected_before["selected_models"], validation_end,
        "2024-09-01", "2024-12-31",
    )
    test_after = evaluate_final_test(
        changed_test, final_model, selected_after["selected_models"], validation_end,
        "2024-09-01", "2024-12-31",
    )
    assert test_before["selected_models"] == test_after["selected_models"]
    assert not test_before["metrics"].equals(test_after["metrics"])


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
