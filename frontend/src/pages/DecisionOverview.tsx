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
import "./DecisionOverview.css";

function DecisionOverview() {
    const cargoRequest = useCargoRequest();

    return (
        <div className="decision-overview-page">
            {/* Sidebar */}
            <Sidebar activePage="decision-overview" />

            {/* Main */}
            <main className="decision-main">
                <header className="decision-header">
                    <div>
                        <p className="decision-eyebrow">
                            Decision Support
                        </p>

                        <h1>Decision Overview</h1>

                        <p className="decision-subtitle">
                            Review freight, vessel, cost and risk information
                            for the current cargo request.
                        </p>
                    </div>

                    <Link
                        to="/cargo-request"
                        className="decision-new-request"
                    >
                        New Cargo Request
                    </Link>
                </header>

                {/* Current Request */}
                <section className="decision-request-card">
                    <div className="decision-request-heading">
                        <div>
                            <span>ACTIVE CARGO REQUEST</span>

                            <h2>
                                {cargoRequest
                                    ? cargoRequest.commodity.replace(/_/g, " ")
                                    : "No active request"}
                            </h2>
                        </div>

                        <Link to="/cargo-request">
                            {cargoRequest ? "New Request" : "Create Request"}
                        </Link>
                    </div>

                    <div className="decision-request-grid">
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

                {/* Summary */}
                <section className="decision-summary-grid">
                    <div className="decision-summary-card">
                        <div className="decision-summary-icon">
                            <TrendingUp size={19} />
                        </div>

                        <span>Freight Forecast</span>
                        <strong>--</strong>
                        <small>Awaiting backend result</small>
                    </div>

                    <div className="decision-summary-card">
                        <div className="decision-summary-icon">
                            <Ship size={19} />
                        </div>

                        <span>Feasible Vessels</span>
                        <strong>--</strong>
                        <small>Awaiting feasibility result</small>
                    </div>

                    <div className="decision-summary-card">
                        <div className="decision-summary-icon">
                            <BarChart3 size={19} />
                        </div>

                        <span>Estimated Cost</span>
                        <strong>--</strong>
                        <small>Awaiting cost result</small>
                    </div>

                    <div className="decision-summary-card">
                        <div className="decision-summary-icon">
                            <AlertTriangle size={19} />
                        </div>

                        <span>Risk Status</span>
                        <strong>--</strong>
                        <small>Awaiting scenario result</small>
                    </div>
                </section>

                {/* Forecast */}
                <section
                    id="forecast"
                    className="decision-content-grid"
                >
                    <div className="decision-panel forecast-panel">
                        <div className="decision-panel-header">
                            <div>
                                <span>FREIGHT FORECAST</span>
                                <h2>Forecast Overview</h2>
                            </div>

                            <TrendingUp size={19} />
                        </div>

                        <div className="decision-empty-state">
                            <TrendingUp size={34} />

                            <h3>No forecast available</h3>

                            <p>
                                Freight forecast data will appear here after
                                the backend processes a cargo request.
                            </p>
                        </div>
                    </div>

                    {/* Recommendation */}
                    <div className="decision-panel recommendation-panel">
                        <div className="decision-panel-header">
                            <div>
                                <span>RECOMMENDATION</span>
                                <h2>Decision Status</h2>
                            </div>

                            <CheckCircle2 size={19} />
                        </div>

                        <div className="decision-empty-state">
                            <CheckCircle2 size={34} />

                            <h3>Awaiting recommendation</h3>

                            <p>
                                The recommendation will be displayed here
                                once the backend decision engine returns a
                                result.
                            </p>
                        </div>
                    </div>
                </section>

                {/* Vessel + Risk */}
                <section
                    id="vessels"
                    className="decision-content-grid"
                >
                    <div className="decision-panel">
                        <div className="decision-panel-header">
                            <div>
                                <span>VESSEL OPTIONS</span>
                                <h2>Feasibility Overview</h2>
                            </div>

                            <Ship size={19} />
                        </div>

                        <div className="decision-empty-state compact">
                            <Ship size={30} />

                            <h3>No vessel results</h3>

                            <p>
                                Vessel feasibility results will appear after
                                backend processing.
                            </p>
                        </div>
                    </div>

                    <div
                        id="risk"
                        className="decision-panel"
                    >
                        <div className="decision-panel-header">
                            <div>
                                <span>SCENARIOS & RISK</span>
                                <h2>Risk Overview</h2>
                            </div>

                            <AlertTriangle size={19} />
                        </div>

                        <div className="decision-scenarios">
                            <div>
                                <span>BASELINE</span>
                                <strong>--</strong>
                            </div>

                            <div>
                                <span>ADVERSE</span>
                                <strong>--</strong>
                            </div>

                            <div>
                                <span>FAVORABLE</span>
                                <strong>--</strong>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Assumptions */}
                <section className="decision-panel assumptions-panel">
                    <div className="decision-panel-header">
                        <div>
                            <span>DATA INFORMATION</span>
                            <h2>Assumptions & Data Status</h2>
                        </div>
                    </div>

                    <div className="decision-assumptions-empty">
                        <p>
                            Backend-provided assumptions, data freshness,
                            warnings and limitations will appear here.
                        </p>
                    </div>
                </section>
            </main>
        </div>
    );
}

export default DecisionOverview;