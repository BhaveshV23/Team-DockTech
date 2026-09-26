import pandas as pd

from ml.features import GROUP_COLUMNS, make_features, prepare_freight_data


def _rows(route_id, vessel_id, unit, offset, count=40):
    start = pd.Timestamp("2024-01-01")
    return [
        {
            "freight_rate_id": f"{route_id}-{i}",
            "observation_date": (start + pd.Timedelta(days=i)).date(),
            "route_id": route_id,
            "vessel_class_id": vessel_id,
            "freight_value": offset + i,
            "freight_unit": unit,
            "currency": "USD",
            "data_type": "SYNTHETIC",
            "source": "TEST",
        }
        for i in range(count)
    ]


def test_feature_generation_is_leakage_safe_and_series_isolated(tmp_path):
    path = tmp_path / "freight.csv"
    rows = _rows("R1", "V1", "USD_PER_MT", 10) + _rows("R2", "V2", "USD_PER_DAY", 1000)
    pd.DataFrame(rows[::-1]).to_csv(path, index=False)

    data = prepare_freight_data(str(path))
    features = make_features(data)

    assert set(GROUP_COLUMNS) <= set(data.columns)
    assert data["observation_date"].is_monotonic_increasing is False
    assert data.groupby(GROUP_COLUMNS, sort=False)["observation_date"].apply(
        lambda dates: dates.is_monotonic_increasing
    ).all()
    target_date = pd.Timestamp("2024-02-05")
    row = features[
        (features.route_id == "R1") & (features.observation_date == target_date)
    ].iloc[0]
    assert row["lag_1"] == 44
    assert row["rolling_mean_7"] == 41

    changed = data.copy()
    changed.loc[
        (changed.route_id == "R1") & (changed.observation_date > target_date),
        "freight_value",
    ] += 10000
    changed_features = make_features(changed)
    changed_row = changed_features[
        (changed_features.route_id == "R1") & (changed_features.observation_date == target_date)
    ].iloc[0]
    assert row[["lag_1", "rolling_mean_7", "rolling_std_7"]].equals(
        changed_row[["lag_1", "rolling_mean_7", "rolling_std_7"]]
    )

    other = features[
        (features.route_id == "R2") & (features.observation_date == target_date)
    ].iloc[0]
    assert other["lag_1"] == 1034
