import { useEffect, useRef, useState } from "react";
import { AlertCircle, AlertTriangle, ArrowRight, BarChart3, CheckCircle2, RefreshCw, Ship, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import { useCargoRequest } from "../hooks/useCargoRequest";
import { apiRequest, getRoleDescription, getRoleLabel, useAuthenticatedUser } from "../services/api";
import { createRecommendation } from "../services/recommendation";
import type { CargoRequestResponse } from "../types/cargo";
import type { RecommendationResult } from "../types/recommendation";
import "./Dashboard.css";

type DashboardData = { cargo: CargoRequestResponse; recommendation: RecommendationResult };
type DashboardState =
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "empty" }
    | { status: "ready"; data: DashboardData };

function formatMoney(value: number | string) {
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(Number(value));
}

function Dashboard() {
    const storedCargo = useCargoRequest();
    const user = useAuthenticatedUser();
    const cargoRequestId = storedCargo?.cargo_request_id;
    const storedCargoUserId = storedCargo?.user_id;
    const userId = user?.user_id;
    const [retryCount, setRetryCount] = useState(0);
    const [pageState, setPageState] = useState<DashboardState>(cargoRequestId ? { status: "loading" } : { status: "empty" });
    const requestRef = useRef<{ key: string; promise: Promise<DashboardData> } | null>(null);

    useEffect(() => {
        if (!cargoRequestId || !storedCargoUserId || !userId) return;
        let active = true;
        const key = `${userId}:${cargoRequestId}`;
        let request = requestRef.current?.key === key ? requestRef.current.promise : null;
        if (!request) {
            request = (async () => {
                if (storedCargoUserId !== userId) throw new Error("The saved cargo request does not belong to the signed-in user.");
                const cargo = await apiRequest<CargoRequestResponse>(`/api/v1/cargo-requests/${encodeURIComponent(cargoRequestId)}`);
                if (cargo.cargo_request_id !== cargoRequestId || cargo.user_id !== userId) {
                    throw new Error("The backend cargo request could not be verified for this user.");
                }
                const recommendation = await createRecommendation(cargoRequestId);
                if (recommendation.cargo_request_id !== cargoRequestId) {
                    throw new Error("The backend recommendation does not match the active cargo request.");
                }
                return { cargo, recommendation };
            })();
            requestRef.current = { key, promise: request };
            void request.catch(() => {
                if (requestRef.current?.promise === request) requestRef.current = null;
            });
        }

        void request.then((data) => {
            if (active) setPageState({ status: "ready", data });
        }).catch((error: unknown) => {
            if (active) setPageState({ status: "error", message: error instanceof Error ? error.message : "Unable to load the cargo decision." });
        });
        return () => { active = false; };
    }, [cargoRequestId, storedCargoUserId, retryCount, userId]);

    const retry = () => {
        requestRef.current = null;
        setPageState({ status: "loading" });
        setRetryCount((count) => count + 1);
    };

    const loadedData = pageState.status === "ready" ? pageState.data : null;
    const data = loadedData && loadedData.cargo.cargo_request_id === cargoRequestId && loadedData.cargo.user_id === userId && storedCargoUserId === userId
        ? loadedData
        : null;
    const cargo = data?.cargo;
    const recommendation = data?.recommendation;
    const showEmptyCargo = pageState.status === "empty" || !cargoRequestId || !userId;

    return (
        <div className="dashboard-page">
            <Sidebar activePage="dashboard" />
            <main className="dashboard-main">
                <header className="dashboard-header">
                    <div><span className="dashboard-eyebrow">DECISION SUPPORT</span><h1>Freight Intelligence Dashboard</h1><p>Review verified cargo and the backend recommendation for its decision workflow.</p></div>
                    <Link to="/cargo-request" className="dashboard-primary-button">New Cargo Request<ArrowRight size={17} /></Link>
                </header>

                {user && <section className="dashboard-profile-card" aria-label="Your profile"><div><span className="dashboard-eyebrow">YOUR PROFILE</span><h2>Welcome, {user.name}</h2><p>{user.email}</p></div><div className="dashboard-profile-role"><strong>Your role: {getRoleLabel(user.role)}</strong><p>{getRoleDescription(user.role)}</p></div></section>}

                <section className="dashboard-section">
                    <div className="dashboard-section-heading"><div><h2>Decision Workflow</h2><p>Follow the procurement decision from cargo input to recommendation.</p></div></div>
                    <div className="dashboard-workflow">
                        <Link to="/cargo-request" className="workflow-card workflow-active"><div className="workflow-icon"><Ship size={20} /></div><div><span>01</span><h3>Cargo Request</h3><p>Define cargo requirements</p></div></Link>
                        <div className="workflow-arrow"><ArrowRight size={18} /></div>
                        <Link to="/vessel-options" className="workflow-card"><div className="workflow-icon"><CheckCircle2 size={20} /></div><div><span>02</span><h3>Feasibility</h3><p>Evaluate vessel feasibility</p></div></Link>
                        <div className="workflow-arrow"><ArrowRight size={18} /></div>
                        <Link to="/freight-forecast" className="workflow-card"><div className="workflow-icon"><TrendingUp size={20} /></div><div><span>03</span><h3>Forecast</h3><p>Review freight outlook</p></div></Link>
                        <div className="workflow-arrow"><ArrowRight size={18} /></div>
                        <Link to="/decision-overview" className="workflow-card"><div className="workflow-icon"><BarChart3 size={20} /></div><div><span>04</span><h3>Decision</h3><p>Review cost and risk</p></div></Link>
                    </div>
                </section>

                <section className="dashboard-section">
                    <div className="dashboard-section-heading"><div><h2>Current Decision Status</h2><p>{recommendation ? "Values returned for the verified cargo request." : "Decision values are shown after the backend workflow completes."}</p></div></div>
                    {pageState.status === "loading" && <div className="dashboard-request-state" role="status" aria-live="polite"><RefreshCw className="dashboard-spinner" size={22} /><div><strong>Loading current decision</strong><p>Verifying cargo ownership and requesting the backend recommendation.</p></div></div>}
                    {pageState.status === "error" && <div className="dashboard-request-state dashboard-request-error" role="alert"><AlertCircle size={22} /><div><strong>Decision unavailable</strong><p>{pageState.message}</p><button type="button" className="dashboard-secondary-button dashboard-retry-button" onClick={retry}>Retry</button></div></div>}
                    {showEmptyCargo && pageState.status !== "loading" && pageState.status !== "error" && <div className="dashboard-request-state" role="status"><Ship size={22} /><div><strong>No active cargo request</strong><p>Create a cargo request to load a verified decision.</p><Link to="/cargo-request" className="dashboard-secondary-button">Create Cargo Request<ArrowRight size={16} /></Link></div></div>}
                    {data && <div className="dashboard-summary-grid">
                        <div className="dashboard-summary-card"><div className="summary-card-top"><div className="summary-card-icon"><TrendingUp size={19} /></div><span className="summary-status">Backend result</span></div><span className="summary-label">Market Entry Action</span><strong>{recommendation?.market_entry_action}</strong><p>Recommendation for this cargo request.</p></div>
                        <div className="dashboard-summary-card"><div className="summary-card-top"><div className="summary-card-icon"><Ship size={19} /></div><span className="summary-status">Backend result</span></div><span className="summary-label">Recommended Vessel</span><strong>{recommendation?.recommended_vessel_class_id}</strong><p>Selected vessel class returned by the recommendation.</p></div>
                        <div className="dashboard-summary-card"><div className="summary-card-top"><div className="summary-card-icon"><BarChart3 size={19} /></div><span className="summary-status">Backend result</span></div><span className="summary-label">Expected Total Cost</span><strong>{recommendation && formatMoney(recommendation.expected_total_cost)}</strong><p>USD, returned by the recommendation.</p></div>
                        <div className="dashboard-summary-card"><div className="summary-card-top"><div className="summary-card-icon"><AlertTriangle size={19} /></div><span className="summary-status">Backend result</span></div><span className="summary-label">Risk / Confidence</span><strong>{recommendation?.risk_level} / {recommendation?.confidence}</strong><p>Categorical values returned by the recommendation.</p></div>
                    </div>}
                </section>

                {cargo && <section className="dashboard-empty-state"><div className="dashboard-empty-icon"><Ship size={25} /></div><h2>Verified Cargo Request</h2><p>{cargo.commodity.replace(/_/g, " ")} · {cargo.cargo_volume_mt} MT · {cargo.origin_port_id} → {cargo.destination_port_id}</p><Link to="/decision-overview" className="dashboard-secondary-button">View Decision Overview<ArrowRight size={16} /></Link></section>}
            </main>
        </div>
    );
}

export default Dashboard;
