import { useEffect, useRef, useState } from "react";
import {
    AlertTriangle,
    BarChart3,
    CheckCircle2,
    Ship,
    TrendingUp,
} from "lucide-react";
import { Link } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import { useCargoRequest } from "../hooks/useCargoRequest";
import { apiRequest, useAuthenticatedUser } from "../services/api";
import {
    createRecommendation,
    getStoredRecommendation,
    storeRecommendation,
} from "../services/recommendation";
import type { CargoRequestResponse } from "../types/cargo";
import type { RecommendationResult } from "../types/recommendation";
import "./DecisionOverview.css";

type DecisionData = {
    cargoRequest: CargoRequestResponse;
    recommendation: RecommendationResult;
};

type PageState =
    | { status: "loading" }
    | { status: "success"; data: DecisionData }
    | { status: "error"; message: string }
    | { status: "empty" };

function formatMoney(value: number | string): string {
    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 2,
    }).format(Number(value));
}

function formatDateTime(value: string): string {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function DecisionOverview() {
    const storedCargo = useCargoRequest();
    const user = useAuthenticatedUser();
    const cargoRequestId = storedCargo?.cargo_request_id;
    const userId = user?.user_id;
    const [retryCount, setRetryCount] = useState(0);
    const [pageState, setPageState] = useState<PageState>(
        cargoRequestId ? { status: "loading" } : { status: "empty" },
    );
    const operationRef = useRef<{
        key: string;
        promise: Promise<DecisionData>;
    } | null>(null);

    useEffect(() => {
        if (!cargoRequestId || !userId) return;

        let active = true;
        const key = `${userId}:${cargoRequestId}`;
        let promise = operationRef.current?.key === key
            ? operationRef.current.promise
            : null;

        if (!promise) {
            promise = (async () => {
                const cargoRequest = await apiRequest<CargoRequestResponse>(
                    `/api/v1/cargo-requests/${encodeURIComponent(cargoRequestId)}`,
                );
                if (
                    cargoRequest.cargo_request_id !== cargoRequestId ||
                    cargoRequest.user_id !== userId
                ) {
                    throw new Error("The saved cargo request does not match the current user or request.");
                }

                const cachedRecommendation = getStoredRecommendation(userId, cargoRequestId);
                const recommendation = cachedRecommendation ??
                    await createRecommendation(cargoRequestId);
                if (recommendation.cargo_request_id !== cargoRequestId) {
                    throw new Error("The backend recommendation belongs to a different cargo request.");
                }
                if (!cachedRecommendation) {
                    storeRecommendation(userId, cargoRequestId, recommendation);
                }
                return { cargoRequest, recommendation };
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
                        : "Unable to load the cargo decision.",
                });
            }
        });

        return () => { active = false; };
    }, [cargoRequestId, retryCount, userId]);

    const retry = () => {
        if (cargoRequestId && userId) {
            operationRef.current = null;
            setPageState({ status: "loading" });
            setRetryCount((count) => count + 1);
        }
    };

    const data = pageState.status === "success" ? pageState.data : null;
    const cargo = data?.cargoRequest;
    const recommendation = data?.recommendation;
    const showEmptyCargo = pageState.status === "empty" || !cargoRequestId || !userId;

    return (
        <div className="decision-overview-page">
            <Sidebar activePage="decision-overview" />

            <main className="decision-main">
                <header className="decision-header">
                    <div>
                        <p className="decision-eyebrow">Decision Support</p>
                        <h1>Decision Overview</h1>
                        <p className="decision-subtitle">
                            Review the backend recommendation for the current cargo request.
                        </p>
                    </div>
                </header>

                {showEmptyCargo ? (
                    <section className="decision-panel" aria-live="polite">
                        <div className="decision-empty-state">
                            <Ship size={34} />
                            <h2>No active cargo request</h2>
                            <p>Create a cargo request to generate a freight decision.</p>
                            <Link to="/cargo-request" className="decision-new-request">Create Cargo Request</Link>
                        </div>
                    </section>
                ) : pageState.status === "loading" ? (
                    <section className="decision-panel" role="status" aria-live="polite">
                        <div className="decision-empty-state">
                            <TrendingUp size={34} />
                            <h2>Loading decision</h2>
                            <p>Verifying the saved cargo request and loading its recommendation.</p>
                        </div>
                    </section>
                ) : pageState.status === "error" ? (
                    <section className="decision-panel" role="alert">
                        <div className="decision-empty-state">
                            <AlertTriangle size={34} />
                            <h2>Decision unavailable</h2>
                            <p>{pageState.message}</p>
                            <button type="button" className="decision-new-request" onClick={retry}>Retry</button>
                        </div>
                    </section>
                ) : (
                    <>
                        <section className="decision-request-card">
                            <div className="decision-request-heading">
                                <div>
                                    <span>VERIFIED CARGO REQUEST</span>
                                    <h2>{cargo?.commodity.replace(/_/g, " ")}</h2>
                                </div>
                                <Link to="/cargo-request">New Request</Link>
                            </div>
                            <div className="decision-request-grid">
                                <div><span>Commodity</span><strong>{cargo?.commodity.replace(/_/g, " ")}</strong></div>
                                <div><span>Cargo Volume</span><strong>{cargo?.cargo_volume_mt} MT</strong></div>
                                <div><span>Origin</span><strong>{cargo?.origin_port_id}</strong></div>
                                <div><span>Destination</span><strong>{cargo?.destination_port_id}</strong></div>
                                <div><span>Delivery Window</span><strong>{cargo?.earliest_delivery_date} → {cargo?.latest_delivery_date}</strong></div>
                                <div><span>Contract Horizon</span><strong>{cargo?.contract_horizon.replace(/_/g, " ")}</strong></div>
                            </div>
                        </section>

                        <section className="decision-summary-grid" aria-label="Recommendation summary">
                            <div className="decision-summary-card"><div className="decision-summary-icon"><TrendingUp size={19} /></div><span>Market Entry</span><strong>{recommendation?.market_entry_action}</strong><small>Backend recommendation</small></div>
                            <div className="decision-summary-card"><div className="decision-summary-icon"><Ship size={19} /></div><span>Recommended Vessel</span><strong>{recommendation?.recommended_vessel_class_id}</strong><small>{recommendation?.contract_strategy.replace(/_/g, " ")}</small></div>
                            <div className="decision-summary-card"><div className="decision-summary-icon"><BarChart3 size={19} /></div><span>Expected Total Cost</span><strong>{recommendation && formatMoney(recommendation.expected_total_cost)}</strong><small>USD</small></div>
                            <div className="decision-summary-card"><div className="decision-summary-icon"><AlertTriangle size={19} /></div><span>Risk / Confidence</span><strong>{recommendation?.risk_level} / {recommendation?.confidence}</strong><small>Categorical assessments</small></div>
                        </section>

                        <section className="decision-content-grid">
                            <div className="decision-panel">
                                <div className="decision-panel-header"><div><span>RECOMMENDATION</span><h2>{recommendation?.market_entry_action}</h2></div><CheckCircle2 size={19} /></div>
                                <div className="decision-empty-state">
                                    <h3>{recommendation?.recommended_vessel_class_id} · {recommendation?.contract_strategy.replace(/_/g, " ")}</h3>
                                    <p>{recommendation?.rationale}</p>
                                </div>
                                <div className="decision-request-grid">
                                    <div><span>Expected Freight Cost</span><strong>{recommendation && formatMoney(recommendation.expected_freight_cost)}</strong></div>
                                    <div><span>Expected Total Cost</span><strong>{recommendation && formatMoney(recommendation.expected_total_cost)}</strong></div>
                                    <div><span>Estimated Turnaround</span><strong>{recommendation && Number(recommendation.estimated_turnaround_hours).toFixed(2)} h</strong></div>
                                    <div><span>Risk</span><strong>{recommendation?.risk_level}</strong></div>
                                    <div><span>Confidence</span><strong>{recommendation?.confidence}</strong></div>
                                </div>
                            </div>

                            <div className="decision-panel assumptions-panel">
                                <div className="decision-panel-header"><div><span>DECISION EVIDENCE</span><h2>Assumptions & Provenance</h2></div></div>
                                <div className="decision-assumptions-empty">
                                    <p>{recommendation?.assumptions}</p>
                                    <p><strong>Forecast Run ID:</strong> {recommendation?.forecast_run_id}</p>
                                    <p><strong>Created:</strong> {recommendation && formatDateTime(recommendation.created_at)}</p>
                                    <p><strong>Recommendation ID:</strong> {recommendation?.recommendation_id}</p>
                                </div>
                            </div>
                        </section>
                    </>
                )}

                <nav aria-label="Decision details">
                    <h2>Explore decision details</h2>
                    <div>
                        <Link to="/freight-forecast" className="decision-new-request">Freight Forecast</Link>{" "}
                        <Link to="/vessel-options" className="decision-new-request">Vessel Options</Link>{" "}
                        <Link to="/cost-analysis" className="decision-new-request">Cost Analysis</Link>{" "}
                        <Link to="/scenarios-risk" className="decision-new-request">Scenarios &amp; Risk</Link>{" "}
                        <Link to="/recommendation" className="decision-new-request">Recommendation</Link>
                        {recommendation && <>{" "}<Link to="/decision-report" state={{ recommendation }} className="decision-new-request">Decision Report</Link></>}
                    </div>
                </nav>
            </main>
        </div>
    );
}

export default DecisionOverview;
