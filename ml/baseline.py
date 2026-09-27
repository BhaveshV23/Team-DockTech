from __future__ import annotations
import pandas as pd


def seasonal_naive_predict(history: pd.DataFrame, dates: pd.DatetimeIndex, seasonal_lag: int = 7) -> pd.Series:
    history = history.sort_values("observation_date")
    values = list(history["freight_value"].astype(float))
    predictions = []
    for _ in dates:
        if len(values) < seasonal_lag:
            raise ValueError("Not enough history for seasonal-naive forecasting")
        pred = values[-seasonal_lag]
        predictions.append(pred)
        # Keep the baseline recursive for multi-step forecasting.
        values.append(pred)
    return pd.Series(predictions, index=dates)
