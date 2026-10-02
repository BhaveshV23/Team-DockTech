import {
    AlertTriangle,
    ArrowLeft,
    CheckCircle2,
    Info,
    ShieldCheck,
    Target,
} from "lucide-react";
import { Link } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import DataProvenance from "../components/DataProvenance";
import { useCargoRequest } from "../hooks/useCargoRequest";
import { useAuthenticatedUser } from "../services/api";
import { getStoredRecommendation } from "../services/recommendation";
import "./Recommendation.css";

type PageStatus = "success" | "error";

function isUuid(value: string | undefined): value is string {
    return Boolean(value && /^[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}$/i.test(value));
}

function formatUsd(value: number | string): string {
    const numericValue = Number(value);
    return Number.isFinite(numericValue)
        ? new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "USD",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(numericValue)
        : "--";
}

function formatHours(value: number | string): string {
    const numericValue = Number(value);
    return Number.isFinite(numericValue) ? `${numericValue.toFixed(2)} h` : "--";
}

function formatAssumptions(value: string): string[] {
    const ratePattern = /([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s+(USD_PER_MT|USD_PER_DAY)/g;
    const formatted = value.replace(ratePattern, (_match, amount: string, unit: string) => {
        const displayUnit = unit === "USD_PER_MT" ? "/ MT" : "/ day";
        return `${formatUsd(amount)} ${displayUnit}`;
    });
    return formatted.split(/(?<=[.;])\s+/).map((assumption) => assumption.trim()).filter(Boolean);
}

function formatTimestamp(value: string): string {
    const timestamp = new Date(value);
    return Number.isNaN(timestamp.getTime()) ? value : timestamp.toLocaleString();
}

function Recommendation() {
    const cargoRequest = useCargoRequest();
    const user = useAuthenticatedUser();
    const cargoRequestId = cargoRequest?.cargo_request_id;
    const hasValidCargoRequestId = isUuid(cargoRequestId);
    const userId = user?.user_id;
    const recommendation = hasValidCargoRequestId && userId
        ? getStoredRecommendation(userId, cargoRequestId)
        : null;
    const status: PageStatus = recommendation
        ? "success"
        : "error";
    const errorMessage = !hasValidCargoRequestId
        ? "No valid saved cargo request was found. Create a cargo request before viewing its recommendation."
        : "No recommendation is stored for this cargo in the current workflow. Open Decision Overview to load the decision, then return here.";

    const displayedValue = (value: string | undefined) => {
        return status === "success" ? value ?? "--" : "--";
    };

    return (
        <div className="recommendation-page">
            <Sidebar activePage="recommendation" />

            <main className="recommendation-main">
                {/* Back navigation */}
                <Link
                    to="/decision-overview"
                    className="recommendation-back-link"
                >
                    <ArrowLeft size={16} />
                    Back to Decision Overview
                </Link>

                {/* Header */}
                <header className="recommendation-page-header">
                    <div>
                        <span className="recommendation-eyebrow">
                            DECISION ENGINE
                        </span>

                        <h1>Final Recommendation</h1>

                        <p>
                            Review the backend-generated procurement
                            recommendation and its supporting rationale.
                        </p>
                    </div>

                    <div className="recommendation-status">
                        <span className="recommendation-status-dot"></span>
                        {status === "success"
                            ? "Recommendation ready"
                            : "Recommendation unavailable"}
                    </div>
                </header>

                <DataProvenance />

                {/* Cargo Request Context */}
                <section className="recommendation-request-card">
                    <div>
                        <span className="recommendation-request-label">
                            CURRENT CARGO REQUEST
                        </span>

                        <h2>
                            {cargoRequest
                                ? cargoRequest.commodity.replace(/_/g, " ")
                                : "No active request"}
                        </h2>
                    </div>

                    <div className="recommendation-request-details">
                        <div>
                            <span>Volume</span>
                            <strong>
                                {cargoRequest
                                    ? `${cargoRequest.cargoVolume.toLocaleString("en-US", { maximumFractionDigits: 2 })} MT`
                                    : "--"}
                            </strong>
                        </div>

                        <div>
                            <span>Origin</span>
                            <strong>
                                {cargoRequest
                                    ? cargoRequest.originPort
                                    : "--"}
                            </strong>
                        </div>

                        <div>
                            <span>Destination</span>
                            <strong>
                                {cargoRequest
                                    ? cargoRequest.destinationPort
                                    : "--"}
                            </strong>
                        </div>

                        <div>
                            <span>Delivery Window</span>
                            <strong>
                                {cargoRequest
                                    ? `${cargoRequest.deliveryStartDate} → ${cargoRequest.deliveryEndDate}`
                                    : "--"}
                            </strong>
                        </div>
                    </div>
                </section>

                {/* Recommendation Result */}
                <section className="recommendation-result-card">
                    <div className="recommendation-result-icon">
                        <Target size={24} />
                    </div>

                    <div className="recommendation-result-content">
                        <span>Recommended Action</span>

                        <h2>{displayedValue(recommendation?.market_entry_action)}</h2>

                        {status === "success" && recommendation ? (
                            <div className="recommendation-vessel">
                                <span>Recommended Vessel</span>
                                <strong>{recommendation.recommended_vessel_class_id}</strong>
                            </div>
                        ) : <p>No recommendation result is available.</p>}
                    </div>

                    <span className="recommendation-confidence">
                        Confidence: {displayedValue(recommendation?.confidence)}
                    </span>
                </section>

                {/* Strategy */}
                <section className="recommendation-strategy-grid">
                    <div className="recommendation-strategy-card">
                        <div className="recommendation-card-icon">
                            <ShieldCheck size={19} />
                        </div>

                        <span>Contract Strategy</span>

                        <strong>
                            {displayedValue(recommendation?.contract_strategy?.replace(/_/g, " "))}
                        </strong>

                        <small>Backend-selected strategy</small>
                    </div>

                    <div className="recommendation-strategy-card">
                        <div className="recommendation-card-icon">
                            <CheckCircle2 size={19} />
                        </div>

                        <span>Expected Freight</span>

                        <strong>
                            {status === "success" && recommendation
                                ? formatUsd(recommendation.expected_freight_cost)
                                : displayedValue(undefined)}
                        </strong>

                        <small>Backend-generated value</small>
                    </div>

                    <div className="recommendation-strategy-card">
                        <div className="recommendation-card-icon">
                            <AlertTriangle size={19} />
                        </div>

                        <span>Risk</span>

                        <strong>{displayedValue(recommendation?.risk_level)}</strong>

                        <small>Backend-generated assessment</small>
                    </div>
                </section>

                {/* Decision Metrics */}
                <section className="recommendation-metrics-card">
                    <div className="recommendation-section-header">
                        <div>
                            <h2>Decision Metrics</h2>

                            <p>
                                Key values supporting the backend-generated
                                recommendation.
                            </p>
                        </div>
                    </div>

                    <div className="recommendation-metrics-grid">
                        <div>
                            <span>Total Cost</span>
                            <strong>
                                {status === "success" && recommendation
                                    ? formatUsd(recommendation.expected_total_cost)
                                    : displayedValue(undefined)}
                            </strong>
                        </div>

                        <div>
                            <span>Turnaround</span>
                            <strong>
                                {status === "success" && recommendation
                                    ? formatHours(recommendation.estimated_turnaround_hours)
                                    : displayedValue(undefined)}
                            </strong>
                        </div>

                        <div>
                            <span>Confidence</span>
                            <strong>{displayedValue(recommendation?.confidence)}</strong>
                        </div>

                        <div>
                            <span>Risk Level</span>
                            <strong>{displayedValue(recommendation?.risk_level)}</strong>
                        </div>
                    </div>
                </section>

                {/* Rationale */}
                <section className="recommendation-rationale-card">
                    <div className="recommendation-section-header">
                        <div className="recommendation-rationale-title">
                            <Info size={18} />

                            <div>
                                <h2>Recommendation Rationale</h2>

                                <p>
                                    Backend-generated explanation for the
                                    recommendation.
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className={`recommendation-empty-state ${status === "success" ? "recommendation-rationale-ready" : ""}`} aria-live="polite">
                        {status === "error" && <div className="recommendation-empty-icon"><AlertTriangle size={24} /></div>}

                        {status === "success" && recommendation ? (
                            <>
                                <h3>Backend rationale</h3>
                                <p className="recommendation-rationale-text">{recommendation.rationale}</p>
                            </>
                        ) : (
                            <>
                                <h3>Recommendation unavailable</h3>
                                <p role="alert">{errorMessage}</p>
                                <Link to={hasValidCargoRequestId ? "/decision-overview" : "/cargo-request"}>
                                    {hasValidCargoRequestId ? "Open Decision Overview" : "Go to Cargo Request"}
                                </Link>
                            </>
                        )}
                    </div>
                </section>

                {/* Assumptions */}
                <section className="recommendation-information-grid">
                    <div className="recommendation-information-card">
                        <div className="recommendation-information-title">
                            <Info size={18} />
                            <h2>Assumptions</h2>
                        </div>

                        <ul className="recommendation-assumptions-list">
                            {status === "success" && recommendation
                                ? formatAssumptions(recommendation.assumptions).map((assumption, index) => <li key={`${index}-${assumption}`}>{assumption}</li>)
                                : <li>No assumptions are available.</li>}
                        </ul>
                    </div>

                    <div className="recommendation-information-card recommendation-data-status">
                        <div className="recommendation-information-title">
                            <AlertTriangle size={18} />
                            <h2>Data Status</h2>
                        </div>

                        <div className="recommendation-info-row">
                            <span>Decision status</span>
                            <strong>
                                {status === "success" ? "Complete" : "Unavailable"}
                            </strong>
                        </div>

                        <div className="recommendation-info-row">
                            <span>Last updated</span>
                            <strong>
                                {status === "success" && recommendation
                                    ? formatTimestamp(recommendation.created_at)
                                    : "--"}
                            </strong>
                        </div>

                        {status === "success" && recommendation && (
                            <>
                                <div className="recommendation-info-row">
                                    <span>Recommendation ID</span>
                                    <strong title={recommendation.recommendation_id}>{recommendation.recommendation_id}</strong>
                                </div>
                                <div className="recommendation-info-row">
                                    <span>Forecast Run ID</span>
                                    <strong title={recommendation.forecast_run_id}>{recommendation.forecast_run_id}</strong>
                                </div>
                            </>
                        )}
                    </div>
                </section>
            </main>
        </div>
    );
}

export default Recommendation;
