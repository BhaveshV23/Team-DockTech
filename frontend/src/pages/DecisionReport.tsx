import {
    AlertTriangle,
    ArrowLeft,
    BarChart3,
    CheckCircle2,
    Download,
    FileText,
    Info,
    Ship,
    TrendingUp,
} from "lucide-react";
import { Link } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import { useCargoRequest } from "../hooks/useCargoRequest";
import "./DecisionReport.css";

function DecisionReport() {
    const cargoRequest = useCargoRequest();

    return (
        <div className="decision-report-page">
            <Sidebar activePage="decision-report" />

            <main className="decision-report-main">
                {/* Back navigation */}
                <Link
                    to="/decision-overview"
                    className="report-back-link"
                >
                    <ArrowLeft size={16} />
                    Back to Decision Overview
                </Link>

                {/* Header */}
                <header className="report-page-header">
                    <div>
                        <span className="report-eyebrow">
                            DECISION REPORT
                        </span>

                        <h1>Procurement Decision Report</h1>

                        <p>
                            Consolidated view of the cargo request, forecast,
                            vessel feasibility, cost, risk, and recommendation.
                        </p>
                    </div>

                    <button
                        type="button"
                        className="report-download-button"
                    >
                        <Download size={16} />
                        Generate Report
                    </button>
                </header>

                {/* Report status */}
                <section className="report-status-card">
                    <div className="report-status-icon">
                        <FileText size={21} />
                    </div>

                    <div>
                        <span>Report Status</span>
                        <strong>Awaiting decision data</strong>
                        <p>
                            The report will be populated once the backend
                            decision pipeline returns the required results.
                        </p>
                    </div>
                </section>

                {/* Cargo Summary */}
                <section className="report-section">
                    <div className="report-section-header">
                        <div>
                            <h2>Cargo Request Summary</h2>
                            <p>
                                Input parameters used for the procurement
                                decision.
                            </p>
                        </div>
                    </div>

                    <div className="report-summary-grid">
                        <div>
                            <span>Commodity</span>
                            <strong>
                                {cargoRequest
                                    ? cargoRequest.commodity.replace(/_/g, " ")
                                    : "--"}
                            </strong>
                        </div>

                        <div>
                            <span>Cargo Volume</span>
                            <strong>
                                {cargoRequest
                                    ? `${cargoRequest.cargoVolume} MT`
                                    : "--"}
                            </strong>
                        </div>

                        <div>
                            <span>Origin Port</span>
                            <strong>
                                {cargoRequest
                                    ? cargoRequest.originPort
                                    : "--"}
                            </strong>
                        </div>

                        <div>
                            <span>Destination Port</span>
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

                        <div>
                            <span>Contract Horizon</span>
                            <strong>
                                {cargoRequest
                                    ? cargoRequest.contractHorizon.replace(
                                        /_/g,
                                        " "
                                    )
                                    : "--"}
                            </strong>
                        </div>
                    </div>
                </section>

                {/* Decision Summary */}
                <section className="report-section">
                    <div className="report-section-header">
                        <div>
                            <h2>Decision Summary</h2>
                            <p>
                                Key outputs from the DockTech decision
                                workflow.
                            </p>
                        </div>
                    </div>

                    <div className="report-output-grid">
                        <div className="report-output-card">
                            <div className="report-output-icon">
                                <TrendingUp size={18} />
                            </div>

                            <span>Freight Forecast</span>
                            <strong>--</strong>
                            <small>Awaiting backend result</small>
                        </div>

                        <div className="report-output-card">
                            <div className="report-output-icon">
                                <Ship size={18} />
                            </div>

                            <span>Vessel Feasibility</span>
                            <strong>--</strong>
                            <small>Awaiting backend result</small>
                        </div>

                        <div className="report-output-card">
                            <div className="report-output-icon">
                                <BarChart3 size={18} />
                            </div>

                            <span>Total Cost</span>
                            <strong>--</strong>
                            <small>Awaiting backend result</small>
                        </div>

                        <div className="report-output-card">
                            <div className="report-output-icon">
                                <AlertTriangle size={18} />
                            </div>

                            <span>Risk</span>
                            <strong>--</strong>
                            <small>Awaiting backend result</small>
                        </div>
                    </div>
                </section>

                {/* Recommendation */}
                <section className="report-recommendation-card">
                    <div className="report-recommendation-header">
                        <div className="report-recommendation-icon">
                            <CheckCircle2 size={20} />
                        </div>

                        <div>
                            <h2>Final Recommendation</h2>
                            <p>
                                Backend decision-engine output.
                            </p>
                        </div>

                        <span className="report-confidence">
                            Confidence: --
                        </span>
                    </div>

                    <div className="report-recommendation-content">
                        <strong>--</strong>

                        <p>
                            No recommendation is available yet. The final
                            recommendation and its rationale will appear here
                            after backend processing.
                        </p>
                    </div>
                </section>

                {/* Assumptions */}
                <section className="report-information-grid">
                    <div className="report-information-card">
                        <div className="report-information-title">
                            <Info size={18} />
                            <h2>Assumptions</h2>
                        </div>

                        <p>
                            Backend-provided assumptions, data limitations,
                            methodology notes, and warnings will be included
                            in the final report.
                        </p>
                    </div>

                    <div className="report-information-card">
                        <div className="report-information-title">
                            <Info size={18} />
                            <h2>Data Status</h2>
                        </div>

                        <div className="report-info-row">
                            <span>Report data</span>
                            <strong>Awaiting data</strong>
                        </div>

                        <div className="report-info-row">
                            <span>Last updated</span>
                            <strong>--</strong>
                        </div>
                    </div>
                </section>
            </main>
        </div>
    );
}

export default DecisionReport;