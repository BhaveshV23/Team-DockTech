import { useEffect, useRef, useState } from "react";
import { AlertCircle, ArrowLeft, CalendarDays, RefreshCw, Ship, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import { useCargoRequest } from "../hooks/useCargoRequest";
import { apiRequest } from "../services/api";
import type { CargoRequestResponse } from "../types/cargo";
import type { ForecastHorizon, ForecastRequest, ForecastRunResponse } from "../types/forecast";
import "./FreightForecast.css";

type RouteReference = {
    route_id: string;
    origin_port_id: string;
    destination_port_id: string;
    commodity: string;
};

type VesselReference = {
    vessel_class_id: string;
    vessel_class_name: string;
};

type ContextState =
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "empty"; message: string }
    | { status: "ready"; cargo: CargoRequestResponse; route: RouteReference; vessels: VesselReference[] };

type ForecastState =
    | { status: "idle" }
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "empty" }
    | { status: "ready"; forecast: ForecastRunResponse };

const HORIZONS: ForecastHorizon[] = [7, 30, 90];

function messageFor(error: unknown) {
    return error instanceof Error ? error.message : "Unable to load forecast data. Please try again.";
}

function formatFreightUnit(unit: string): string {
    return unit.replace("_PER_", " / ");
}

function ForecastChart({ points, unit }: { points: ForecastRunResponse["forecast_points"]; unit: string }) {
    if (points.length === 0) return null;

    const width = 900;
    const height = 310;
    const padding = { top: 18, right: 24, bottom: 48, left: 64 };
    const values = points.flatMap((point) => [point.lower_value, point.central_value, point.upper_value]);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const spread = max - min || Math.max(Math.abs(max) * 0.1, 1);
    const yMin = min - spread * 0.08;
    const yMax = max + spread * 0.08;
    const x = (index: number) => padding.left + (points.length === 1 ? (width - padding.left - padding.right) / 2 : index * (width - padding.left - padding.right) / (points.length - 1));
    const y = (value: number) => padding.top + (yMax - value) * (height - padding.top - padding.bottom) / (yMax - yMin);
    const line = (key: "central_value" | "lower_value" | "upper_value") => points.map((point, index) => `${index === 0 ? "M" : "L"} ${x(index)} ${y(point[key])}`).join(" ");
    const band = `${points.map((point, index) => `${index === 0 ? "M" : "L"} ${x(index)} ${y(point.upper_value)}`).join(" ")} ${points.slice().reverse().map((point, reverseIndex) => `L ${x(points.length - reverseIndex - 1)} ${y(point.lower_value)}`).join(" ")} Z`;
    const labelIndices = [...new Set([0, Math.floor((points.length - 1) / 2), points.length - 1])];

    return (
        <div className="forecast-chart-scroll">
            <svg className="forecast-data-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`Forecast central values and lower and upper range in ${unit}`}>
                <text x="8" y="16" className="forecast-axis-unit">{unit}</text>
                {[0, 1, 2, 3].map((tick) => {
                    const value = yMax - ((yMax - yMin) * tick) / 3;
                    const lineY = y(value);
                    return <g key={tick}><line x1={padding.left} x2={width - padding.right} y1={lineY} y2={lineY} className="forecast-gridline" /><text x={padding.left - 8} y={lineY + 4} textAnchor="end" className="forecast-axis-label">{value.toLocaleString(undefined, { maximumFractionDigits: 2 })}</text></g>;
                })}
                <path d={band} className="forecast-range-band" />
                <path d={line("upper_value")} className="forecast-bound-line" />
                <path d={line("lower_value")} className="forecast-bound-line" />
                <path d={line("central_value")} className="forecast-central-line" />
                {points.map((point, index) => <circle key={`${point.forecast_date}-${index}`} cx={x(index)} cy={y(point.central_value)} r="3" className="forecast-central-point"><title>{`${point.forecast_date}: ${point.central_value} ${formatFreightUnit(point.unit)}`}</title></circle>)}
                {labelIndices.map((index) => <text key={index} x={x(index)} y={height - 15} textAnchor="middle" className="forecast-axis-label">{points[index].forecast_date}</text>)}
            </svg>
        </div>
    );
}

function FreightForecast() {
    const storedCargo = useCargoRequest();
    const cargoRequestId = storedCargo?.cargo_request_id;
    const cargoUserId = storedCargo?.user_id;
    const [retryCount, setRetryCount] = useState(0);
    const [context, setContext] = useState<ContextState>(cargoRequestId && cargoUserId ? { status: "loading" } : { status: "empty", message: "Create a cargo request before generating its freight forecast." });
    const [contextCargoKey, setContextCargoKey] = useState<string | null>(
        cargoRequestId && cargoUserId ? `${cargoUserId}:${cargoRequestId}` : null,
    );
    const [horizon, setHorizon] = useState<ForecastHorizon>(7);
    const [vesselClassId, setVesselClassId] = useState("");
    const [forecastState, setForecastState] = useState<ForecastState>({ status: "idle" });
    const [forecastRetryCount, setForecastRetryCount] = useState(0);
    const forecastRequestRef = useRef<{
        key: string;
        promise: Promise<ForecastRunResponse>;
    } | null>(null);

    useEffect(() => {
        if (!cargoRequestId || !cargoUserId) {
            forecastRequestRef.current = null;
            return;
        }

        let active = true;
        forecastRequestRef.current = null;
        const loadContext = async () => {
            const [cargo, routes, vessels] = await Promise.all([
                apiRequest<CargoRequestResponse>(`/api/v1/cargo-requests/${encodeURIComponent(cargoRequestId)}`),
                apiRequest<RouteReference[]>("/api/v1/routes"),
                apiRequest<VesselReference[]>("/api/v1/vessels"),
            ]);
            if (cargo.cargo_request_id !== cargoRequestId || cargo.user_id !== cargoUserId) {
                throw new Error("The active cargo request could not be verified for this user.");
            }
            const matchingRoutes = routes.filter((route) =>
                route.origin_port_id === cargo.origin_port_id &&
                route.destination_port_id === cargo.destination_port_id &&
                route.commodity === cargo.commodity,
            );
            if (matchingRoutes.length === 0) return { status: "empty" as const, message: "No route matches this cargo's origin, destination, and commodity." };
            if (vessels.length === 0) return { status: "empty" as const, message: "No vessel classes are available from the backend." };
            return { status: "ready" as const, cargo, route: matchingRoutes[0], vessels };
        };
        void loadContext().then((loaded) => {
            if (!active) return;
            setContext(loaded);
            setContextCargoKey(`${cargoUserId}:${cargoRequestId}`);
            setVesselClassId(loaded.status === "ready" ? loaded.vessels[0].vessel_class_id : "");
            forecastRequestRef.current = null;
            setForecastState({ status: "idle" });
        }).catch((error: unknown) => {
            if (active) {
                setContext({ status: "error", message: messageFor(error) });
                setContextCargoKey(`${cargoUserId}:${cargoRequestId}`);
            }
        });
        return () => { active = false; };
    }, [cargoRequestId, cargoUserId, retryCount]);

    const retryContext = () => {
        setContext({ status: "loading" });
        setRetryCount((count) => count + 1);
    };

    useEffect(() => {
        if (
            !cargoRequestId ||
            !cargoUserId ||
            context.status !== "ready" ||
            context.cargo.cargo_request_id !== cargoRequestId ||
            context.cargo.user_id !== cargoUserId ||
            !vesselClassId
        ) return;

        let active = true;
        const request: ForecastRequest = {
            cargo_request_id: context.cargo.cargo_request_id,
            route_id: context.route.route_id,
            vessel_class_id: vesselClassId,
            freight_unit: "USD_PER_MT",
            horizon,
        };
        const key = JSON.stringify(request);
        let operation = forecastRequestRef.current;

        if (!operation || operation.key !== key) {
            setForecastState({ status: "loading" });
            const promise = apiRequest<ForecastRunResponse>("/api/v1/forecast", {
                method: "POST",
                body: JSON.stringify(request),
            }).then((forecast) => {
                if (
                    forecast.cargo_request_id !== request.cargo_request_id ||
                    forecast.route_id !== request.route_id ||
                    forecast.vessel_class_id !== request.vessel_class_id ||
                    forecast.freight_unit !== request.freight_unit
                ) {
                    throw new Error("The forecast response did not match the selected cargo, route, vessel, and unit.");
                }
                return forecast;
            });
            operation = { key, promise };
            forecastRequestRef.current = operation;
        }

        void operation.promise.then((forecast) => {
            if (!active) return;
            setForecastState(forecast.forecast_points.length
                ? { status: "ready", forecast }
                : { status: "empty" });
        }).catch((error: unknown) => {
            if (!active) return;
            setForecastState({ status: "error", message: messageFor(error) });
        });

        return () => { active = false; };
    }, [cargoRequestId, cargoUserId, context, forecastRetryCount, horizon, vesselClassId]);

    const generateForecast = () => {
        if (context.status !== "ready" || !vesselClassId) return;
        forecastRequestRef.current = null;
        setForecastRetryCount((count) => count + 1);
    };

    const currentContextKey = cargoRequestId && cargoUserId
        ? `${cargoUserId}:${cargoRequestId}`
        : null;
    const currentContext: ContextState = !currentContextKey
        ? { status: "empty", message: "Create a cargo request before generating its freight forecast." }
        : contextCargoKey !== currentContextKey ||
            (context.status === "ready" &&
                (context.cargo.cargo_request_id !== cargoRequestId || context.cargo.user_id !== cargoUserId))
            ? { status: "loading" }
            : context;
    const readyContext = currentContext.status === "ready" ? currentContext : null;

    return (
        <div className="freight-forecast-page">
            <Sidebar activePage="freight-forecast" />
            <main className="freight-forecast-main">
                <Link to="/decision-overview" className="forecast-back-link"><ArrowLeft size={16} />Back to Decision Overview</Link>
                <header className="forecast-page-header">
                    <div><span className="forecast-eyebrow">FREIGHT INTELLIGENCE</span><h1>Freight Forecast</h1><p>Generate the backend forecast for the verified cargo, route, and vessel class.</p></div>
                    <div className="forecast-status" role={currentContext.status === "error" || (currentContext.status === "ready" && forecastState.status === "error") ? "alert" : undefined}><span className="forecast-status-dot"></span>{currentContext.status === "loading" ? "Loading reference data" : currentContext.status === "ready" ? forecastState.status === "loading" ? "Generating forecast" : forecastState.status === "ready" ? "Forecast ready" : forecastState.status === "empty" ? "No forecast points" : forecastState.status === "error" ? "Forecast unavailable" : "Ready to forecast" : currentContext.status === "error" ? "Unable to load" : "No forecast data"}</div>
                </header>

                {currentContext.status === "loading" ? <section className="forecast-state-card" role="status" aria-live="polite">Verifying cargo and loading route and vessel references…</section> : null}
                {currentContext.status === "error" ? <section className="forecast-state-card forecast-error" role="alert"><AlertCircle /><div><h2>Forecast inputs unavailable</h2><p>{currentContext.message}</p><button type="button" className="forecast-action-button" onClick={retryContext}>Retry</button></div></section> : null}
                {currentContext.status === "empty" ? <section className="forecast-state-card"><Ship /><div><h2>No forecast inputs</h2><p>{currentContext.message}</p>{cargoRequestId ? <button type="button" className="forecast-action-button" onClick={retryContext}>Retry</button> : <Link to="/cargo-request">Create Cargo Request</Link>}</div></section> : null}

                {readyContext && <>
                    <section className="forecast-request-card">
                        <div><span className="forecast-request-label">VERIFIED CARGO REQUEST</span><h2>{readyContext.cargo.commodity.replace(/_/g, " ")}</h2><small>Cargo Request ID: {readyContext.cargo.cargo_request_id}</small></div>
                        <div className="forecast-request-details">
                            <div><span>Volume</span><strong>{readyContext.cargo.cargo_volume_mt.toLocaleString()} MT</strong></div>
                            <div><span>Origin</span><strong>{readyContext.cargo.origin_port_id}</strong></div>
                            <div><span>Destination</span><strong>{readyContext.cargo.destination_port_id}</strong></div>
                            <div><span>Route</span><strong className="forecast-route-id" title={readyContext.route.route_id}>{readyContext.route.route_id}</strong></div>
                        </div>
                    </section>
                    <section className="forecast-controls-card">
                        <div className="forecast-control-heading"><div className="forecast-control-icon"><CalendarDays size={18} /></div><div><h2>Forecast Inputs</h2><p>Choose an available vessel class and forecast horizon.</p></div></div>
                        <div className="forecast-inputs">
                            <label className="forecast-vessel-label">Vessel class<select value={vesselClassId} onChange={(event) => { setVesselClassId(event.target.value); setForecastState({ status: "idle" }); }}><option value="">Select a vessel class</option>{readyContext.vessels.map((vessel) => <option key={vessel.vessel_class_id} value={vessel.vessel_class_id}>{vessel.vessel_class_name} ({vessel.vessel_class_id})</option>)}</select></label>
                            <div><span className="forecast-vessel-label">Horizon</span><div className="forecast-horizon-options">{HORIZONS.map((value) => <button key={value} type="button" className={`forecast-horizon-button ${horizon === value ? "active" : ""}`} aria-pressed={horizon === value} onClick={() => { setHorizon(value); setForecastState({ status: "idle" }); }}>{value} Days</button>)}</div></div>
                            <button type="button" className="forecast-action-button" disabled={!vesselClassId || forecastState.status === "loading"} onClick={generateForecast}>{forecastState.status === "loading" ? "Generating…" : forecastState.status === "ready" || forecastState.status === "empty" ? "Generate again" : forecastState.status === "error" ? "Retry forecast" : "Generate forecast"}</button>
                        </div>
                    </section>

                    <section className="forecast-chart-card">
                        <div className="forecast-card-header"><div><h2>Freight Rate Outlook</h2><p>Backend forecast values for the selected {horizon}-day horizon.</p></div><div className="forecast-unit-label">USD / MT</div></div>
                        {forecastState.status === "idle" ? <div className="forecast-empty-chart"><div className="forecast-chart-icon"><TrendingUp size={25} /></div><h3>Forecast not generated</h3><p>Select a vessel class and generate a forecast to display backend forecast points.</p></div> : null}
                        {forecastState.status === "loading" ? <div className="forecast-empty-chart" role="status" aria-live="polite"><RefreshCw className="forecast-spinner" size={25} /><h3>Generating forecast</h3><p>Waiting for the backend forecast result.</p></div> : null}
                        {forecastState.status === "error" ? <div className="forecast-empty-chart forecast-error" role="alert"><AlertCircle size={25} /><h3>Forecast unavailable</h3><p>{forecastState.message}</p><button type="button" className="forecast-action-button" onClick={generateForecast}>Retry forecast</button></div> : null}
                        {forecastState.status === "empty" ? <div className="forecast-empty-chart" role="status"><h3>No forecast points returned</h3><p>The backend returned a forecast run without any forecast points.</p><button type="button" className="forecast-action-button" onClick={generateForecast}>Retry forecast</button></div> : null}
                        {forecastState.status === "ready" ? <><ForecastChart points={forecastState.forecast.forecast_points} unit={formatFreightUnit(forecastState.forecast.freight_unit)} /><div className="forecast-chart-legend"><span><i className="legend-dot forecast"></i>Central value</span><span><i className="legend-dot range"></i>Lower/upper range</span></div></> : null}
                    </section>

                    {forecastState.status === "ready" && <section className="forecast-information-card forecast-metadata-card"><div className="forecast-information-header"><TrendingUp size={18} /><h2>Forecast Run</h2></div><div className="forecast-info-row"><span>Unit</span><strong>{formatFreightUnit(forecastState.forecast.freight_unit)}</strong></div><div className="forecast-info-row"><span>Model</span><strong>{forecastState.forecast.model_name} / {forecastState.forecast.model_version}</strong></div><div className="forecast-info-row"><span>Training data end date</span><strong>{forecastState.forecast.training_data_end_date}</strong></div><div className="forecast-info-row"><span>Forecast run ID</span><strong>{forecastState.forecast.forecast_run_id}</strong></div><div className="forecast-info-row"><span>Selected horizon</span><strong>{horizon} days</strong></div></section>}
                </>}
            </main>
        </div>
    );
}

export default FreightForecast;
