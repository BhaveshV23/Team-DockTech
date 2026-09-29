import { apiRequest } from "./api";
import type {
    RecommendationApiResponse,
    RecommendationRequest,
    RecommendationResult,
} from "../types/recommendation";

export async function createRecommendation(
    cargoRequestId: string
): Promise<RecommendationResult> {
    const payload: RecommendationRequest = {
        cargo_request_id: cargoRequestId,
        forecast_horizon: 30,
        freight_unit: "USD_PER_MT",
    };
    const response = await apiRequest<RecommendationApiResponse>(
        "/api/v1/recommendations",
        { method: "POST", body: JSON.stringify(payload) }
    );

    if (!response.success || !response.data) {
        throw new Error(response.message || "The backend returned no recommendation.");
    }
    return response.data;
}

function recommendationStorageKey(userId: string, cargoRequestId: string): string {
    return `docktech-recommendation:${userId}:${cargoRequestId}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null;
}

function isRecommendationResult(value: unknown): value is RecommendationResult {
    if (!isRecord(value)) return false;
    return typeof value.recommendation_id === "string" &&
        typeof value.cargo_request_id === "string" &&
        typeof value.forecast_run_id === "string" &&
        typeof value.recommended_vessel_class_id === "string" &&
        (value.market_entry_action === "FIX_NOW" || value.market_entry_action === "WAIT") &&
        (value.contract_strategy === "SPOT" || value.contract_strategy === "SHORT_TERM_MULTIPLE_VOYAGE") &&
        (typeof value.expected_freight_cost === "number" || typeof value.expected_freight_cost === "string") &&
        (typeof value.expected_total_cost === "number" || typeof value.expected_total_cost === "string") &&
        (typeof value.estimated_turnaround_hours === "number" || typeof value.estimated_turnaround_hours === "string") &&
        (value.risk_level === "LOW" || value.risk_level === "MEDIUM" || value.risk_level === "HIGH") &&
        (value.confidence === "LOW" || value.confidence === "MEDIUM" || value.confidence === "HIGH") &&
        typeof value.rationale === "string" &&
        typeof value.assumptions === "string" &&
        typeof value.created_at === "string";
}

export function storeRecommendation(
    userId: string,
    cargoRequestId: string,
    recommendation: RecommendationResult
): void {
    if (recommendation.cargo_request_id !== cargoRequestId) {
        throw new Error("Cannot store a recommendation for a different cargo request.");
    }
    sessionStorage.setItem(
        recommendationStorageKey(userId, cargoRequestId),
        JSON.stringify(recommendation)
    );
}

export function getStoredRecommendation(
    userId: string,
    cargoRequestId: string
): RecommendationResult | null {
    const stored = sessionStorage.getItem(recommendationStorageKey(userId, cargoRequestId));
    if (!stored) return null;

    try {
        const recommendation: unknown = JSON.parse(stored);
        return isRecommendationResult(recommendation) &&
            recommendation.cargo_request_id === cargoRequestId
            ? recommendation
            : null;
    } catch {
        return null;
    }
}
