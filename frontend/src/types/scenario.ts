export type ScenarioType = "BASELINE" | "ADVERSE" | "FAVORABLE";
export type CongestionLevel = "LOW" | "MEDIUM" | "HIGH";
export type ScenarioRiskLevel = "LOW" | "MEDIUM" | "HIGH";

export interface ScenarioDefault {
    scenario_id: ScenarioType;
    scenario_name: string;
    freight_change_pct: number;
    fuel_change_pct: number;
    delay_hours: number;
    port_congestion_level: CongestionLevel;
    description: string;
}

export interface VoyageCostBreakdown {
    sailing_days: number;
    required_voyages: number;
    origin_handling_hours_total: number;
    destination_handling_hours_total: number;
    waiting_hours_total: number;
    scenario_delay_total: number;
    estimated_turnaround_hours: number;
    turnaround_hours_per_voyage: number;
    port_days_per_voyage: number;
    vessel_days_per_voyage: number;
    total_fuel_cost_usd: number;
    expected_freight_cost: number;
    expected_total_cost: number;
    effective_cost_per_mt: number;
}

export interface ScenarioResult {
    scenario_instance_id: string;
    cargo_request_id: string;
    scenario_type: ScenarioType;
    freight_change_pct: number;
    fuel_change_pct: number;
    delay_hours: number;
    congestion_level: CongestionLevel;
    estimated_total_cost: number;
    estimated_turnaround_hours: number;
    cost_breakdown: VoyageCostBreakdown;
    risk_level: ScenarioRiskLevel;
    created_at: string;
}

export interface CanonicalScenarioSet {
    baseline: ScenarioResult;
    adverse: ScenarioResult;
    favorable: ScenarioResult;
}

export interface CustomScenarioRequest {
    cargo_request_id: string;
    forecast_run_id: string;
    freight_change_pct: number;
    fuel_change_pct: number;
    delay_hours: number;
    congestion_level: CongestionLevel;
}

export interface ScenarioComparison {
    baseline_result: ScenarioResult;
    scenario_result: ScenarioResult;
    delta_cost_usd: number;
    delta_cost_pct: number;
    delta_turnaround_hours: number;
    delta_effective_cost_per_mt: number;
    risk_transition: string;
}

export interface ScenarioApiResponse<T> {
    success: boolean;
    data: T | null;
    message: string | null;
}
