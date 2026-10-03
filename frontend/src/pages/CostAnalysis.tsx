import { useEffect, useRef, useState } from "react";
import {
    AlertCircle,
    ArrowLeft,
    BarChart3,
    Calculator,
    Info,
} from "lucide-react";
import { Link } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import DataProvenance from "../components/DataProvenance";
import { useCargoRequest } from "../hooks/useCargoRequest";
import { apiRequest, startPageLoadTiming, useAuthenticatedUser } from "../services/api";
import { getStoredRecommendation } from "../services/recommendation";
import type { CargoRequestResponse } from "../types/cargo";
import type { RecommendationResult } from "../types/recommendation";
import "./CostAnalysis.css";

type CostResponse = {
    required_voyages: number;
    sailing_days_per_voyage: number;
    origin_handling_hours_total: number;
    dest_handling_hours_total: number;
    waiting_hours_total: number;
    scenario_delay_hours_total: number;
    estimated_turnaround_hours: number;
    port_days_per_voyage: number;
    vessel_days_per_voyage: number;
    vlsfo_price_used: number;
    total_fuel_consumption_mt: number;
    total_fuel_cost_usd: number;
    freight_rate_used: number;
    freight_unit: string;
    expected_freight_cost: number;
    port_costs_usd: number;
    expected_total_cost: number;
    effective_cost_per_mt: number;
    cost_reference_date: string;
    assumptions: string[];
};

type CostPageData = {
    cargo: CargoRequestResponse;
    recommendation: RecommendationResult;
    cost: CostResponse;
};

type PageState =
    | { status: "loading" }
    | { status: "success"; data: CostPageData }
    | { status: "error"; message: string }
    | { status: "empty" };

function formatUsd(value: number): string {
    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 2,
    }).format(value);
}

function formatFreightUnit(unit: string): string {
    return unit.replace("_PER_", " / ");
}

function CostAnalysis() {
    const storedCargo = useCargoRequest();
    const user = useAuthenticatedUser();
    const cargoRequestId = storedCargo?.cargo_request_id;
    const cargoUserId = storedCargo?.user_id;
    const userId = user?.user_id;
    const [retryCount, setRetryCount] = useState(0);
    const [pageState, setPageState] = useState<PageState>(
        cargoRequestId && cargoUserId && userId ? { status: "loading" } : { status: "empty" },
    );
    const operationRef = useRef<{
        key: string;
        promise: Promise<CostPageData>;
    } | null>(null);

    useEffect(() => {
        if (!cargoRequestId || !cargoUserId || !userId) return;

        let active = true;
        const finishTiming = startPageLoadTiming("Cost Analysis");
        const key = `${userId}:${cargoRequestId}`;
        let promise = operationRef.current?.key === key
            ? operationRef.current.promise
            : null;

        if (!promise) {
            promise = (async () => {
                const cargo = await apiRequest<CargoRequestResponse>(
                    `/api/v1/cargo-requests/${encodeURIComponent(cargoRequestId)}`,
                );
                if (
                    cargo.cargo_request_id !== cargoRequestId ||
                    cargo.user_id !== userId ||
                    cargoUserId !== userId
                ) {
                    throw new Error("The active cargo request could not be verified.");
                }

                const recommendation = getStoredRecommendation(userId, cargoRequestId);
                if (
                    !recommendation ||
                    recommendation.cargo_request_id !== cargoRequestId ||
                    !recommendation.recommended_vessel_class_id ||
                    !recommendation.forecast_run_id
                ) {
                    throw new Error("No matching cached recommendation is available. Open Decision Overview before viewing cost analysis.");
                }
                const cost = await apiRequest<CostResponse>("/api/v1/cost", {
                    method: "POST",
                    body: JSON.stringify({
                        cargo_request_id: cargoRequestId,
                        forecast_run_id: recommendation.forecast_run_id,
                        use_forecast_central_rate: true,
                    }),
                });
                return { cargo, recommendation, cost };
            })();
            operationRef.current = { key, promise };
        }

        void promise.then((data) => {
            if (active) setPageState({ status: "success", data });
        }).catch((requestError: unknown) => {
            if (active) {
                setPageState({
                    status: "error",
                    message: requestError instanceof Error
                        ? requestError.message
                        : "Unable to load cost analysis.",
                });
            }
        }).finally(finishTiming);

        return () => { active = false; };
    }, [cargoRequestId, cargoUserId, retryCount, userId]);

    const retry = () => {
        if (!cargoRequestId || !cargoUserId || !userId) return;
        operationRef.current = null;
        setPageState({ status: "loading" });
        setRetryCount((count) => count + 1);
    };

    const showEmpty = !cargoRequestId || !cargoUserId || pageState.status === "empty";
    const data = pageState.status === "success" ? pageState.data : null;
    const cargo = data?.cargo;
    const recommendation = data?.recommendation;
    const cost = data?.cost;

    return (
        <div className="cost-analysis-page">
            <Sidebar activePage="cost-analysis" />

            <main className="cost-analysis-main">
                <Link to="/decision-overview" className="cost-back-link">
                    <ArrowLeft size={16} />
                    Back to Decision Overview
                </Link>

                <header className="cost-page-header">
                    <div>
                        <span className="cost-eyebrow">COST ANALYSIS</span>
                        <h1>Cost Analysis</h1>
                        <p>Backend-calculated costs for the selected vessel and active cargo request.</p>
                    </div>
                    <div className="cost-status" role={pageState.status === "error" ? "alert" : undefined}>
                        <span className="cost-status-dot"></span>
                        {showEmpty ? "No active request" : pageState.status === "loading" ? "Loading cost data" : pageState.status === "success" ? "Cost available" : "Cost unavailable"}
                    </div>
                </header>

                <DataProvenance />

                {showEmpty ? (
                    <section className="cost-comparison-card">
                        <div className="cost-empty-state" role="status">
                            <div className="cost-empty-icon"><AlertCircle size={25} /></div>
                            <h3>No active cargo request</h3>
                            <p>Create a cargo request before viewing its selected-vessel cost.</p>
                            <Link to="/cargo-request">Create Cargo Request</Link>
                        </div>
                    </section>
                ) : pageState.status === "loading" ? (
                    <section className="cost-comparison-card">
                        <div className="cost-empty-state" role="status" aria-live="polite">
                            <div className="cost-empty-icon"><Calculator size={25} /></div>
                            <h3>Loading cost analysis</h3>
                            <p>Verifying cargo, obtaining the backend recommendation, and loading its cost result.</p>
                        </div>
                    </section>
                ) : pageState.status === "error" ? (
                    <section className="cost-comparison-card">
                        <div className="cost-empty-state" role="alert">
                            <div className="cost-empty-icon"><AlertCircle size={25} /></div>
                            <h3>Cost analysis unavailable</h3>
                            <p>{pageState.message}</p>
                            <button type="button" onClick={retry}>Retry</button>
                        </div>
                    </section>
                ) : cost && cargo && recommendation ? (
                    <>
                        <section className="cost-request-card">
                            <div>
                                <span className="cost-request-label">VERIFIED CARGO REQUEST</span>
                                <h2>{cargo.commodity.replace(/_/g, " ")}</h2>
                            </div>
                            <div className="cost-request-details">
                                <div><span>Volume</span><strong>{cargo.cargo_volume_mt.toLocaleString()} MT</strong></div>
                                <div><span>Route</span><strong>{cargo.origin_port_id} → {cargo.destination_port_id}</strong></div>
                                <div><span>Selected Vessel</span><strong>{recommendation.recommended_vessel_class_id}</strong></div>
                                <div><span>Required Voyages</span><strong>{cost.required_voyages}</strong></div>
                            </div>
                        </section>

                        <section className="cost-total-card">
                            <div className="cost-total-icon"><Calculator size={21} /></div>
                            <div>
                                <span>Expected Total Cost</span>
                                <strong>{formatUsd(cost.expected_total_cost)}</strong>
                                <p>Backend result for {recommendation.recommended_vessel_class_id}; no frontend cost calculation.</p>
                            </div>
                        </section>

                        <section className="cost-section">
                            <div className="cost-section-heading">
                                <div><h2>Cost Components</h2><p>Values returned by the Cost API.</p></div>
                            </div>
                            <div className="cost-component-grid">
                                <div className="cost-component-card">
                                    <div className="cost-component-icon"><BarChart3 size={18} /></div>
                                    <span>Expected Freight Cost</span>
                                    <strong>{formatUsd(cost.expected_freight_cost)}</strong>
                                    <small>Freight rate: {formatUsd(cost.freight_rate_used)} {formatFreightUnit(cost.freight_unit)}</small>
                                </div>
                                <div className="cost-component-card">
                                    <div className="cost-component-icon"><Calculator size={18} /></div>
                                    <span>Total Fuel Cost</span>
                                    <strong>{formatUsd(cost.total_fuel_cost_usd)}</strong>
                                    <small>Fuel consumption: {cost.total_fuel_consumption_mt.toLocaleString()} MT</small>
                                </div>
                                <div className="cost-component-card">
                                    <div className="cost-component-icon"><BarChart3 size={18} /></div>
                                    <span>Port Costs</span>
                                    <strong>{formatUsd(cost.port_costs_usd)}</strong>
                                    <small>Effective cost: {formatUsd(cost.effective_cost_per_mt)} / MT</small>
                                </div>
                            </div>
                        </section>

                        <section className="cost-section">
                            <div className="cost-section-heading">
                                <div><h2>Operational Breakdown</h2><p>Operational values returned by the Cost API.</p></div>
                            </div>
                            <div className="cost-operational-grid">
                                <div className="cost-operational-item"><span>Sailing time / voyage</span><strong>{cost.sailing_days_per_voyage.toFixed(2)} days</strong></div>
                                <div className="cost-operational-item"><span>Origin handling time</span><strong>{cost.origin_handling_hours_total.toFixed(2)} h</strong></div>
                                <div className="cost-operational-item"><span>Destination handling time</span><strong>{cost.dest_handling_hours_total.toFixed(2)} h</strong></div>
                                <div className="cost-operational-item"><span>Waiting time</span><strong>{cost.waiting_hours_total.toFixed(2)} h</strong></div>
                                <div className="cost-operational-item"><span>Scenario delay</span><strong>{cost.scenario_delay_hours_total.toFixed(2)} h</strong></div>
                                <div className="cost-operational-item"><span>Turnaround</span><strong>{cost.estimated_turnaround_hours.toFixed(2)} h</strong></div>
                                <div className="cost-operational-item"><span>Required voyages</span><strong>{cost.required_voyages.toFixed(0)}</strong></div>
                            </div>
                        </section>

                        <section className="cost-comparison-card">
                            <div className="cost-card-header">
                                <div>
                                    <h2>Feasible Vessel Cost Comparison</h2>
                                    <p>Backend-calculated economics and risk for each feasible vessel candidate.</p>
                                </div>
                                <span className="cost-option-count">{recommendation.candidate_comparisons?.length ?? 0} feasible options</span>
                            </div>
                            {recommendation.candidate_comparisons?.length ? (
                                <div className="cost-table-wrapper">
                                    <table className="cost-comparison-table">
                                        <thead><tr><th>Vessel Class</th><th>Feasibility</th><th>Expected Freight</th><th>Expected Total Cost</th><th>Effective Cost / MT</th><th>Turnaround</th><th>Required Voyages</th><th>Risk</th></tr></thead>
                                        <tbody>{recommendation.candidate_comparisons.map((option) => (
                                            <tr key={option.vessel_class_id}>
                                                <td>{option.vessel_class_id}{option.vessel_class_id === recommendation.recommended_vessel_class_id ? <span className="cost-recommended-badge">Recommended</span> : null}</td>
                                                <td>{option.feasibility_status}</td>
                                                <td>{formatUsd(Number(option.expected_freight_cost))}</td>
                                                <td>{formatUsd(Number(option.expected_total_cost))}</td>
                                                <td>{formatUsd(Number(option.effective_cost_per_mt))} / MT</td>
                                                <td>{Number(option.estimated_turnaround_hours).toFixed(2)} h</td>
                                                <td>{option.required_voyages}</td>
                                                <td>{option.risk_level}</td>
                                            </tr>
                                        ))}</tbody>
                                    </table>
                                </div>
                            ) : <p className="cost-no-comparisons">No feasible-vessel comparison was returned with this saved recommendation.</p>}
                        </section>

                        <section className="cost-comparison-card">
                            <div className="cost-card-header">
                                <div>
                                    <h2>Selected Vessel Cost Breakdown</h2>
                                    <p>One cost result for the vessel selected by the backend recommendation.</p>
                                </div>
                                <span className="cost-option-count">1 selected option</span>
                            </div>
                            <div className="cost-table-wrapper">
                                <table className="cost-comparison-table">
                                    <thead><tr><th>Selected Vessel</th><th>Expected Freight Cost</th><th>Expected Total Cost</th><th>Effective Cost / MT</th><th>Turnaround</th><th>Voyages</th></tr></thead>
                                    <tbody><tr>
                                        <td>{recommendation.recommended_vessel_class_id}</td>
                                        <td>{formatUsd(cost.expected_freight_cost)}</td>
                                        <td>{formatUsd(cost.expected_total_cost)}</td>
                                        <td>{formatUsd(cost.effective_cost_per_mt)} / MT</td>
                                        <td>{cost.estimated_turnaround_hours.toFixed(2)} h</td>
                                        <td>{cost.required_voyages.toFixed(0)}</td>
                                    </tr></tbody>
                                </table>
                            </div>
                        </section>

                        <section className="cost-information-grid">
                            <div className="cost-information-card">
                                <div className="cost-information-title"><Info size={18} /><h2>Cost Assumptions</h2></div>
                                {cost.assumptions.length > 0 ? <ul>{cost.assumptions.map((assumption, index) => <li key={`${index}-${assumption}`}>{assumption}</li>)}</ul> : <p>No assumptions were returned.</p>}
                            </div>
                            <div className="cost-information-card">
                                <div className="cost-information-title"><AlertCircle size={18} /><h2>Data Status</h2></div>
                                <div className="cost-info-row"><span>Cost reference date</span><strong>{cost.cost_reference_date}</strong></div>
                                <div className="cost-info-row"><span>Forecast run</span><strong>{recommendation.forecast_run_id}</strong></div>
                                <div className="cost-info-row"><span>Recommendation created</span><strong>{new Date(recommendation.created_at).toLocaleString()}</strong></div>
                            </div>
                        </section>
                    </>
                ) : null}
            </main>
        </div>
    );
}

export default CostAnalysis;
