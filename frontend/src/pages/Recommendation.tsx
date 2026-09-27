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
import { useCargoRequest } from "../hooks/useCargoRequest";
import "./Recommendation.css";

function Recommendation() {
    const cargoRequest = useCargoRequest();

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
                        Awaiting data
                    </div>
                </header>

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
                                    ? `${cargoRequest.cargoVolume} MT`
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

                        <h2>--</h2>

                        <p>
                            The backend decision engine recommendation will
                            appear here after the cargo request is processed.
                        </p>
                    </div>

                    <span className="recommendation-confidence">
                        Confidence: --
                    </span>
                </section>

                {/* Strategy */}
                <section className="recommendation-strategy-grid">
                    <div className="recommendation-strategy-card">
                        <div className="recommendation-card-icon">
                            <Target size={19} />
                        </div>

                        <span>Market Entry</span>

                        <strong>--</strong>

                        <small>FIX_NOW / WAIT</small>
                    </div>

                    <div className="recommendation-strategy-card">
                        <div className="recommendation-card-icon">
                            <ShieldCheck size={19} />
                        </div>

                        <span>Contract Strategy</span>

                        <strong>--</strong>

                        <small>
                            SPOT / SHORT TERM / MULTIPLE VOYAGE
                        </small>
                    </div>

                    <div className="recommendation-strategy-card">
                        <div className="recommendation-card-icon">
                            <CheckCircle2 size={19} />
                        </div>

                        <span>Expected Freight</span>

                        <strong>--</strong>

                        <small>Backend-generated value</small>
                    </div>

                    <div className="recommendation-strategy-card">
                        <div className="recommendation-card-icon">
                            <AlertTriangle size={19} />
                        </div>

                        <span>Risk</span>

                        <strong>--</strong>

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
                            <strong>--</strong>
                        </div>

                        <div>
                            <span>Turnaround</span>
                            <strong>--</strong>
                        </div>

                        <div>
                            <span>Confidence</span>
                            <strong>--</strong>
                        </div>

                        <div>
                            <span>Risk Level</span>
                            <strong>--</strong>
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

                    <div className="recommendation-empty-state">
                        <div className="recommendation-empty-icon">
                            <Info size={24} />
                        </div>

                        <h3>No recommendation available</h3>

                        <p>
                            Once the decision engine processes the cargo
                            request, its rationale, supporting factors,
                            assumptions, and limitations will be displayed
                            here.
                        </p>
                    </div>
                </section>

                {/* Assumptions */}
                <section className="recommendation-information-grid">
                    <div className="recommendation-information-card">
                        <div className="recommendation-information-title">
                            <Info size={18} />
                            <h2>Assumptions</h2>
                        </div>

                        <p>
                            Backend-provided assumptions and decision
                            limitations will appear here.
                        </p>
                    </div>

                    <div className="recommendation-information-card">
                        <div className="recommendation-information-title">
                            <AlertTriangle size={18} />
                            <h2>Data Status</h2>
                        </div>

                        <div className="recommendation-info-row">
                            <span>Decision status</span>
                            <strong>Awaiting data</strong>
                        </div>

                        <div className="recommendation-info-row">
                            <span>Last updated</span>
                            <strong>--</strong>
                        </div>
                    </div>
                </section>
            </main>
        </div>
    );
}

export default Recommendation;