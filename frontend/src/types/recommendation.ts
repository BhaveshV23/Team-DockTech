export type MarketEntryAction = "FIX_NOW" | "WAIT";
export type RecommendationContractStrategy = "SPOT" | "SHORT_TERM_MULTIPLE_VOYAGE";
export type RecommendationRiskLevel = "LOW" | "MEDIUM" | "HIGH";
export type RecommendationConfidence = "LOW" | "MEDIUM" | "HIGH";
export type RecommendationFreightUnit = "USD_PER_MT" | "USD_PER_DAY";

export interface RecommendationRequest {
    cargo_request_id: string;
    forecast_horizon: 30;
    freight_unit: "USD_PER_MT";
}

export type RecommendationDecimal = number | string;

export interface RecommendationResult {
    recommendation_id: string;
    cargo_request_id: string;
    forecast_run_id: string;
    recommended_vessel_class_id: string;
    market_entry_action: MarketEntryAction;
    contract_strategy: RecommendationContractStrategy;
    expected_freight_cost: RecommendationDecimal;
    expected_total_cost: RecommendationDecimal;
    estimated_turnaround_hours: RecommendationDecimal;
    risk_level: RecommendationRiskLevel;
    confidence: RecommendationConfidence;
    rationale: string;
    assumptions: string;
    created_at: string;
}

export interface RecommendationApiResponse {
    success: boolean;
    data: RecommendationResult | null;
    message: string | null;
}
