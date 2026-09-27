import {
    AlertTriangle,
    ArrowRight,
    BarChart3,
    CheckCircle2,
    Ship,
    TrendingUp,
} from "lucide-react";
import { Link } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import { useCargoRequest } from "../hooks/useCargoRequest";
import "./Dashboard.css";

function Dashboard() {
    const cargoRequest = useCargoRequest();

    return (
        <div className="dashboard-page">
            <Sidebar activePage="dashboard" />

            <main className="dashboard-main">
                {/* Header */}
                <header className="dashboard-header">
                    <div>
                        <span className="dashboard-eyebrow">
                            DECISION SUPPORT
                        </span>

                        <h1>Freight Intelligence Dashboard</h1>

                        <p>
                            Analyze cargo requirements, freight forecasts,
                            vessel feasibility, costs, and risk in one place.
                        </p>
                    </div>

                    <Link
                        to="/cargo-request"
                        className="dashboard-primary-button"
                    >
                        New Cargo Request
                        <ArrowRight size={17} />
                    </Link>
                </header>

                {/* Decision Flow */}
                <section className="dashboard-section">
                    <div className="dashboard-section-heading">
                        <div>
                            <h2>Decision Workflow</h2>
                            <p>
                                Follow the procurement decision from cargo
                                input to recommendation.
                            </p>
                        </div>
                    </div>

                    <div className="dashboard-workflow">
                        <Link
                            to="/cargo-request"
                            className="workflow-card workflow-active"
                        >
                            <div className="workflow-icon">
                                <Ship size={20} />
                            </div>

                            <div>
                                <span>01</span>
                                <h3>Cargo Request</h3>
                                <p>Define cargo requirements</p>
                            </div>
                        </Link>

                        <div className="workflow-arrow">
                            <ArrowRight size={18} />
                        </div>

                        <div className="workflow-card">
                            <div className="workflow-icon">
                                <CheckCircle2 size={20} />
                            </div>

                            <div>
                                <span>02</span>
                                <h3>Feasibility</h3>
                                <p>Evaluate vessel feasibility</p>
                            </div>
                        </div>

                        <div className="workflow-arrow">
                            <ArrowRight size={18} />
                        </div>

                        <div className="workflow-card">
                            <div className="workflow-icon">
                                <TrendingUp size={20} />
                            </div>

                            <div>
                                <span>03</span>
                                <h3>Forecast</h3>
                                <p>Review freight outlook</p>
                            </div>
                        </div>

                        <div className="workflow-arrow">
                            <ArrowRight size={18} />
                        </div>

                        <Link
                            to="/decision-overview"
                            className="workflow-card"
                        >
                            <div className="workflow-icon">
                                <BarChart3 size={20} />
                            </div>

                            <div>
                                <span>04</span>
                                <h3>Decision</h3>
                                <p>Compare cost and risk</p>
                            </div>
                        </Link>
                    </div>
                </section>

                {/* Summary Cards */}
                <section className="dashboard-section">
                    <div className="dashboard-section-heading">
                        <div>
                            <h2>Current Decision Status</h2>
                            <p>
                                Results will appear here after a cargo request
                                is processed.
                            </p>
                        </div>
                    </div>

                    <div className="dashboard-summary-grid">
                        <div className="dashboard-summary-card">
                            <div className="summary-card-top">
                                <div className="summary-card-icon">
                                    <TrendingUp size={19} />
                                </div>

                                <span className="summary-status">
                                    Awaiting data
                                </span>
                            </div>

                            <span className="summary-label">
                                Freight Forecast
                            </span>

                            <strong>--</strong>

                            <p>
                                Backend forecast will appear after processing.
                            </p>
                        </div>

                        <div className="dashboard-summary-card">
                            <div className="summary-card-top">
                                <div className="summary-card-icon">
                                    <Ship size={19} />
                                </div>

                                <span className="summary-status">
                                    Awaiting data
                                </span>
                            </div>

                            <span className="summary-label">
                                Vessel Options
                            </span>

                            <strong>--</strong>

                            <p>
                                Feasible vessels will appear after analysis.
                            </p>
                        </div>

                        <div className="dashboard-summary-card">
                            <div className="summary-card-top">
                                <div className="summary-card-icon">
                                    <BarChart3 size={19} />
                                </div>

                                <span className="summary-status">
                                    Awaiting data
                                </span>
                            </div>

                            <span className="summary-label">
                                Estimated Cost
                            </span>

                            <strong>--</strong>

                            <p>
                                Backend-calculated cost will appear here.
                            </p>
                        </div>

                        <div className="dashboard-summary-card">
                            <div className="summary-card-top">
                                <div className="summary-card-icon">
                                    <AlertTriangle size={19} />
                                </div>

                                <span className="summary-status">
                                    Awaiting data
                                </span>
                            </div>

                            <span className="summary-label">
                                Risk Assessment
                            </span>

                            <strong>--</strong>

                            <p>
                                Scenario and risk results will appear here.
                            </p>
                        </div>
                    </div>
                </section>

                {/* Empty State */}
                <section className="dashboard-empty-state">
                    <div className="dashboard-empty-icon">
                        <Ship size={25} />
                    </div>

                    {cargoRequest ? (
                        <>
                            <h2>Active Cargo Request</h2>

                            <p>
                                {cargoRequest.commodity.replace(/_/g, " ")} ·{" "}
                                {cargoRequest.cargoVolume} MT ·{" "}
                                {cargoRequest.originPort} →{" "}
                                {cargoRequest.destinationPort}
                            </p>

                            <Link
                                to="/decision-overview"
                                className="dashboard-secondary-button"
                            >
                                View Decision Overview
                                <ArrowRight size={16} />
                            </Link>
                        </>
                    ) : (
                        <>
                            <h2>No active cargo decision</h2>

                            <p>
                                Start by entering a cargo requirement. DockTech
                                will use the backend decision pipeline to
                                generate feasibility, forecast, vessel, cost,
                                scenario, and recommendation results.
                            </p>

                            <Link
                                to="/cargo-request"
                                className="dashboard-secondary-button"
                            >
                                Create Cargo Request
                                <ArrowRight size={16} />
                            </Link>
                        </>
                    )}
                </section>
            </main>
        </div>
    );
}

export default Dashboard;