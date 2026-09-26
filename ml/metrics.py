from __future__ import annotations
import numpy as np


def mae(y_true, y_pred) -> float:
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true, y_pred) -> float:
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mape(y_true, y_pred, eps: float = 1e-6) -> float:
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    if y_true.size == 0:
        return float("nan")
    denom = np.abs(y_true)
    safe = np.where(denom > eps, True, False)
    if not safe.any():
        return float("nan")
    relative = np.abs((y_true[safe] - y_pred[safe]) / denom[safe])
    return float(np.mean(relative) * 100)


def directional_accuracy(y_true, y_pred, previous):
    y_true, y_pred, previous = map(np.asarray, (y_true, y_pred, previous))
    actual_direction = np.sign(y_true - previous)
    predicted_direction = np.sign(y_pred - previous)
    return float(np.mean(actual_direction == predicted_direction) * 100)
