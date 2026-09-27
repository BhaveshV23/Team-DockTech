import {
    AlertTriangle,
    ArrowLeft,
    CheckCircle2,
    Info,
    TrendingDown,
    TrendingUp,
} from "lucide-react";
import { Link } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import { useCargoRequest } from "../hooks/useCargoRequest";
import "./ScenariosRisk.css";

function ScenariosRisk() {
    const cargoRequest = useCargoRequest();

    return (
        <div className="scenarios-risk-page">
            <Sidebar activePage="scenarios-risk" />

            <main className="scenarios-risk-main">
                {/* Back navigation */}
                <Link
                    to="/decision-overview"
                    className="scenarios-back-link"
                >
                    <ArrowLeft size={16} />
                    Back to Decision Overview
                </Link>

                {/* Header */}
                <header className="scenarios-page-header">
                    <div>
                        <span className="scenarios-eyebrow">
                            SCENARIO ANALYSIS
                        </span>

                        <h1>Scenarios & Risk</h1>

                        <p>
                            Review how different market and operational
                            scenarios may affect the procurement decision.
                        </p>
                    </div>

                    <div className="scenarios-status">
                        <span className="scenarios-status-dot"></span>
                        Awaiting data
                    </div>
                </header>

                {/* Cargo Request Context */}
                <section className="scenarios-request-card">
                    <div>
                        <span className="scenarios-request-label">
                            CURRENT CARGO REQUEST
                        </span>

                        <h2>
                            {cargoRequest
                                ? cargoRequest.commodity.replace(/_/g, " ")
                                : "No active request"}
                        </h2>
                    </div>

                    <div className="scenarios-request-details">
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

                {/* Scenario cards */}
                <section className="scenarios-section">
                    <div className="scenarios-section-heading">
                        <div>
                            <h2>Scenario Comparison</h2>

                            <p>
                                Scenario impacts and costs are calculated by
                                the backend decision engine.
                            </p>
                        </div>
                    </div>

                    <div className="scenario-grid">
                        {/* Baseline */}
                        <div className="scenario-card baseline">
                            <div className="scenario-card-header">
                                <div className="scenario-icon">
                                    <CheckCircle2 size={19} />
                                </div>

                                <span className="scenario-label">
                                    BASELINE
                                </span>
                            </div>

                            <h3>Baseline Scenario</h3>

                            <p>
                                Expected market and operational conditions.
                            </p>

                            <div className="scenario-metrics">
                                <div>
                                    <span>Freight Impact</span>
                                    <strong>--</strong>
                                </div>

                                <div>
                                    <span>Fuel Impact</span>
                                    <strong>--</strong>
                                </div>

                                <div>
                                    <span>Delay</span>
                                    <strong>--</strong>
                                </div>

                                <div>
                                    <span>Scenario Cost</span>
                                    <strong>--</strong>
                                </div>
                            </div>
                        </div>

                        {/* Adverse */}
                        <div className="scenario-card adverse">
                            <div className="scenario-card-header">
                                <div className="scenario-icon">
                                    <TrendingUp size={19} />
                                </div>

                                <span className="scenario-label">
                                    ADVERSE
                                </span>
                            </div>

                            <h3>Adverse Scenario</h3>

                            <p>
                                Higher disruption, congestion, or market
                                pressure.
                            </p>

                            <div className="scenario-metrics">
                                <div>
                                    <span>Freight Impact</span>
                                    <strong>--</strong>
                                </div>

                                <div>
                                    <span>Fuel Impact</span>
                                    <strong>--</strong>
                                </div>

                                <div>
                                    <span>Delay</span>
                                    <strong>--</strong>
                                </div>

                                <div>
                                    <span>Scenario Cost</span>
                                    <strong>--</strong>
                                </div>
                            </div>
                        </div>

                        {/* Favorable */}
                        <div className="scenario-card favorable">
                            <div className="scenario-card-header">
                                <div className="scenario-icon">
                                    <TrendingDown size={19} />
                                </div>

                                <span className="scenario-label">
                                    FAVORABLE
                                </span>
                            </div>

                            <h3>Favorable Scenario</h3>

                            <p>
                                Improved market and operational conditions.
                            </p>

                            <div className="scenario-metrics">
                                <div>
                                    <span>Freight Impact</span>
                                    <strong>--</strong>
                                </div>

                                <div>
                                    <span>Fuel Impact</span>
                                    <strong>--</strong>
                                </div>

                                <div>
                                    <span>Delay</span>
                                    <strong>--</strong>
                                </div>

                                <div>
                                    <span>Scenario Cost</span>
                                    <strong>--</strong>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Risk Overview */}
                <section className="risk-overview-card">
                    <div className="risk-overview-header">
                        <div className="risk-overview-title">
                            <AlertTriangle size={19} />

                            <div>
                                <h2>Risk Overview</h2>

                                <p>
                                    Backend-generated risk assessment will
                                    appear here.
                                </p>
                            </div>
                        </div>

                        <span className="risk-level">
                            Risk: --
                        </span>
                    </div>

                    <div className="risk-empty-state">
                        <div className="risk-empty-icon">
                            <AlertTriangle size={24} />
                        </div>

                        <h3>No risk assessment available</h3>

                        <p>
                            Risk indicators, scenario exposure, congestion
                            effects, delay impact, and other backend-generated
                            risk information will be displayed after the cargo
                            request is processed.
                        </p>
                    </div>
                </section>

                {/* Information */}
                <section className="scenarios-information-grid">
                    <div className="scenarios-information-card">
                        <div className="scenarios-information-title">
                            <Info size={18} />
                            <h2>Scenario Information</h2>
                        </div>

                        <p>
                            DockTech compares BASELINE, ADVERSE, and FAVORABLE
                            scenarios using backend-generated outputs. The
                            frontend only presents the returned values and
                            assumptions.
                        </p>
                    </div>

                    <div className="scenarios-information-card">
                        <div className="scenarios-information-title">
                            <AlertTriangle size={18} />
                            <h2>Assumptions & Warnings</h2>
                        </div>

                        <p>
                            Backend-provided assumptions, data limitations,
                            warnings, and scenario methodology notes will
                            appear here.
                        </p>
                    </div>
                </section>
            </main>
        </div>
    );
}

export default ScenariosRisk;