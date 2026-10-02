import { useEffect, useRef, useState } from "react";
import { AlertCircle, ArrowLeft, CalendarDays, RefreshCw, Ship, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import DataProvenance from "../components/DataProvenance";
import { useCargoRequest } from "../hooks/useCargoRequest";
import { apiRequest, useAuthenticatedUser } from "../services/api";
import type { CargoRequestResponse } from "../types/cargo";
import type { FreightHistoryResponse, ForecastHorizon, ForecastRequest, ForecastRunResponse } from "../types/forecast";
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

type HistoryState =
    | { status: "idle" | "loading" }
    | { status: "error"; message: string }
    | { status: "ready"; history: FreightHistoryResponse };

const HORIZONS: ForecastHorizon[] = [7, 30, 90];

function messageFor(error: unknown) {
    return error instanceof Error ? error.message : "Unable to load forecast data. Please try again.";
}

function formatFreightUnit(unit: string): string {
    return unit.replace("_PER_", " / ");
}

function ForecastChart({ history, points, unit }: { history: FreightHistoryResponse["observations"]; points: ForecastRunResponse["forecast_points"]; unit: string }) {
    if (points.length === 0) return null;

    const width = 900;
    const height = 310;
    const padding = { top: 18, right: 24, bottom: 48, left: 64 };
    const historicalDates = history.map((point) => Date.parse(`${point.observation_date}T00:00:00Z`));
    const forecastDates = points.map((point) => Date.parse(`${point.forecast_date}T00:00:00Z`));
    const allDates = [...historicalDates, ...forecastDates];
    const minDate = Math.min(...allDates);
    const maxDate = Math.max(...allDates);
    const x = (timestamp: number) => padding.left + (maxDate === minDate ? (width - padding.left - padding.right) / 2 : (timestamp - minDate) * (width - padding.left - padding.right) / (maxDate - minDate));
    const values = [...history.map((point) => point.freight_value), ...points.flatMap((point) => [point.lower_value, point.central_value, point.upper_value])];
    const min = Math.min(...values);
    const max = Math.max(...values);
    const spread = max - min || Math.max(Math.abs(max) * 0.1, 1);
    const yMin = min - spread * 0.08;
    const yMax = max + spread * 0.08;
    const y = (value: number) => padding.top + (yMax - value) * (height - padding.top - padding.bottom) / (yMax - yMin);
    const pathFor = <T,>(items: T[], date: (item: T) => string, value: (item: T) => number) => items.map((item, index) => `${index === 0 ? "M" : "L"} ${x(Date.parse(`${date(item)}T00:00:00Z`))} ${y(value(item))}`).join(" ");
    const line = (key: "central_value" | "lower_value" | "upper_value") => pathFor(points, (point) => point.forecast_date, (point) => point[key]);
    const historyLine = pathFor(history, (point) => point.observation_date, (point) => point.freight_value);
    const band = `${pathFor(points, (point) => point.forecast_date, (point) => point.upper_value)} ${points.slice().reverse().map((point) => `L ${x(Date.parse(`${point.forecast_date}T00:00:00Z`))} ${y(point.lower_value)}`).join(" ")} Z`;
    const dateLabels = [...new Set([history[0]?.observation_date, history.at(-1)?.observation_date, points.at(-1)?.forecast_date].filter((value): value is string => Boolean(value)))];
    const forecastStart = x(Date.parse(`${points[0].forecast_date}T00:00:00Z`));

    return (
        <div className="forecast-chart-scroll">
            <svg className="forecast-data-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`Historical reference freight observations and forecast base values with lower and upper bounds in ${unit}`}>
                <text x="8" y="16" className="forecast-axis-unit">{unit}</text>
                {[0, 1, 2, 3].map((tick) => {
                    const value = yMax - ((yMax - yMin) * tick) / 3;
                    const lineY = y(value);
                    return <g key={tick}><line x1={padding.left} x2={width - padding.right} y1={lineY} y2={lineY} className="forecast-gridline" /><text x={padding.left - 8} y={lineY + 4} textAnchor="end" className="forecast-axis-label">{value.toLocaleString(undefined, { maximumFractionDigits: 2 })}</text></g>;
                })}
                {history.length > 0 && <path d={historyLine} className="forecast-history-line" />}
                {history.map((point, index) => <circle key={`history-${point.observation_date}-${index}`} cx={x(Date.parse(`${point.observation_date}T00:00:00Z`))} cy={y(point.freight_value)} r="1.8" className="forecast-history-point"><title>{`${point.observation_date}: ${point.freight_value} ${formatFreightUnit(point.freight_unit)} historical reference observation`}</title></circle>)}
                <line x1={forecastStart} x2={forecastStart} y1={padding.top} y2={height - padding.bottom} className="forecast-start-marker" />
                <text x={forecastStart + 5} y={padding.top + 10} className="forecast-start-label">Forecast starts</text>
                <path d={band} className="forecast-range-band" />
                <path d={line("upper_value")} className="forecast-bound-line" />
                <path d={line("lower_value")} className="forecast-bound-line" />
                <path d={line("central_value")} className="forecast-central-line" />
                {points.map((point, index) => <circle key={`${point.forecast_date}-${index}`} cx={x(Date.parse(`${point.forecast_date}T00:00:00Z`))} cy={y(point.central_value)} r="3" className="forecast-central-point"><title>{`${point.forecast_date}: ${point.central_value} ${formatFreightUnit(point.unit)} forecast base`}</title></circle>)}
                {dateLabels.map((dateLabel) => <text key={dateLabel} x={x(Date.parse(`${dateLabel}T00:00:00Z`))} y={height - 15} textAnchor="middle" className="forecast-axis-label">{dateLabel}</text>)}
                <text x={width / 2} y={height - 1} textAnchor="middle" className="forecast-axis-label">Date</text>
            </svg>
        </div>
    );
}

function FreightForecast() {
    const storedCargo = useCargoRequest();
    const user = useAuthenticatedUser();
    const cargoRequestId = storedCargo && user && storedCargo.user_id === user.user_id
        ? storedCargo.cargo_request_id
        : undefined;
    const cargoUserId = storedCargo && user && storedCargo.user_id === user.user_id
        ? storedCargo.user_id
        : undefined;
    const [retryCount, setRetryCount] = useState(0);
    const [context, setContext] = useState<ContextState>(cargoRequestId && cargoUserId ? { status: "loading" } : { status: "empty", message: "Create a cargo request before generating its freight forecast." });
    const [contextCargoKey, setContextCargoKey] = useState<string | null>(
        cargoRequestId && cargoUserId ? `${cargoUserId}:${cargoRequestId}` : null,
    );
    const [horizon, setHorizon] = useState<ForecastHorizon>(7);
    const [vesselClassId, setVesselClassId] = useState("");
    const [forecastState, setForecastState] = useState<ForecastState>({ status: "idle" });
    const [historyState, setHistoryState] = useState<HistoryState>({ status: "idle" });
    const [historyRetryCount, setHistoryRetryCount] = useState(0);
    const [forecastRetryCount, setForecastRetryCount] = useState(0);
    const forecastRequestRef = useRef<{
        key: string;
        promise: Promise<ForecastRunResponse>;
    } | null>(null);
    const forecastResultsRef = useRef(new Map<string, ForecastRunResponse>());
    const historyRequestsRef = useRef(new Map<string, Promise<FreightHistoryResponse>>());
    const historyResultsRef = useRef(new Map<string, FreightHistoryResponse>());

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
            if (matchingRoutes.length > 1) return { status: "error" as const, message: "More than one canonical route matches this cargo; a unique route is required." };
            const route = matchingRoutes[0];
            if (!route.route_id?.trim()) return { status: "error" as const, message: "The matching canonical route has no valid route ID." };
            const validVessels = vessels.filter((vessel) =>
                typeof vessel.vessel_class_id === "string" && vessel.vessel_class_id.trim().length > 0,
            );
            if (validVessels.length === 0) return { status: "empty" as const, message: "No valid canonical vessel classes are available from the backend." };
            return { status: "ready" as const, cargo, route, vessels: validVessels };
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
        if (context.status !== "ready" || !vesselClassId) {
            return;
        }
        const key = `${context.route.route_id}:${vesselClassId}:USD_PER_MT`;
        const cachedHistory = historyResultsRef.current.get(key);
        if (cachedHistory) {
            setHistoryState({ status: "ready", history: cachedHistory });
            return;
        }

        let active = true;
        setHistoryState({ status: "loading" });
        let request = historyRequestsRef.current.get(key);
        if (!request) {
            const params = new URLSearchParams({
                route_id: context.route.route_id,
                vessel_class_id: vesselClassId,
                freight_unit: "USD_PER_MT",
            });
            request = apiRequest<FreightHistoryResponse>(`/api/v1/forecast/history?${params.toString()}`)
                .then((history) => {
                    if (
                        history.route_id !== context.route.route_id ||
                        history.vessel_class_id !== vesselClassId ||
                        history.freight_unit !== "USD_PER_MT" ||
                        !Array.isArray(history.observations) ||
                        history.observations.some((point) => point.freight_unit !== history.freight_unit)
                    ) {
                        throw new Error("Historical freight data did not match the selected route, vessel, and unit.");
                    }
                    historyResultsRef.current.set(key, history);
                    return history;
                });
            historyRequestsRef.current.set(key, request);
        }
        void request.then((history) => {
            historyRequestsRef.current.delete(key);
            if (active) setHistoryState({ status: "ready", history });
        }).catch((error: unknown) => {
            historyRequestsRef.current.delete(key);
            if (active) setHistoryState({ status: "error", message: messageFor(error) });
        });
        return () => { active = false; };
    }, [context, historyRetryCount, vesselClassId]);

    useEffect(() => {
        if (
            !cargoRequestId ||
            !cargoUserId ||
            context.status !== "ready" ||
            context.cargo.cargo_request_id !== cargoRequestId ||
            context.cargo.user_id !== cargoUserId ||
            !vesselClassId ||
            !context.vessels.some((vessel) => vessel.vessel_class_id === vesselClassId)
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
        const cachedForecast = forecastResultsRef.current.get(key);
        if (cachedForecast) {
            setForecastState({ status: "ready", forecast: cachedForecast });
            return () => { active = false; };
        }
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
                    forecast.freight_unit !== request.freight_unit ||
                    !Array.isArray(forecast.forecast_points)
                ) {
                    throw new Error("The forecast response did not match the selected cargo, route, vessel, and unit.");
                }
                if (forecast.forecast_points.length > 0) {
                    forecastResultsRef.current.set(key, forecast);
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
        const request: ForecastRequest = {
            cargo_request_id: context.cargo.cargo_request_id,
            route_id: context.route.route_id,
            vessel_class_id: vesselClassId,
            freight_unit: "USD_PER_MT",
            horizon,
        };
        forecastResultsRef.current.delete(JSON.stringify(request));
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
                    <div><span className="forecast-eyebrow">FREIGHT INTELLIGENCE</span><h1>Freight Forecast</h1><p>Review historical reference rates and generate the backend forecast for the verified cargo, route, and vessel class.</p></div>
                    <div className="forecast-status" role={currentContext.status === "error" || (currentContext.status === "ready" && forecastState.status === "error") ? "alert" : undefined}><span className="forecast-status-dot"></span>{currentContext.status === "loading" ? "Loading reference data" : currentContext.status === "ready" ? forecastState.status === "loading" ? "Generating forecast" : forecastState.status === "ready" ? "Forecast ready" : forecastState.status === "empty" ? "No forecast points" : forecastState.status === "error" ? "Forecast unavailable" : "Ready to forecast" : currentContext.status === "error" ? "Unable to load" : "No forecast data"}</div>
                </header>

                <DataProvenance />

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
                        {historyState.status === "loading" && <p className="forecast-history-status" role="status">Loading dated historical freight reference observations…</p>}
                        {historyState.status === "error" && <p className="forecast-history-status forecast-history-error" role="alert">Historical reference observations are unavailable: {historyState.message} <button type="button" onClick={() => setHistoryRetryCount((count) => count + 1)}>Retry history</button></p>}
                        {forecastState.status === "idle" ? <div className="forecast-empty-chart"><div className="forecast-chart-icon"><TrendingUp size={25} /></div><h3>Forecast not generated</h3><p>Select a vessel class and generate a forecast to display backend forecast points.</p></div> : null}
                        {forecastState.status === "loading" ? <div className="forecast-empty-chart" role="status" aria-live="polite"><RefreshCw className="forecast-spinner" size={25} /><h3>Generating forecast</h3><p>Waiting for the backend forecast result.</p></div> : null}
                        {forecastState.status === "error" ? <div className="forecast-empty-chart forecast-error" role="alert"><AlertCircle size={25} /><h3>Forecast unavailable</h3><p>{forecastState.message}</p><button type="button" className="forecast-action-button" onClick={generateForecast}>Retry forecast</button></div> : null}
                        {forecastState.status === "empty" ? <div className="forecast-empty-chart" role="status"><h3>No forecast points returned</h3><p>The backend returned a forecast run without any forecast points.</p><button type="button" className="forecast-action-button" onClick={generateForecast}>Retry forecast</button></div> : null}
                        {forecastState.status === "ready" ? <><ForecastChart history={historyState.status === "ready" ? historyState.history.observations : []} points={forecastState.forecast.forecast_points} unit={formatFreightUnit(forecastState.forecast.freight_unit)} /><div className="forecast-chart-legend"><span><i className="legend-dot historical"></i>Historical reference observations</span><span><i className="legend-dot forecast"></i>Forecast base</span><span><i className="legend-dot range"></i>Lower/upper forecast bounds</span></div>{historyState.status === "ready" && historyState.history.observations.length === 0 ? <p className="forecast-history-status">No historical reference observations exist for this route, vessel class, and freight unit.</p> : null}</> : null}
                    </section>

                    {forecastState.status === "ready" && <section className="forecast-information-card forecast-metadata-card"><div className="forecast-information-header"><TrendingUp size={18} /><h2>Forecast Run</h2></div><div className="forecast-info-row"><span>Unit</span><strong>{formatFreightUnit(forecastState.forecast.freight_unit)}</strong></div><div className="forecast-info-row"><span>Model</span><strong>{forecastState.forecast.model_name} / {forecastState.forecast.model_version}</strong></div><div className="forecast-info-row"><span>Training data end date</span><strong>{forecastState.forecast.training_data_end_date}</strong></div><div className="forecast-info-row"><span>Forecast run ID</span><strong>{forecastState.forecast.forecast_run_id}</strong></div><div className="forecast-info-row"><span>Selected horizon</span><strong>{horizon} days</strong></div></section>}
                </>}
            </main>
        </div>
    );
}

export default FreightForecast;
