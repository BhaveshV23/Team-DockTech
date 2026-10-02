import { useEffect, useRef, useState } from "react";
import { AlertCircle, ArrowLeft, CheckCircle2, Info, RefreshCw, TrendingDown, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import DataProvenance from "../components/DataProvenance";
import { useCargoRequest } from "../hooks/useCargoRequest";
import { apiRequest, useAuthenticatedUser } from "../services/api";
import {
    createRecommendation,
    getStoredRecommendation,
    storeRecommendation,
} from "../services/recommendation";
import type { RecommendationResult } from "../types/recommendation";
import type { CargoRequestResponse } from "../types/cargo";
import type { CanonicalScenarioSet, CongestionLevel, CustomScenarioRequest, ScenarioApiResponse, ScenarioComparison, ScenarioDefault, ScenarioResult } from "../types/scenario";
import "./ScenariosRisk.css";

type PageState =
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "empty"; message: string }
    | { status: "ready"; cargo: CargoRequestResponse; forecastRunId: string; defaults: ScenarioDefault[]; canonical: CanonicalScenarioSet };

type CustomForm = { freight: string; fuel: string; delay: string; congestion: CongestionLevel };
type CustomState = { status: "idle" } | { status: "loading" } | { status: "error"; message: string } | { status: "ready"; comparison: ScenarioComparison };

const initialCustomForm: CustomForm = { freight: "0", fuel: "0", delay: "0", congestion: "MEDIUM" };
const SCENARIOS: Array<{ key: keyof CanonicalScenarioSet; title: string; icon: typeof CheckCircle2 }> = [
    { key: "baseline", title: "Baseline", icon: CheckCircle2 },
    { key: "adverse", title: "Adverse", icon: TrendingUp },
    { key: "favorable", title: "Favorable", icon: TrendingDown },
];

function unwrap<T>(response: ScenarioApiResponse<T>, label: string): T {
    if (!response.success || response.data === null) throw new Error(response.message || `${label} returned no data.`);
    return response.data;
}

function formatUsd(value: number) {
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(value);
}

function formatOperationalValue(value: number) {
    return value.toFixed(2);
}

function formatPercent(value: number) {
    return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value)}%`;
}

function formatInteger(value: number) {
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value);
}

function parseCongestionLevel(value: string): CongestionLevel {
    if (value === "LOW" || value === "MEDIUM" || value === "HIGH") return value;
    return "MEDIUM";
}

function ScenarioMetrics({ result }: { result: ScenarioResult }) {
    const cost = result.cost_breakdown;
    const rows: Array<[string, string]> = [
        ["Sailing", `${formatOperationalValue(cost.sailing_days)} days`],
        ["Origin handling", `${formatOperationalValue(cost.origin_handling_hours_total)} h`],
        ["Destination handling", `${formatOperationalValue(cost.destination_handling_hours_total)} h`],
        ["Waiting", `${formatOperationalValue(cost.waiting_hours_total)} h`],
        ["Scenario delay", `${formatOperationalValue(cost.scenario_delay_total)} h`],
        ["Turnaround per voyage", `${formatOperationalValue(cost.turnaround_hours_per_voyage)} h`],
        ["Port duration per voyage", `${formatOperationalValue(cost.port_days_per_voyage)} days`],
        ["Vessel duration per voyage", `${formatOperationalValue(cost.vessel_days_per_voyage)} days`],
        ["Fuel cost", formatUsd(cost.total_fuel_cost_usd)],
        ["Freight cost", formatUsd(cost.expected_freight_cost)],
        ["Total cost", formatUsd(cost.expected_total_cost)],
        ["Effective cost per MT", `${formatUsd(cost.effective_cost_per_mt)} / MT`],
    ];
    return <details className="scenario-cost-details"><summary>Cost breakdown</summary><dl>{rows.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl></details>;
}

function ScenarioResultCard({ result, description, title, icon: Icon }: { result: ScenarioResult; description?: string; title: string; icon: typeof CheckCircle2 }) {
    return (
        <article className={`scenario-card ${result.scenario_type.toLowerCase()}`}>
            <div className="scenario-card-header"><div className="scenario-icon"><Icon size={19} /></div><span className="scenario-label">{result.scenario_type}</span></div>
            <h3>{title} Scenario</h3>
            {description && <p>{description}</p>}
            <div className="scenario-metrics">
                <div><span>Freight adjustment</span><strong>{formatPercent(result.freight_change_pct)}</strong></div>
                <div><span>Fuel adjustment</span><strong>{formatPercent(result.fuel_change_pct)}</strong></div>
                <div><span>Delay</span><strong>{formatOperationalValue(result.delay_hours)} h</strong></div>
                <div><span>Congestion</span><strong>{result.congestion_level}</strong></div>
                <div><span>Estimated total cost</span><strong>{formatUsd(result.estimated_total_cost)}</strong></div>
                <div><span>Estimated turnaround</span><strong>{formatOperationalValue(result.estimated_turnaround_hours)} h</strong></div>
                <div><span>Risk</span><strong>{result.risk_level}</strong></div>
                <div><span>Required voyages</span><strong>{formatInteger(result.cost_breakdown.required_voyages)}</strong></div>
            </div>
            <ScenarioMetrics result={result} />
        </article>
    );
}

function ScenariosRisk() {
    const storedCargo = useCargoRequest();
    const user = useAuthenticatedUser();
    const cargoRequestId = storedCargo?.cargo_request_id;
    const cargoUserId = storedCargo?.user_id;
    const userId = user?.user_id;
    const [retryCount, setRetryCount] = useState(0);
    const [pageState, setPageState] = useState<PageState>(cargoRequestId ? { status: "loading" } : { status: "empty", message: "Create a cargo request before running scenario analysis." });
    const [form, setForm] = useState<CustomForm>(initialCustomForm);
    const [customState, setCustomState] = useState<CustomState>({ status: "idle" });
    const recommendationRequestRef = useRef<{ key: string; promise: Promise<RecommendationResult> } | null>(null);
    const pageLoadRequestRef = useRef<{ key: string; promise: Promise<PageState> } | null>(null);

    useEffect(() => {
        if (!cargoRequestId || !cargoUserId || !userId) return;
        let active = true;
        const loadScenarios = async (): Promise<PageState> => {
            const key = `${userId}:${cargoRequestId}`;
            const cachedRecommendation = getStoredRecommendation(userId, cargoRequestId);
            const cargo = await apiRequest<CargoRequestResponse>(`/api/v1/cargo-requests/${encodeURIComponent(cargoRequestId)}`);
            if (cargo.cargo_request_id !== cargoRequestId || cargo.user_id !== userId || cargoUserId !== userId) {
                throw new Error("The active cargo request could not be verified for this user.");
            }

            let recommendation = cachedRecommendation?.cargo_request_id === cargoRequestId &&
                cachedRecommendation.forecast_run_id.trim()
                ? cachedRecommendation
                : getStoredRecommendation(userId, cargoRequestId);
            if (!recommendation || recommendation.cargo_request_id !== cargoRequestId || !recommendation.forecast_run_id.trim()) {
                let recommendationRequest = recommendationRequestRef.current?.key === key
                    ? recommendationRequestRef.current.promise
                    : null;
                if (!recommendationRequest) {
                    recommendationRequest = createRecommendation(cargoRequestId);
                    recommendationRequestRef.current = { key, promise: recommendationRequest };
                    void recommendationRequest.catch(() => {
                        if (recommendationRequestRef.current?.promise === recommendationRequest) {
                            recommendationRequestRef.current = null;
                        }
                    });
                }
                recommendation = await recommendationRequest;
                if (
                    recommendation.cargo_request_id !== cargoRequestId ||
                    !recommendation.forecast_run_id
                ) {
                    throw new Error("The existing recommendation workflow returned no matching forecast run.");
                }
                storeRecommendation(userId, cargoRequestId, recommendation);
            }

            if (recommendation.cargo_request_id !== cargoRequestId || !recommendation.forecast_run_id) {
                throw new Error("The existing recommendation workflow returned no matching forecast run.");
            }
            const defaultsResponse = await apiRequest<ScenarioApiResponse<ScenarioDefault[]>>(
                "/api/v1/scenarios/defaults",
            );
            const defaults = unwrap(defaultsResponse, "Scenario defaults");
            if (defaults.length === 0) return { status: "empty", message: "The backend returned no canonical scenario defaults." };

            const canonicalResponse = await apiRequest<ScenarioApiResponse<CanonicalScenarioSet>>("/api/v1/scenarios/run-canonical", {
                method: "POST",
                body: JSON.stringify({ cargo_request_id: cargoRequestId, forecast_run_id: recommendation.forecast_run_id }),
            });
            const canonical = unwrap(canonicalResponse, "Canonical scenarios");
            if (
                canonical.baseline?.cargo_request_id !== cargoRequestId ||
                canonical.adverse?.cargo_request_id !== cargoRequestId ||
                canonical.favorable?.cargo_request_id !== cargoRequestId
            ) {
                throw new Error("The canonical scenario response does not match the active cargo request.");
            }
            const readyState: PageState = { status: "ready", cargo, forecastRunId: recommendation.forecast_run_id, defaults, canonical };
            if (active) {
                setPageState(readyState);
                setCustomState({ status: "idle" });
            }
            return readyState;
        };
        const key = `${userId}:${cargoRequestId}`;
        let pageLoadRequest = pageLoadRequestRef.current?.key === key ? pageLoadRequestRef.current.promise : null;
        if (!pageLoadRequest) {
            pageLoadRequest = loadScenarios();
            pageLoadRequestRef.current = { key, promise: pageLoadRequest };
            void pageLoadRequest.catch(() => {
                if (pageLoadRequestRef.current?.promise === pageLoadRequest) pageLoadRequestRef.current = null;
            });
        }
        void pageLoadRequest.then((result) => {
            if (active) {
                setPageState(result);
                setCustomState({ status: "idle" });
            }
        }).catch((error: unknown) => {
            if (active) setPageState({ status: "error", message: error instanceof Error ? error.message : "Unable to load scenario results." });
        });
        return () => { active = false; };
    }, [cargoRequestId, cargoUserId, retryCount, userId]);

    const retry = () => {
        pageLoadRequestRef.current = null;
        setPageState({ status: "loading" });
        setRetryCount((count) => count + 1);
    };

    const submitCustomScenario = async () => {
        if (pageState.status !== "ready" || customState.status === "loading") return;
        const freight = Number(form.freight);
        const fuel = Number(form.fuel);
        const delay = Number(form.delay);
        const numericInputPattern = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/;
        if (
            ![form.freight, form.fuel, form.delay].every((value) => numericInputPattern.test(value.trim())) ||
            ![freight, fuel, delay].every(Number.isFinite) ||
            delay < 0
        ) {
            setCustomState({ status: "error", message: "Enter valid numeric adjustments and a nonnegative delay." });
            return;
        }
        const request: CustomScenarioRequest = {
            cargo_request_id: pageState.cargo.cargo_request_id,
            forecast_run_id: pageState.forecastRunId,
            freight_change_pct: freight,
            fuel_change_pct: fuel,
            delay_hours: delay,
            congestion_level: form.congestion,
        };
        setCustomState({ status: "loading" });
        try {
            const response = await apiRequest<ScenarioApiResponse<ScenarioComparison>>("/api/v1/scenarios/evaluate", { method: "POST", body: JSON.stringify(request) });
            const comparison = unwrap(response, "Custom scenario");
            if (comparison.scenario_result.cargo_request_id !== pageState.cargo.cargo_request_id) {
                throw new Error("The custom scenario response does not match the active cargo request.");
            }
            setCustomState({ status: "ready", comparison });
        } catch (error) {
            setCustomState({ status: "error", message: error instanceof Error ? error.message : "Unable to evaluate the custom scenario." });
        }
    };

    const defaultsByType = pageState.status === "ready" ? new Map(pageState.defaults.map((item) => [item.scenario_id, item])) : null;
    const hasActiveCargo = Boolean(cargoRequestId && cargoUserId && userId && cargoUserId === userId);
    const visiblePageState: PageState = !hasActiveCargo
        ? { status: "empty" as const, message: "Create a cargo request before running scenario analysis." }
        : pageState.status === "ready" &&
            (pageState.cargo.cargo_request_id !== cargoRequestId || pageState.cargo.user_id !== userId)
            ? { status: "loading" as const }
            : pageState;

    return (
        <div className="scenarios-risk-page">
            <Sidebar activePage="scenarios-risk" />
            <main className="scenarios-risk-main">
                <Link to="/decision-overview" className="scenarios-back-link"><ArrowLeft size={16} />Back to Decision Overview</Link>
                <header className="scenarios-page-header"><div><span className="scenarios-eyebrow">SCENARIO ANALYSIS</span><h1>Scenarios &amp; Risk</h1><p>Review backend-generated canonical scenarios and evaluate custom adjustments.</p></div><div className="scenarios-status" role={visiblePageState.status === "error" ? "alert" : undefined}><span className="scenarios-status-dot"></span>{visiblePageState.status === "loading" ? "Loading scenarios" : visiblePageState.status === "ready" ? "Scenario results ready" : visiblePageState.status === "error" ? "Unable to load" : "No scenario data"}</div></header>

                {visiblePageState.status === "loading" && <section className="scenarios-page-state" role="status" aria-live="polite"><RefreshCw className="scenarios-spinner" /><div><h2>Loading scenario analysis</h2><p>Verifying cargo and loading its recommendation forecast run, defaults, and canonical scenarios.</p></div></section>}
                {visiblePageState.status === "error" && <section className="scenarios-page-state scenarios-error" role="alert"><AlertCircle /><div><h2>Scenario analysis unavailable</h2><p>{visiblePageState.message}</p><button type="button" className="scenarios-submit-button" onClick={retry}>Retry</button></div></section>}
                {visiblePageState.status === "empty" && <section className="scenarios-page-state" role="status"><Info /><div><h2>No scenario data</h2><p>{visiblePageState.message}</p>{cargoRequestId ? <button type="button" className="scenarios-submit-button" onClick={retry}>Retry</button> : <Link to="/cargo-request">Create Cargo Request</Link>}</div></section>}

                <DataProvenance />

                {pageState.status === "ready" && visiblePageState.status === "ready" && <>
                    <section className="scenarios-request-card"><div><span className="scenarios-request-label">VERIFIED CARGO REQUEST</span><h2>{pageState.cargo.commodity.replace(/_/g, " ")}</h2><div className="scenarios-provenance"><small>Cargo Request ID: {pageState.cargo.cargo_request_id}</small><small>Forecast Run ID: {pageState.forecastRunId}</small></div></div><div className="scenarios-request-details"><div><span>Volume</span><strong>{pageState.cargo.cargo_volume_mt} MT</strong></div><div><span>Origin</span><strong>{pageState.cargo.origin_port_id}</strong></div><div><span>Destination</span><strong>{pageState.cargo.destination_port_id}</strong></div></div></section>

                    <section className="scenarios-section"><div className="scenarios-section-heading"><div><h2>Canonical Scenario Comparison</h2><p>Scenario impacts, costs, and risk are returned by the backend.</p></div></div><div className="scenario-grid">{SCENARIOS.map(({ key, title, icon }) => { const result = pageState.canonical[key]; const defaultData = defaultsByType?.get(result.scenario_type); return <ScenarioResultCard key={key} result={result} title={title} icon={icon} description={defaultData?.description} />; })}</div></section>

                    <section className="scenarios-custom-card"><div className="scenarios-section-heading"><div><h2>Evaluate Custom Scenario</h2><p>Submit adjustments to the backend for comparison against its baseline.</p></div></div><div className="scenarios-custom-controls"><label>Freight adjustment (%)<input type="number" step="any" value={form.freight} onChange={(event) => setForm((current) => ({ ...current, freight: event.target.value }))} /></label><label>Fuel adjustment (%)<input type="number" step="any" value={form.fuel} onChange={(event) => setForm((current) => ({ ...current, fuel: event.target.value }))} /></label><label>Delay (hours)<input type="number" min="0" step="any" value={form.delay} onChange={(event) => setForm((current) => ({ ...current, delay: event.target.value }))} /></label><label>Congestion level<select value={form.congestion} onChange={(event) => setForm((current) => ({ ...current, congestion: parseCongestionLevel(event.target.value) }))}><option value="LOW">LOW</option><option value="MEDIUM">MEDIUM</option><option value="HIGH">HIGH</option></select></label><button type="button" className="scenarios-submit-button" disabled={customState.status === "loading"} onClick={() => void submitCustomScenario()}>{customState.status === "loading" ? "Evaluating…" : "Evaluate scenario"}</button></div>
                        {customState.status === "loading" && <p className="scenarios-inline-state" role="status">Evaluating custom scenario…</p>}
                        {customState.status === "error" && <div className="scenarios-inline-error" role="alert"><p>{customState.message}</p><button type="button" onClick={() => void submitCustomScenario()}>Retry evaluation</button></div>}
                        {customState.status === "ready" && <div className="scenarios-custom-result"><h3>Custom Scenario Result · {customState.comparison.scenario_result.scenario_type}</h3><div className="scenarios-delta-grid"><div><span>Freight adjustment</span><strong>{formatPercent(customState.comparison.scenario_result.freight_change_pct)}</strong></div><div><span>Fuel adjustment</span><strong>{formatPercent(customState.comparison.scenario_result.fuel_change_pct)}</strong></div><div><span>Delay</span><strong>{formatOperationalValue(customState.comparison.scenario_result.delay_hours)} h</strong></div><div><span>Congestion</span><strong>{customState.comparison.scenario_result.congestion_level}</strong></div><div><span>Scenario total cost</span><strong>{formatUsd(customState.comparison.scenario_result.estimated_total_cost)}</strong></div><div><span>Turnaround</span><strong>{formatOperationalValue(customState.comparison.scenario_result.estimated_turnaround_hours)} h</strong></div><div><span>Risk</span><strong>{customState.comparison.scenario_result.risk_level}</strong></div><div><span>Required voyages</span><strong>{formatInteger(customState.comparison.scenario_result.cost_breakdown.required_voyages)}</strong></div><div><span>Cost delta</span><strong>{formatUsd(customState.comparison.delta_cost_usd)}</strong></div><div><span>Cost delta</span><strong>{formatPercent(customState.comparison.delta_cost_pct)}</strong></div><div><span>Turnaround delta</span><strong>{formatOperationalValue(customState.comparison.delta_turnaround_hours)} h</strong></div><div><span>Effective cost / MT delta</span><strong>{formatUsd(customState.comparison.delta_effective_cost_per_mt)} / MT</strong></div><div><span>Risk transition</span><strong>{customState.comparison.risk_transition}</strong></div></div><ScenarioMetrics result={customState.comparison.scenario_result} /></div>}
                    </section>
                </>}

            </main>
        </div>
    );
}

export default ScenariosRisk;
