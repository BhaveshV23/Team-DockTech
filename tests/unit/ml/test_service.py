import json
import pandas as pd
from ml.model import train_improved_model, save_model
from ml.features import prepare_freight_data, make_features
from ml.service import ForecastService

def test_service_forecast(tmp_path):
    path=tmp_path/'freight.csv'
    rows=[]
    for i in range(100):
        rows.append({"freight_rate_id":f"F{i}","observation_date":(pd.Timestamp('2024-01-01')+pd.Timedelta(days=i)).date(),
                     "route_id":"R","vessel_class_id":"V","freight_value":20+0.1*i,
                     "freight_unit":"USD_PER_MT","currency":"USD","data_type":"SYNTHETIC","source":"TEST"})
    pd.DataFrame(rows).to_csv(path,index=False)
    df=prepare_freight_data(str(path)); model=train_improved_model(make_features(df))
    artifact=tmp_path/'model.joblib'; meta=tmp_path/'meta.json'
    save_model(model,str(artifact),str(meta),{"model_version":model.version,"training_period":{"end":"2024-04-09"}})
    service=ForecastService(str(path),str(artifact),str(meta))
    result=service.forecast('R','V','USD_PER_MT',7)
    assert len(result.points)==7
    assert result.points[0].lower <= result.points[0].central <= result.points[0].upper
