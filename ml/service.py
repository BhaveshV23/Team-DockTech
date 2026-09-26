from __future__ import annotations
from dataclasses import dataclass, asdict
import csv
from pathlib import Path
import json
import math
import pandas as pd
from .baseline import seasonal_naive_predict
from .features import prepare_freight_data, build_feature_row, feature_columns
from .model import load_model, model_key


def _load_scenario_freight_changes() -> dict[str, float]:
    path = Path(__file__).resolve().parents[1] / "data" / "reference" / "scenario_defaults.csv"
    with path.open(encoding="utf-8", newline="") as scenario_file:
        rows = list(csv.DictReader(scenario_file))

    changes = {}
    for row in rows:
        scenario_id = row["scenario_id"]
        if scenario_id in changes:
            raise ValueError(f"Duplicate scenario default {scenario_id!r} in {path}")
        changes[scenario_id] = float(row["freight_change_pct"])

    required = {"BASELINE", "FAVORABLE", "ADVERSE"}
    if not required.issubset(changes):
        raise ValueError(f"Missing canonical scenario defaults: {sorted(required - changes.keys())}")
    if not all(math.isfinite(changes[scenario_id]) for scenario_id in required):
        raise ValueError("Canonical scenario freight changes must be finite")
    if changes["BASELINE"] != 0 or not changes["FAVORABLE"] < 0 < changes["ADVERSE"]:
        raise ValueError("Canonical scenario freight changes do not support forecast bound ordering")
    return {scenario_id: changes[scenario_id] for scenario_id in required}


@dataclass
class ForecastPoint:
    forecast_date: str
    central: float
    lower: float
    upper: float
    freight_unit: str
    model_version: str
    training_data_end_date: str

    @property
    def date(self) -> str:
        """Backward-compatible alias for the original serialized `date` field."""
        return self.forecast_date

@dataclass
class ForecastResult:
    route_id: str
    vessel_class_id: str
    freight_unit: str
    horizon: int
    model_version: str
    points: list[ForecastPoint]

class ForecastService:
    """Backend-facing inference service. Training is intentionally separate."""
    def __init__(self, data_path: str = "data/reference/freight_rates.csv",
                 artifact_path: str = "models/artifacts/freight_forecaster.joblib",
                 metadata_path: str = "models/metadata/freight_forecaster.json"):
        self.data = prepare_freight_data(data_path)
        self.models = load_model(artifact_path)
        self.metadata = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
        self.model_version = self.metadata["model_version"]
        self.training_end = self.metadata["training_period"]["end"]
        self.selected_models = self.metadata.get("selected_model_by_series", {})
        self.scenario_freight_changes = _load_scenario_freight_changes()

    def forecast(self, route_id: str, vessel_class_id: str, freight_unit: str, horizon: int) -> ForecastResult:
        if horizon not in {7, 30, 90}:
            raise ValueError("horizon must be one of 7, 30, or 90 days")
        group = self.data[(self.data.route_id == route_id) &
                          (self.data.vessel_class_id == vessel_class_id) &
                          (self.data.freight_unit == freight_unit)].copy()
        if group.empty:
            raise ValueError("Unsupported route, vessel class, or freight unit combination")
        group = group.sort_values("observation_date")
        history = group[["observation_date", "route_id", "vessel_class_id", "freight_unit", "freight_value"]].copy()
        last_date = history.observation_date.max()
        points = []
        series_key = model_key(route_id, vessel_class_id, freight_unit)
        selected_model = self.selected_models.get(series_key, "ridge_autoregression")
        model_versions = self.metadata.get("model_versions", {})
        selected_version = model_versions.get(
            selected_model,
            self.model_version if selected_model == "ridge_autoregression" else "docktech-seasonal-naive-7d-v1",
        )
        future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=horizon, freq="D")
        if selected_model == "seasonal_naive_7d":
            baseline_predictions = seasonal_naive_predict(history, future_dates)
        elif selected_model != "ridge_autoregression":
            raise ValueError(f"Unsupported selected model {selected_model!r} for {series_key}")
        for i in range(1, horizon + 1):
            date = future_dates[i - 1]
            if selected_model == "seasonal_naive_7d":
                pred = float(baseline_predictions.iloc[i - 1])
            else:
                if series_key not in self.models:
                    raise ValueError("No trained model is available for this route/vessel/unit combination")
                row = build_feature_row(history, route_id, vessel_class_id, freight_unit, date)
                pred = float(self.models[series_key].predict(pd.DataFrame([row])[feature_columns()[3:]])[0])
            if not math.isfinite(pred):
                raise ValueError(f"Model produced a non-finite forecast for {series_key}")
            central = max(
                0.0,
                pred * (1 + self.scenario_freight_changes["BASELINE"] / 100),
            )
            lower = max(
                0.0,
                pred * (1 + self.scenario_freight_changes["FAVORABLE"] / 100),
            )
            upper = max(
                0.0,
                pred * (1 + self.scenario_freight_changes["ADVERSE"] / 100),
            )
            points.append(ForecastPoint(
                forecast_date=date.date().isoformat(), central=central, lower=lower, upper=upper,
                freight_unit=freight_unit, model_version=selected_version,
                training_data_end_date=self.training_end,
            ))
            if selected_model == "ridge_autoregression":
                history = pd.concat([history, pd.DataFrame([{
                    "observation_date": date, "route_id": route_id, "vessel_class_id": vessel_class_id,
                    "freight_unit": freight_unit, "freight_value": central
                }])], ignore_index=True)
        return ForecastResult(route_id, vessel_class_id, freight_unit, horizon, selected_version, points)

    def forecast_dict(self, route_id: str, vessel_class_id: str, freight_unit: str, horizon: int) -> dict:
        result = self.forecast(route_id, vessel_class_id, freight_unit, horizon)
        return {"route_id": result.route_id, "vessel_class_id": result.vessel_class_id,
                "freight_unit": result.freight_unit, "horizon": result.horizon,
                "model_version": result.model_version,
                "points": [
                    {**asdict(point), "date": point.forecast_date}
                    for point in result.points
                ]}


def forecast(route_id: str, vessel_class_id: str, freight_unit: str, horizon: int,
             data_path: str = "data/reference/freight_rates.csv",
             artifact_path: str = "models/artifacts/freight_forecaster.joblib",
             metadata_path: str = "models/metadata/freight_forecaster.json") -> dict:
    return ForecastService(data_path, artifact_path, metadata_path).forecast_dict(route_id, vessel_class_id, freight_unit, horizon)
