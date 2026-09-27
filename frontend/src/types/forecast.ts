export type ForecastHorizon = 7 | 30 | 90;

export interface ForecastPoint {
    date: string;
    historical?: number;
    centralForecast?: number;
    lowerForecast?: number;
    upperForecast?: number;
}

export interface FreightForecast {
    horizon: ForecastHorizon;
    unit: string;
    points: ForecastPoint[];
}