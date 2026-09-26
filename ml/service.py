from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import pandas as pd
from .features import prepare_freight_data, build_feature_row, feature_columns
from .model import load_model, model_key

@dataclass
class ForecastPoint:
    date: str
    central: float
    lower: float
    upper: float
    freight_unit: str
    model_version: str
    training_data_end_date: str

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
        # Use residual scale from metadata if available; otherwise a conservative
        # group-level historical volatility estimate is used.
        residual_map = self.metadata.get("residual_std_by_series", {})
        residual_std = float(residual_map.get(model_key(route_id, vessel_class_id, freight_unit), 0.0))
        residual_std = max(residual_std, float(history.freight_value.std() * 0.05), 1e-6)
        for i in range(1, horizon + 1):
            date = last_date + pd.Timedelta(days=i)
            row = build_feature_row(history, route_id, vessel_class_id, freight_unit, date)
            key = model_key(route_id, vessel_class_id, freight_unit)
            if key not in self.models:
                raise ValueError("No trained model is available for this route/vessel/unit combination")
            pred = float(self.models[key].predict(pd.DataFrame([row])[feature_columns()[3:]])[0])
            pred = max(pred, 0.0)
            interval_width = 1.96 * residual_std * (i ** 0.5)
            lower = max(pred - interval_width, 0.0)
            upper = pred + interval_width
            points.append(ForecastPoint(
                date=date.date().isoformat(), central=pred, lower=lower, upper=upper,
                freight_unit=freight_unit, model_version=self.model_version,
                training_data_end_date=self.training_end,
            ))
            history = pd.concat([history, pd.DataFrame([{
                "observation_date": date, "route_id": route_id, "vessel_class_id": vessel_class_id,
                "freight_unit": freight_unit, "freight_value": pred
            }])], ignore_index=True)
        return ForecastResult(route_id, vessel_class_id, freight_unit, horizon, self.model_version, points)

    def forecast_dict(self, route_id: str, vessel_class_id: str, freight_unit: str, horizon: int) -> dict:
        result = self.forecast(route_id, vessel_class_id, freight_unit, horizon)
        return {"route_id": result.route_id, "vessel_class_id": result.vessel_class_id,
                "freight_unit": result.freight_unit, "horizon": result.horizon,
                "model_version": result.model_version,
                "points": [asdict(p) for p in result.points]}


def forecast(route_id: str, vessel_class_id: str, freight_unit: str, horizon: int,
             data_path: str = "data/reference/freight_rates.csv",
             artifact_path: str = "models/artifacts/freight_forecaster.joblib",
             metadata_path: str = "models/metadata/freight_forecaster.json") -> dict:
    return ForecastService(data_path, artifact_path, metadata_path).forecast_dict(route_id, vessel_class_id, freight_unit, horizon)
