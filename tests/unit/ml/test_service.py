import json

import joblib
import numpy as np
import pandas as pd
import pytest

from ml.features import make_features, prepare_freight_data
from ml.model import NUMERIC, load_model, save_model, train_improved_model
from ml.service import ForecastService


@pytest.fixture
def service_files(tmp_path):
    rows = []
    start = pd.Timestamp("2024-01-01")
    for i in range(100):
        rows.append({
            "freight_rate_id": f"F{i}",
            "observation_date": (start + pd.Timedelta(days=i)).date(),
            "route_id": "R",
            "vessel_class_id": "V",
            "freight_value": 20 + 0.1 * i + (i % 7) * 0.4,
            "freight_unit": "USD_PER_MT",
            "currency": "USD",
            "data_type": "SYNTHETIC",
            "source": "TEST",
        })
    data_path = tmp_path / "freight.csv"
    pd.DataFrame(rows).to_csv(data_path, index=False)
    data = prepare_freight_data(str(data_path))
    model = train_improved_model(make_features(data))
    artifact_path = tmp_path / "model.joblib"
    metadata_path = tmp_path / "metadata.json"
    metadata = {
        "model_version": model.version,
        "model_versions": {
            "ridge_autoregression": "docktech-ridge-ar-v1",
            "seasonal_naive_7d": "docktech-seasonal-naive-7d-v1",
        },
        "training_period": {"end": "2024-04-09"},
        "residual_std_by_series": {"R||V||USD_PER_MT": 5000.0},
    }
    save_model(model, str(artifact_path), str(metadata_path), metadata)
    return data_path, artifact_path, metadata_path, metadata


@pytest.mark.parametrize("horizon", [7, 30, 90])
def test_service_executes_supported_forecast_horizons(service_files, horizon):
    data_path, artifact_path, metadata_path, _ = service_files
    service = ForecastService(str(data_path), str(artifact_path), str(metadata_path))

    result = service.forecast("R", "V", "USD_PER_MT", horizon)

    assert len(result.points) == horizon
    assert result.points[0].forecast_date == "2024-04-10"
    assert result.points[-1].forecast_date == (
        pd.Timestamp("2024-04-09") + pd.Timedelta(days=horizon)
    ).date().isoformat()


def test_forecast_output_contract_and_uncertainty_bounds(service_files):
    data_path, artifact_path, metadata_path, _ = service_files
    service = ForecastService(str(data_path), str(artifact_path), str(metadata_path))

    output = service.forecast_dict("R", "V", "USD_PER_MT", 7)
    point = output["points"][0]

    assert {
        "forecast_date", "central", "lower", "upper", "freight_unit",
        "model_version", "training_data_end_date",
    } <= point.keys()
    assert point["date"] == point["forecast_date"]
    assert set(point) == {
        "forecast_date", "date", "central", "lower", "upper", "freight_unit",
        "model_version", "training_data_end_date",
    }
    assert point["freight_unit"] == "USD_PER_MT"
    assert point["model_version"] == "docktech-ridge-ar-v1"
    assert point["training_data_end_date"] == "2024-04-09"
    assert point["lower"] <= point["central"] <= point["upper"]
    assert "confidence" not in point


@pytest.mark.parametrize("horizon", [7, 30, 90])
def test_bounds_use_canonical_scenario_freight_shocks(service_files, horizon):
    data_path, artifact_path, metadata_path, _ = service_files
    service = ForecastService(str(data_path), str(artifact_path), str(metadata_path))
    defaults = pd.read_csv("data/reference/scenario_defaults.csv").set_index("scenario_id")

    result = service.forecast("R", "V", "USD_PER_MT", horizon)

    baseline = defaults.loc["BASELINE", "freight_change_pct"]
    favorable = defaults.loc["FAVORABLE", "freight_change_pct"]
    adverse = defaults.loc["ADVERSE", "freight_change_pct"]
    assert baseline == 0
    assert favorable < 0 < adverse
    assert len(result.points) == horizon
    for point in result.points:
        assert point.central > 0
        assert point.central == pytest.approx(point.central * (1 + baseline / 100))
        assert point.lower == pytest.approx(max(0, point.central * (1 + favorable / 100)))
        assert point.upper == pytest.approx(max(0, point.central * (1 + adverse / 100)))
        assert point.lower <= point.central <= point.upper
        assert not hasattr(point, "confidence")


@pytest.mark.parametrize("horizon", [0, 1, 14, 91, -7])
def test_service_rejects_invalid_horizon(service_files, horizon):
    data_path, artifact_path, metadata_path, _ = service_files
    service = ForecastService(str(data_path), str(artifact_path), str(metadata_path))

    with pytest.raises(ValueError, match="horizon"):
        service.forecast("R", "V", "USD_PER_MT", horizon)


@pytest.mark.parametrize(
    ("route_id", "vessel_class_id", "freight_unit"),
    [
        ("UNKNOWN", "V", "USD_PER_MT"),
        ("R", "UNKNOWN", "USD_PER_MT"),
        ("R", "V", "UNKNOWN"),
    ],
)
def test_service_rejects_unknown_series(service_files, route_id, vessel_class_id, freight_unit):
    data_path, artifact_path, metadata_path, _ = service_files
    service = ForecastService(str(data_path), str(artifact_path), str(metadata_path))

    with pytest.raises(ValueError, match="Unsupported"):
        service.forecast(route_id, vessel_class_id, freight_unit, 7)


def test_selected_baseline_is_served_and_uses_its_version(service_files):
    data_path, artifact_path, metadata_path, metadata = service_files
    metadata["selected_model_by_series"] = {"R||V||USD_PER_MT": "seasonal_naive_7d"}
    metadata["model_versions"] = {
        "seasonal_naive_7d": "docktech-seasonal-naive-7d-v1",
        "ridge_autoregression": "docktech-ridge-ar-v1",
    }
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    service = ForecastService(str(data_path), str(artifact_path), str(metadata_path))

    result = service.forecast("R", "V", "USD_PER_MT", 30)

    assert result.model_version == "docktech-seasonal-naive-7d-v1"
    assert all(point.model_version == result.model_version for point in result.points)
    assert all(point.lower <= point.central <= point.upper for point in result.points)


def _forecast_version(service):
    result = service.forecast("R", "V", "USD_PER_MT", 7)
    assert result.model_version == "docktech-seasonal-naive-7d-v1"
    assert all(point.model_version == result.model_version for point in result.points)
    return result


def test_missing_ridge_artifact_falls_back_to_seasonal_naive(service_files, tmp_path):
    data_path, _, metadata_path, _ = service_files
    service = ForecastService(str(data_path), str(tmp_path / "missing.joblib"), str(metadata_path))

    result = _forecast_version(service)

    assert result.points[0].central == pytest.approx(20 + 0.1 * 93 + (93 % 7) * 0.4)


def test_corrupt_ridge_artifact_falls_back_to_seasonal_naive(service_files, tmp_path):
    data_path, _, metadata_path, _ = service_files
    corrupt_artifact = tmp_path / "corrupt.joblib"
    corrupt_artifact.write_bytes(b"not a valid model artifact")
    service = ForecastService(str(data_path), str(corrupt_artifact), str(metadata_path))

    _forecast_version(service)


def test_malformed_ridge_estimator_falls_back_to_seasonal_naive(service_files, tmp_path):
    data_path, _, metadata_path, _ = service_files
    malformed_artifact = tmp_path / "malformed.joblib"
    joblib.dump({"R||V||USD_PER_MT": object()}, malformed_artifact)
    service = ForecastService(str(data_path), str(malformed_artifact), str(metadata_path))

    _forecast_version(service)


def test_ridge_inference_exception_falls_back(service_files):
    data_path, artifact_path, metadata_path, _ = service_files
    service = ForecastService(str(data_path), str(artifact_path), str(metadata_path))

    class BrokenEstimator:
        def predict(self, _features):
            raise RuntimeError("inference failure")

    service.models["R||V||USD_PER_MT"] = BrokenEstimator()

    _forecast_version(service)


@pytest.mark.parametrize("output", [np.nan, np.inf, 0.0, -1.0, [1.0, 2.0]])
def test_invalid_ridge_output_falls_back(service_files, output):
    data_path, artifact_path, metadata_path, _ = service_files
    service = ForecastService(str(data_path), str(artifact_path), str(metadata_path))

    class InvalidEstimator:
        def predict(self, _features):
            return output

    service.models["R||V||USD_PER_MT"] = InvalidEstimator()

    _forecast_version(service)


def test_small_but_valid_ridge_value_does_not_trigger_fallback(service_files):
    data_path, artifact_path, metadata_path, _ = service_files
    service = ForecastService(str(data_path), str(artifact_path), str(metadata_path))

    class LowEstimator:
        def predict(self, _features):
            return np.array([0.0001])

    service.models["R||V||USD_PER_MT"] = LowEstimator()

    result = service.forecast("R", "V", "USD_PER_MT", 7)

    assert result.model_version == "docktech-ridge-ar-v1"
    assert result.points[0].central == pytest.approx(0.0001)


def test_baseline_failure_is_not_hidden_by_fallback(service_files, monkeypatch):
    data_path, _, metadata_path, _ = service_files
    service = ForecastService(str(data_path), "missing.joblib", str(metadata_path))

    def fail_baseline(_history, _dates):
        raise ValueError("Not enough history for seasonal-naive forecasting")

    monkeypatch.setattr("ml.service.seasonal_naive_predict", fail_baseline)
    with pytest.raises(ValueError, match="Not enough history"):
        service.forecast("R", "V", "USD_PER_MT", 7)


def test_model_artifact_save_load_preserves_predictions(service_files):
    data_path, artifact_path, _, _ = service_files
    data = prepare_freight_data(str(data_path))
    features = make_features(data)
    model = train_improved_model(features)
    loaded = load_model(str(artifact_path))

    assert set(loaded) == set(model.models)
    for key, estimator in model.models.items():
        inputs = features.loc[features.route_id == "R", NUMERIC]
        assert (estimator.predict(inputs) == loaded[key].predict(inputs)).all()
