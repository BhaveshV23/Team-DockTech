import pandas as pd
from ml.features import prepare_freight_data, make_features

def test_feature_generation_is_leakage_safe(tmp_path):
    path = tmp_path / 'freight.csv'
    rows=[]
    for i in range(35):
        rows.append({"freight_rate_id": f"F{i}", "observation_date": (pd.Timestamp('2024-01-01')+pd.Timedelta(days=i)).date(),
                     "route_id":"R", "vessel_class_id":"V", "freight_value":10+i,
                     "freight_unit":"USD_PER_MT", "currency":"USD", "data_type":"SYNTHETIC", "source":"TEST"})
    pd.DataFrame(rows).to_csv(path,index=False)
    df=prepare_freight_data(str(path))
    features=make_features(df)
    first=features.iloc[0]
    assert first['lag_1'] < first['freight_value']
    assert first['rolling_mean_7'] < first['freight_value']
