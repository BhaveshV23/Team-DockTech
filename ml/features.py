from __future__ import annotations

from typing import Iterable
import pandas as pd

LAGS = (1, 2, 3, 7, 14, 28)
ROLLING_WINDOWS = (7, 14, 28)
GROUP_COLUMNS = ["route_id", "vessel_class_id", "freight_unit"]


def prepare_freight_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["observation_date"])
    required = {
        "observation_date", "route_id", "vessel_class_id", "freight_value",
        "freight_unit", "currency", "data_type", "source"
    }
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required freight columns: {sorted(missing)}")
    if df.empty:
        raise ValueError("Freight dataset is empty")
    if df["observation_date"].isna().any() or df["freight_value"].isna().any():
        raise ValueError("Freight dataset contains missing dates or values")
    if (df["freight_value"] <= 0).any():
        raise ValueError("Freight values must be positive")
    dupes = df.duplicated(GROUP_COLUMNS + ["observation_date"])
    if dupes.any():
        raise ValueError("Freight dataset contains duplicate observations at canonical grain")
    df = df.sort_values(GROUP_COLUMNS + ["observation_date"]).reset_index(drop=True)
    return df


def make_features(df: pd.DataFrame, include_target: bool = True) -> pd.DataFrame:
    """Create leakage-safe lag/rolling/calendar features.

    All rolling statistics use shift(1), so the current target is never used
    to build its own features.
    """
    out = df.copy().sort_values(GROUP_COLUMNS + ["observation_date"])
    grouped = out.groupby(GROUP_COLUMNS, sort=False)["freight_value"]
    for lag in LAGS:
        out[f"lag_{lag}"] = grouped.shift(lag)
    shifted = grouped.shift(1)
    for window in ROLLING_WINDOWS:
        out[f"rolling_mean_{window}"] = shifted.groupby(
            [out[c] for c in GROUP_COLUMNS], sort=False
        ).transform(lambda s: s.rolling(window, min_periods=window).mean())
        out[f"rolling_std_{window}"] = shifted.groupby(
            [out[c] for c in GROUP_COLUMNS], sort=False
        ).transform(lambda s: s.rolling(window, min_periods=window).std())
    out["day_of_week"] = out["observation_date"].dt.dayofweek
    out["day_of_year"] = out["observation_date"].dt.dayofyear
    out["month"] = out["observation_date"].dt.month
    out["trend_day"] = (out["observation_date"] - out["observation_date"].min()).dt.days
    if include_target:
        return out.dropna(subset=["lag_28", "rolling_mean_28", "rolling_std_28"])
    return out


def build_feature_row(history: pd.DataFrame, route_id: str, vessel_class_id: str,
                      freight_unit: str, date: pd.Timestamp) -> dict:
    subset = history[
        (history["route_id"] == route_id)
        & (history["vessel_class_id"] == vessel_class_id)
        & (history["freight_unit"] == freight_unit)
    ].sort_values("observation_date")
    values = subset["freight_value"].tolist()
    if len(values) < max(LAGS):
        raise ValueError("At least 28 historical observations are required for forecasting")
    row = {
        "route_id": route_id,
        "vessel_class_id": vessel_class_id,
        "freight_unit": freight_unit,
        "observation_date": date,
        "day_of_week": date.dayofweek,
        "day_of_year": date.dayofyear,
        "month": date.month,
        "trend_day": (date - history["observation_date"].min()).days,
    }
    for lag in LAGS:
        row[f"lag_{lag}"] = values[-lag]
    series = pd.Series(values)
    for window in ROLLING_WINDOWS:
        window_values = series.iloc[-window:]
        row[f"rolling_mean_{window}"] = float(window_values.mean())
        row[f"rolling_std_{window}"] = float(window_values.std(ddof=1))
    return row


def feature_columns() -> list[str]:
    numeric = [
        *(f"lag_{x}" for x in LAGS),
        *(f"rolling_mean_{x}" for x in ROLLING_WINDOWS),
        *(f"rolling_std_{x}" for x in ROLLING_WINDOWS),
        "day_of_week", "day_of_year", "month", "trend_day",
    ]
    return GROUP_COLUMNS + numeric
