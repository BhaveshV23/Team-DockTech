import json
import sys

import pandas as pd

from ml.model import load_model
from ml.train import main


def test_training_writes_split_metadata_selection_and_loadable_artifact(tmp_path, monkeypatch):
    rows = []
    for i, date in enumerate(pd.date_range("2024-01-01", "2025-12-31", freq="D")):
        rows.append({
            "freight_rate_id": f"F{i}",
            "observation_date": date.date(),
            "route_id": "ROUTE",
            "vessel_class_id": "VESSEL",
            "freight_value": 20 + 0.01 * i + (i % 7) * 0.2,
            "freight_unit": "USD_PER_MT",
            "currency": "USD",
            "data_type": "SYNTHETIC",
            "source": "TEST",
        })
    data_path = tmp_path / "freight.csv"
    artifact_path = tmp_path / "models" / "forecast.joblib"
    metadata_path = tmp_path / "models" / "metadata.json"
    metrics_path = tmp_path / "models" / "evaluation.csv"
    pd.DataFrame(rows).to_csv(data_path, index=False)
    monkeypatch.setattr(sys, "argv", [
        "ml.train",
        "--data", str(data_path),
        "--artifact", str(artifact_path),
        "--metadata", str(metadata_path),
        "--metrics", str(metrics_path),
    ])

    main()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metrics = pd.read_csv(metrics_path)
    artifact = load_model(str(artifact_path))
    series_key = "ROUTE||VESSEL||USD_PER_MT"
    required_metric_names = {
        "mae", "rmse", "mape_pct", "directional_accuracy_pct",
    }

    assert metadata["model_name"]
    assert metadata["model_version"] == "docktech-ridge-ar-v1"
    assert metadata["training_period"] == {"start": "2024-01-01", "end": "2025-06-30"}
    assert metadata["evaluation_period"] == {"start": "2025-07-01", "end": "2025-12-31"}
    assert metadata["series"] == [{
        "route_id": "ROUTE", "vessel_class_id": "VESSEL", "freight_unit": "USD_PER_MT",
    }]
    assert metadata["model_config"]["ridge"]["alpha"] == 1.0
    assert set(metadata["runtime"]) == {"python", "numpy", "pandas", "scikit_learn", "joblib"}
    assert metadata["selection_metric"]
    assert metadata["selected_model_by_series"][series_key] in {
        "seasonal_naive_7d", "ridge_autoregression",
    }
    assert set(metadata["metrics_summary"]["baseline_mean"]) == required_metric_names
    assert set(metadata["metrics_summary"]["improved_mean"]) == required_metric_names
    assert set(metadata["metrics_summary"]["selected_mean"]) == required_metric_names
    assert set(metrics["model"]) == {"seasonal_naive_7d", "ridge_autoregression"}
    series_metrics = metrics.set_index("model")
    expected = min(
        ("seasonal_naive_7d", "ridge_autoregression"),
        key=lambda name: (series_metrics.loc[name, "mae"], name != "seasonal_naive_7d"),
    )
    assert metadata["selected_model_by_series"][series_key] == expected
    assert series_key in artifact
    assert metadata["uncertainty"]
