import numpy as np
from ml.metrics import mae, rmse, mape, directional_accuracy

def test_metrics():
    y = np.array([10, 20, 30])
    p = np.array([12, 18, 33])
    assert round(mae(y, p), 6) == round(7/3, 6)
    assert rmse(y, p) > 0
    assert mape(y, p) > 0
    assert 0 <= directional_accuracy(y, p, np.array([9, 21, 29])) <= 100
