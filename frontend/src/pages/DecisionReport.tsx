import { useEffect, useRef, useState } from "react";
import { AlertCircle, AlertTriangle, ArrowLeft, BarChart3, CheckCircle2, Download, FileText, Info, Ship, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import DataProvenance from "../components/DataProvenance";
import { useWorkflowState } from "../context/WorkflowStateContext";
import type { WorkflowScope } from "../context/WorkflowStateContext";
import { useCargoRequest } from "../hooks/useCargoRequest";
import { apiRequest, useAuthenticatedUser } from "../services/api";
import { getStoredRecommendation } from "../services/recommendation";
import type { CargoRequestResponse } from "../types/cargo";
import type { RecommendationResult } from "../types/recommendation";
import "./DecisionReport.css";

type ReportState =
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "no-cargo" }
    | { status: "no-decision"; cargo: CargoRequestResponse }
    | { status: "ready"; cargo: CargoRequestResponse; recommendation: RecommendationResult };

function isReusableCargo(value: CargoRequestResponse | null, userId: string, cargoRequestId: string): value is CargoRequestResponse {
    return Boolean(value && value.user_id === userId && value.cargo_request_id === cargoRequestId &&
        typeof value.commodity === "string" && typeof value.cargo_volume_mt === "number" &&
        Number.isFinite(value.cargo_volume_mt) && typeof value.origin_port_id === "string" &&
        typeof value.destination_port_id === "string" && typeof value.earliest_delivery_date === "string" &&
        typeof value.latest_delivery_date === "string" && typeof value.contract_horizon === "string");
}

function formatMoney(value: number | string) {
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(Number(value));
}

function formatTimestamp(value: string) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    const datePart = date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
    const timePart = date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: true });
    return `${datePart} · ${timePart}`;
}

function formatAssumptions(value: string): string[] {
    const formattedRates = value.replace(
        /([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s+(USD_PER_MT|USD_PER_DAY)/g,
        (_match, amount: string, unit: string) => {
            const numericAmount = Number(amount);
            const displayUnit = unit === "USD_PER_MT" ? "USD/MT" : "USD/day";
            return `${Number.isFinite(numericAmount) ? numericAmount.toFixed(2) : amount} ${displayUnit}`;
        },
    );
    return formattedRates.split(/(?<=[.;])\s+/).map((assumption) => assumption.trim()).filter(Boolean);
}

function DecisionReport() {
    const storedCargo = useCargoRequest();
    const user = useAuthenticatedUser();
    const cargoRequestId = storedCargo?.cargo_request_id;
    const storedCargoUserId = storedCargo?.user_id;
    const userId = user?.user_id;
    const workflow = useWorkflowState();
    const workflowRef = useRef(workflow);
    const [retryCount, setRetryCount] = useState(0);
    const [pageState, setPageState] = useState<ReportState>(cargoRequestId ? { status: "loading" } : { status: "no-cargo" });

    useEffect(() => {
        workflowRef.current = workflow;
    }, [workflow]);

    useEffect(() => {
        if (!cargoRequestId || !storedCargoUserId || !userId) return;
        let active = true;
        const loadReport = async () => {
            if (storedCargoUserId !== userId) throw new Error("The saved cargo request does not belong to the signed-in user.");
            const workflowState = workflowRef.current;
            const scope: WorkflowScope = { userId, cargoRequestId };
            workflowState.setActiveScope(userId, cargoRequestId);
            const cachedRecommendation = getStoredRecommendation(userId, cargoRequestId);
            const contextCargo = workflowState.getVerifiedCargo(scope);
            const cargo = isReusableCargo(contextCargo, userId, cargoRequestId)
                ? contextCargo
                : await apiRequest<CargoRequestResponse>(`/api/v1/cargo-requests/${encodeURIComponent(cargoRequestId)}`);
            if (cargo.cargo_request_id !== cargoRequestId || cargo.user_id !== userId) {
                throw new Error("The backend cargo request could not be verified for this user.");
            }
            if (!isReusableCargo(contextCargo, userId, cargoRequestId) &&
                isReusableCargo(cargo, userId, cargoRequestId)) {
                workflowState.setVerifiedCargo(scope, cargo);
            }
            const recommendation = [
                cachedRecommendation,
                getStoredRecommendation(userId, cargoRequestId),
            ].find((candidate): candidate is RecommendationResult =>
                candidate !== null &&
                candidate.cargo_request_id === cargo.cargo_request_id &&
                candidate.recommendation_id.trim().length > 0 &&
                candidate.forecast_run_id.trim().length > 0,
            );
            if (!recommendation) {
                return { status: "no-decision" as const, cargo };
            }
            return { status: "ready" as const, cargo, recommendation };
        };
        void loadReport().then((result) => {
            if (active) setPageState(result);
        }).catch((error: unknown) => {
            if (active) setPageState({ status: "error", message: error instanceof Error ? error.message : "Unable to verify report data." });
        });
        return () => { active = false; };
    }, [cargoRequestId, retryCount, storedCargoUserId, userId]);

    const retry = () => {
        if (userId && cargoRequestId) {
            workflowRef.current.invalidateWorkflowEntry({ type: "verifiedCargo" });
        }
        setPageState({ status: "loading" });
        setRetryCount((count) => count + 1);
    };
    const loadedCargo = pageState.status === "ready" || pageState.status === "no-decision" ? pageState.cargo : null;
    const verifiedState = loadedCargo && loadedCargo.cargo_request_id === cargoRequestId && loadedCargo.user_id === userId && storedCargoUserId === userId;
    const cargo = verifiedState ? loadedCargo : null;
    const recommendation = verifiedState && pageState.status === "ready" ? pageState.recommendation : null;
    const canPrint = Boolean(recommendation);
    const showLoading = pageState.status === "loading" || Boolean(cargoRequestId && userId && !cargo && pageState.status !== "error");
    const showNoCargo = !cargoRequestId || pageState.status === "no-cargo";

    return (
        <div className="decision-report-page">
            <Sidebar activePage="decision-report" />
            <main className="decision-report-main">
                <Link to="/decision-overview" className="report-back-link"><ArrowLeft size={16} />Back to Decision Overview</Link>
                <header className="report-page-header"><div><span className="report-eyebrow">DECISION REPORT</span><h1>Procurement Decision Report</h1><p>Verified procurement decision summary with supporting cost, risk, and recommendation details.</p></div><div className="report-action-wrap"><button type="button" className="report-download-button" disabled={!canPrint} onClick={() => window.print()}><Download size={16} />{canPrint ? "Print / Save as PDF" : "Report export unavailable"}</button>{!canPrint && <span className="report-export-state">A verified recommendation is required before printing this report.</span>}</div></header>

                <DataProvenance />

                {showLoading && <section className="report-state-card" role="status" aria-live="polite"><FileText size={21} /><div><strong>Verifying report data</strong><p>Checking the active cargo with the backend and looking for an existing recommendation from the current workflow.</p></div></section>}
                {pageState.status === "error" && <section className="report-state-card report-error" role="alert"><AlertCircle size={21} /><div><strong>Report data unavailable</strong><p>{pageState.message}</p><button type="button" className="report-retry-button" onClick={retry}>Retry</button></div></section>}
                {showNoCargo && <section className="report-state-card" role="status"><Ship size={21} /><div><strong>No active cargo request</strong><p>Create a cargo request before viewing a decision report.</p><Link to="/cargo-request">Create Cargo Request</Link></div></section>}
                {pageState.status === "no-decision" && cargo && <section className="report-state-card" role="status"><Info size={21} /><div><strong>No existing decision available</strong><p>The cargo was verified, but no valid recommendation is saved for this user and cargo request.</p><Link to="/decision-overview">Open Decision Overview</Link></div></section>}

                {cargo && <section className="report-section"><div className="report-section-header"><div><h2>Cargo Request Summary</h2><p>Values refreshed from the backend for this report.</p></div></div><div className="report-summary-grid"><div><span>Commodity</span><strong>{cargo.commodity.replace(/_/g, " ")}</strong></div><div><span>Cargo Volume</span><strong>{cargo.cargo_volume_mt.toLocaleString("en-US", { maximumFractionDigits: 20 })} MT</strong></div><div><span>Origin Port</span><strong>{cargo.origin_port_id}</strong></div><div><span>Destination Port</span><strong>{cargo.destination_port_id}</strong></div><div><span>Delivery Window</span><strong>{cargo.earliest_delivery_date} → {cargo.latest_delivery_date}</strong></div><div><span>Contract Horizon</span><strong>{cargo.contract_horizon.replace(/_/g, " ")}</strong></div></div></section>}

                {recommendation && <>
                    <section className="report-section"><div className="report-section-header"><div><h2>Decision Summary</h2><p>Recommendation values returned by the backend.</p></div></div><div className="report-output-grid"><div className="report-output-card"><div className="report-output-icon"><TrendingUp size={18} /></div><span>Market Entry Action</span><strong>{recommendation.market_entry_action}</strong></div><div className="report-output-card"><div className="report-output-icon"><Ship size={18} /></div><span>Recommended Vessel</span><strong>{recommendation.recommended_vessel_class_id}</strong></div><div className="report-output-card"><div className="report-output-icon"><BarChart3 size={18} /></div><span>Expected Total Cost</span><strong>{formatMoney(recommendation.expected_total_cost)}</strong></div><div className="report-output-card"><div className="report-output-icon"><AlertTriangle size={18} /></div><span>Risk / Confidence</span><strong>{recommendation.risk_level} / {recommendation.confidence}</strong></div></div></section>
                    <section className="report-recommendation-card"><div className="report-recommendation-header"><div className="report-recommendation-icon"><CheckCircle2 size={20} /></div><div><h2>Final Recommendation</h2><p>{recommendation.contract_strategy.replace(/_/g, " ")} contract strategy</p></div><span className="report-confidence">Confidence: {recommendation.confidence}</span></div><div className="report-recommendation-content"><strong>{recommendation.market_entry_action} · {recommendation.recommended_vessel_class_id}</strong><div className="report-recommendation-facts"><div><span>Expected freight cost</span><strong>{formatMoney(recommendation.expected_freight_cost)}</strong></div><div><span>Expected total cost</span><strong>{formatMoney(recommendation.expected_total_cost)}</strong></div><div><span>Estimated turnaround</span><strong>{Number(recommendation.estimated_turnaround_hours).toFixed(2)} h</strong></div><div><span>Risk</span><strong>{recommendation.risk_level}</strong></div><div><span>Recommendation created</span><strong>{formatTimestamp(recommendation.created_at)}</strong></div></div><p>{recommendation.rationale}</p></div></section>
                    <section className="report-information-grid"><div className="report-information-card"><div className="report-information-title"><Info size={18} /><h2>Assumptions</h2></div><ul className="report-assumptions-list">{formatAssumptions(recommendation.assumptions).map((assumption, index) => <li key={`${index}-${assumption}`}>{assumption}</li>)}</ul></div><div className="report-information-card report-record-card"><div className="report-information-title"><Info size={18} /><h2>Recommendation Record</h2></div><div className="report-info-row"><span>Recommendation ID</span><strong>{recommendation.recommendation_id}</strong></div><div className="report-info-row"><span>Forecast Run ID</span><strong>{recommendation.forecast_run_id}</strong></div><div className="report-info-row"><span>Cargo Request ID</span><strong>{recommendation.cargo_request_id}</strong></div><div className="report-info-row"><span>Created at</span><strong>{formatTimestamp(recommendation.created_at)}</strong></div></div></section>
                </>}
            </main>
        </div>
    );
}

export default DecisionReport;
