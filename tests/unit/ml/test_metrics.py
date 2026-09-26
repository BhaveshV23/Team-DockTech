import numpy as np

from ml.metrics import directional_accuracy, mae, mape, rmse


def test_mae_exact_value():
    assert mae([1, 2, 3], [2, 4, 0]) == 2


def test_rmse_exact_value():
    assert np.isclose(rmse([1, 2, 3], [2, 4, 0]), np.sqrt(14 / 3))


def test_mape_exact_value():
    assert np.isclose(mape([10, 20, 30], [12, 18, 33]), 40 / 3)


def test_mape_ignores_zero_and_near_zero_denominators():
    assert mape([0, 1e-12, 10], [1000, 1, 12]) == 20
    assert np.isnan(mape([0, 1e-12], [1, 1]))


def test_directional_accuracy_exact_value():
    assert directional_accuracy([11, 18, 30], [12, 18, 33], [10, 20, 29]) == 100


def test_directional_accuracy_counts_direction_mismatches():
    assert directional_accuracy([11, 18, 30], [9, 22, 25], [10, 20, 29]) == 0
