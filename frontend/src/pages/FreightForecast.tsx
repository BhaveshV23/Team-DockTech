import { useState } from "react";
import {
    ArrowLeft,
    BarChart3,
    CalendarDays,
    Info,
    RefreshCw,
    TrendingUp,
} from "lucide-react";
import { Link } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import { useCargoRequest } from "../hooks/useCargoRequest";
import "./FreightForecast.css";

function FreightForecast() {
    const [forecastHorizon, setForecastHorizon] = useState<7 | 30 | 90>(7);
    const cargoRequest = useCargoRequest();

    return (
        <div className="freight-forecast-page">
            <Sidebar activePage="freight-forecast" />

            <main className="freight-forecast-main">
                {/* Back navigation */}
                <Link
                    to="/decision-overview"
                    className="forecast-back-link"
                >
                    <ArrowLeft size={16} />
                    Back to Decision Overview
                </Link>

                {/* Page Header */}
                <header className="forecast-page-header">
                    <div>
                        <span className="forecast-eyebrow">
                            FREIGHT INTELLIGENCE
                        </span>

                        <h1>Freight Forecast</h1>

                        <p>
                            Review the backend-generated freight outlook for
                            the selected cargo requirement.
                        </p>
                    </div>

                    <div className="forecast-status">
                        <span className="forecast-status-dot"></span>
                        Awaiting data
                    </div>
                </header>

                {/* Cargo Request Context */}
                <section className="forecast-request-card">
                    <div>
                        <span className="forecast-request-label">
                            CURRENT CARGO REQUEST
                        </span>

                        <h2>
                            {cargoRequest
                                ? cargoRequest.commodity.replace(/_/g, " ")
                                : "No active request"}
                        </h2>
                    </div>

                    <div className="forecast-request-details">
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

                {/* Forecast Controls */}
                <section className="forecast-controls-card">
                    <div className="forecast-control-heading">
                        <div className="forecast-control-icon">
                            <CalendarDays size={18} />
                        </div>

                        <div>
                            <h2>Forecast Horizon</h2>
                            <p>
                                Select the period for which the forecast should
                                be displayed.
                            </p>
                        </div>
                    </div>

                    <div className="forecast-horizon-options">
                        <button
                            type="button"
                            className={`forecast-horizon-button ${forecastHorizon === 7 ? "active" : ""
                                }`}
                            onClick={() => setForecastHorizon(7)}
                        >
                            7 Days
                        </button>

                        <button
                            type="button"
                            className={`forecast-horizon-button ${forecastHorizon === 30 ? "active" : ""
                                }`}
                            onClick={() => setForecastHorizon(30)}
                        >
                            30 Days
                        </button>

                        <button
                            type="button"
                            className={`forecast-horizon-button ${forecastHorizon === 90 ? "active" : ""
                                }`}
                            onClick={() => setForecastHorizon(90)}
                        >
                            90 Days
                        </button>
                    </div>
                </section>

                {/* Forecast Chart */}
                <section className="forecast-chart-card">
                    <div className="forecast-card-header">
                        <div>
                            <h2>Freight Rate Outlook</h2>
                            <p>
                                Historical trend and backend-generated forecast
                                for the{" "}
                                <strong>{forecastHorizon}-day horizon</strong>{" "}
                                will appear here.
                            </p>
                        </div>

                        <div className="forecast-unit-label">
                            Freight Rate
                        </div>
                    </div>

                    <div className="forecast-empty-chart">
                        <div className="forecast-chart-icon">
                            <TrendingUp size={25} />
                        </div>

                        <h3>Forecast data unavailable</h3>

                        <p>
                            No forecast result has been received from the
                            backend yet. Once available, this area will display
                            historical values and lower, base, and upper
                            forecast bands.
                        </p>

                        <div className="forecast-chart-legend">
                            <span>
                                <i className="legend-dot historical"></i>
                                Historical
                            </span>

                            <span>
                                <i className="legend-dot forecast"></i>
                                Forecast
                            </span>

                            <span>
                                <i className="legend-dot range"></i>
                                Forecast Range
                            </span>
                        </div>
                    </div>
                </section>

                {/* Forecast Summary */}
                <section className="forecast-summary-grid">
                    <div className="forecast-summary-card">
                        <div className="forecast-summary-icon">
                            <TrendingUp size={18} />
                        </div>

                        <span>Base Forecast</span>
                        <strong>--</strong>
                        <small>Awaiting backend result</small>
                    </div>

                    <div className="forecast-summary-card">
                        <div className="forecast-summary-icon">
                            <BarChart3 size={18} />
                        </div>

                        <span>Lower Forecast</span>
                        <strong>--</strong>
                        <small>Awaiting backend result</small>
                    </div>

                    <div className="forecast-summary-card">
                        <div className="forecast-summary-icon">
                            <BarChart3 size={18} />
                        </div>

                        <span>Upper Forecast</span>
                        <strong>--</strong>
                        <small>Awaiting backend result</small>
                    </div>
                </section>

                {/* Information */}
                <section className="forecast-information-grid">
                    <div className="forecast-information-card">
                        <div className="forecast-information-header">
                            <Info size={18} />
                            <h2>Forecast Information</h2>
                        </div>

                        <div className="forecast-info-row">
                            <span>Data freshness</span>
                            <strong>--</strong>
                        </div>

                        <div className="forecast-info-row">
                            <span>Model status</span>
                            <strong>Awaiting data</strong>
                        </div>

                        <div className="forecast-info-row">
                            <span>Last updated</span>
                            <strong>--</strong>
                        </div>
                    </div>

                    <div className="forecast-information-card">
                        <div className="forecast-information-header">
                            <RefreshCw size={18} />
                            <h2>Assumptions</h2>
                        </div>

                        <p className="forecast-assumption-text">
                            Backend-provided assumptions, data limitations,
                            warnings, and forecast methodology notes will be
                            displayed here.
                        </p>
                    </div>
                </section>
            </main>
        </div>
    );
}

export default FreightForecast;