from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import joblib
import pandas as pd
from sklearn.linear_model import Ridge
from .features import feature_columns

NUMERIC = [c for c in feature_columns() if c not in {"route_id", "vessel_class_id", "freight_unit"}]

@dataclass
class ImprovedModel:
    models: dict[str, Ridge]
    version: str


def _key(route_id: str, vessel_class_id: str, freight_unit: str) -> str:
    return f"{route_id}||{vessel_class_id}||{freight_unit}"


def train_improved_model(train_features: pd.DataFrame) -> ImprovedModel:
    models: dict[str, Ridge] = {}
    for keys, group in train_features.groupby(["route_id", "vessel_class_id", "freight_unit"], sort=False):
        route_id, vessel_id, unit = keys
        model = Ridge(alpha=1.0)
        model.fit(group[NUMERIC], group["freight_value"])
        models[_key(route_id, vessel_id, unit)] = model
    return ImprovedModel(models=models, version="docktech-ridge-ar-v1")


def predict(model: ImprovedModel, features: pd.DataFrame) -> pd.Series:
    values = []
    for keys, group in features.groupby(["route_id", "vessel_class_id", "freight_unit"], sort=False):
        key = _key(*keys)
        if key not in model.models:
            raise ValueError(f"No trained model for {key}")
        pred = model.models[key].predict(group[NUMERIC])
        values.append(pd.Series(pred, index=group.index))
    return pd.concat(values).sort_index()


def save_model(model: ImprovedModel, artifact_path: str, metadata_path: str, metadata: dict) -> None:
    Path(artifact_path).parent.mkdir(parents=True, exist_ok=True)
    Path(metadata_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model.models, artifact_path)
    Path(metadata_path).write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def load_model(artifact_path: str) -> dict[str, Ridge]:
    return joblib.load(artifact_path)


def model_key(route_id: str, vessel_class_id: str, freight_unit: str) -> str:
    return _key(route_id, vessel_class_id, freight_unit)
