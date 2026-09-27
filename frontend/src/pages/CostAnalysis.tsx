import { useCargoRequest } from "../hooks/useCargoRequest";
import {
    AlertCircle,
    ArrowLeft,
    BarChart3,
    Calculator,
    Info,
} from "lucide-react";
import { Link } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import "./CostAnalysis.css";

function CostAnalysis() {
    const cargoRequest = useCargoRequest();

    return (
        <div className="cost-analysis-page">
            <Sidebar activePage="cost-analysis" />

            <main className="cost-analysis-main">
                {/* Back navigation */}
                <Link
                    to="/decision-overview"
                    className="cost-back-link"
                >
                    <ArrowLeft size={16} />
                    Back to Decision Overview
                </Link>

                {/* Header */}
                <header className="cost-page-header">
                    <div>
                        <span className="cost-eyebrow">
                            COST ANALYSIS
                        </span>

                        <h1>Cost Comparison</h1>

                        <p>
                            Review backend-calculated cost estimates and compare
                            available procurement options.
                        </p>
                    </div>

                    <div className="cost-status">
                        <span className="cost-status-dot"></span>
                        Awaiting data
                    </div>
                </header>

                {/* Cargo Request Context */}
                <section className="cost-request-card">
                    <div>
                        <span className="cost-request-label">
                            CURRENT CARGO REQUEST
                        </span>

                        <h2>
                            {cargoRequest
                                ? cargoRequest.commodity.replace(/_/g, " ")
                                : "No active request"}
                        </h2>
                    </div>

                    <div className="cost-request-details">
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

                {/* Total Cost */}
                <section className="cost-total-card">
                    <div className="cost-total-icon">
                        <Calculator size={21} />
                    </div>

                    <div>
                        <span>Total Estimated Cost</span>
                        <strong>--</strong>
                        <p>
                            Backend-calculated total cost will appear after
                            processing.
                        </p>
                    </div>
                </section>

                {/* Cost Components */}
                <section className="cost-section">
                    <div className="cost-section-heading">
                        <div>
                            <h2>Cost Components</h2>
                            <p>
                                Cost components will be populated from the
                                backend decision engine.
                            </p>
                        </div>
                    </div>

                    <div className="cost-component-grid">
                        <div className="cost-component-card">
                            <div className="cost-component-icon">
                                <BarChart3 size={18} />
                            </div>

                            <span>Freight Cost</span>
                            <strong>--</strong>
                            <small>Awaiting backend result</small>
                        </div>

                        <div className="cost-component-card">
                            <div className="cost-component-icon">
                                <Calculator size={18} />
                            </div>

                            <span>Fuel / Operational Cost</span>
                            <strong>--</strong>
                            <small>Awaiting backend result</small>
                        </div>

                        <div className="cost-component-card">
                            <div className="cost-component-icon">
                                <BarChart3 size={18} />
                            </div>

                            <span>Additional Costs</span>
                            <strong>--</strong>
                            <small>Awaiting backend result</small>
                        </div>
                    </div>
                </section>

                {/* Comparison */}
                <section className="cost-comparison-card">
                    <div className="cost-card-header">
                        <div>
                            <h2>Procurement Option Comparison</h2>
                            <p>
                                Backend-generated cost values for available
                                procurement options will appear here.
                            </p>
                        </div>

                        <span className="cost-option-count">
                            0 options
                        </span>
                    </div>

                    <div className="cost-table-wrapper">
                        <table className="cost-comparison-table">
                            <thead>
                                <tr>
                                    <th>Procurement Option</th>
                                    <th>Expected Freight Cost</th>
                                    <th>Expected Total Cost</th>
                                    <th>Freight Unit</th>
                                    <th>Turnaround</th>
                                </tr>
                            </thead>

                            <tbody>
                                {/* Backend cost results will be rendered here. */}
                            </tbody>
                        </table>
                    </div>

                    <div className="cost-empty-state">
                        <div className="cost-empty-icon">
                            <BarChart3 size={25} />
                        </div>

                        <h3>No cost comparison available</h3>

                        <p>
                            Submit a cargo request and wait for the backend
                            decision pipeline to return cost results.
                        </p>
                    </div>
                </section>

                {/* Information */}
                <section className="cost-information-grid">
                    <div className="cost-information-card">
                        <div className="cost-information-title">
                            <Info size={18} />
                            <h2>Cost Assumptions</h2>
                        </div>

                        <p>
                            Backend-provided assumptions, units, data
                            freshness, and calculation notes will be displayed
                            here.
                        </p>
                    </div>

                    <div className="cost-information-card">
                        <div className="cost-information-title">
                            <AlertCircle size={18} />
                            <h2>Data Status</h2>
                        </div>

                        <div className="cost-info-row">
                            <span>Calculation status</span>
                            <strong>Awaiting data</strong>
                        </div>

                        <div className="cost-info-row">
                            <span>Last updated</span>
                            <strong>--</strong>
                        </div>
                    </div>
                </section>
            </main>
        </div>
    );
}

export default CostAnalysis;