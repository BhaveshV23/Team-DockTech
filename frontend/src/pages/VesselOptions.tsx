import {
    AlertCircle,
    ArrowLeft,
    CheckCircle2,
    Ship,
} from "lucide-react";
import { Link } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import { useCargoRequest } from "../hooks/useCargoRequest";
import "./VesselOptions.css";

function VesselOptions() {
    const cargoRequest = useCargoRequest();

    return (
        <div className="vessel-options-page">
            <Sidebar activePage="vessel-options" />

            <main className="vessel-options-main">
                {/* Back navigation */}
                <Link
                    to="/decision-overview"
                    className="vessel-back-link"
                >
                    <ArrowLeft size={16} />
                    Back to Decision Overview
                </Link>

                {/* Header */}
                <header className="vessel-page-header">
                    <div>
                        <span className="vessel-eyebrow">
                            VESSEL FEASIBILITY
                        </span>

                        <h1>Vessel Options</h1>

                        <p>
                            Compare vessel options and review backend-generated
                            feasibility results for the cargo request.
                        </p>
                    </div>

                    <div className="vessel-status">
                        <span className="vessel-status-dot"></span>
                        Awaiting data
                    </div>
                </header>

                {/* Request Summary */}
                <section className="vessel-request-card">
                    <div className="vessel-request-icon">
                        <Ship size={19} />
                    </div>

                    <div>
                        <span>Active Cargo Request</span>

                        <strong>
                            {cargoRequest
                                ? cargoRequest.commodity.replace(/_/g, " ")
                                : "No cargo request loaded"}
                        </strong>

                        <p>
                            {cargoRequest
                                ? `${cargoRequest.cargoVolume} MT · ${cargoRequest.originPort} → ${cargoRequest.destinationPort}`
                                : "Cargo and route details will appear here after a request is processed."}
                        </p>
                    </div>
                </section>

                {/* Vessel Comparison */}
                <section className="vessel-table-card">
                    <div className="vessel-card-header">
                        <div>
                            <h2>Vessel Feasibility</h2>

                            <p>
                                Backend feasibility results will be displayed
                                for each vessel option.
                            </p>
                        </div>

                        <span className="vessel-count">
                            0 options
                        </span>
                    </div>

                    <div className="vessel-table-wrapper">
                        <table className="vessel-comparison-table">
                            <thead>
                                <tr>
                                    <th>Vessel Class</th>
                                    <th>Feasibility</th>
                                    <th>Reason</th>
                                    <th>Capacity</th>
                                    <th>Voyages</th>
                                    <th>Constraints</th>
                                    <th>Cost</th>
                                </tr>
                            </thead>

                            <tbody>
                                {/* Backend vessel results will be rendered here. */}
                            </tbody>
                        </table>
                    </div>

                    <div className="vessel-empty-state">
                        <div className="vessel-empty-icon">
                            <Ship size={25} />
                        </div>

                        <h3>No vessel options available</h3>

                        <p>
                            Submit a cargo request to receive vessel options,
                            feasibility status, capacity, voyages, constraints,
                            and related cost information.
                        </p>
                    </div>
                </section>

                {/* Feasibility Explanation */}
                <section className="vessel-info-grid">
                    <div className="vessel-info-card">
                        <div className="vessel-info-title">
                            <CheckCircle2 size={18} />
                            <h2>Feasibility Checks</h2>
                        </div>

                        <ul>
                            <li>
                                Vessel class and capacity compatibility
                            </li>
                            <li>
                                Port and route constraints
                            </li>
                            <li>
                                Cargo and delivery requirements
                            </li>
                            <li>
                                Voyage and operational constraints
                            </li>
                        </ul>
                    </div>

                    <div className="vessel-info-card">
                        <div className="vessel-info-title">
                            <AlertCircle size={18} />
                            <h2>Backend Decision Data</h2>
                        </div>

                        <p>
                            Feasibility status, rejection reasons, capacity,
                            voyage count, constraints, and cost values will be
                            supplied by the backend decision engine.
                        </p>
                    </div>
                </section>
            </main>
        </div>
    );
}

export default VesselOptions;