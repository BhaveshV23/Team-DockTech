export type ForecastHorizon = 7 | 30 | 90;
export type FreightUnit = "USD_PER_MT" | "USD_PER_DAY";

export interface ForecastRequest {
    cargo_request_id: string;
    route_id: string;
    vessel_class_id: string;
    freight_unit: FreightUnit;
    horizon: ForecastHorizon;
}

export interface ForecastPointResponse {
    forecast_point_id?: string | null;
    forecast_date: string;
    central_value: number;
    lower_value: number;
    upper_value: number;
    unit: string;
}

export interface ForecastRunResponse {
    forecast_run_id: string;
    cargo_request_id: string;
    route_id: string;
    vessel_class_id: string;
    freight_unit: string;
    model_name: string;
    model_version: string;
    training_data_end_date: string;
    forecast_points: ForecastPointResponse[];
}
