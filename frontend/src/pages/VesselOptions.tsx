import { useEffect, useRef, useState } from "react";
import {
    AlertCircle,
    ArrowLeft,
    CheckCircle2,
    Ship,
} from "lucide-react";
import { Link } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import { useWorkflowState } from "../context/WorkflowStateContext";
import type { WorkflowFeasibility, WorkflowScope, WorkflowVessel } from "../context/WorkflowStateContext";
import { useCargoRequest } from "../hooks/useCargoRequest";
import { apiRequest, startPageLoadTiming, useAuthenticatedUser } from "../services/api";
import type { CargoRequestResponse } from "../types/cargo";
import "./VesselOptions.css";

type VesselClass = WorkflowVessel;
type FeasibilityResult = WorkflowFeasibility;

type VesselOption = {
    vessel: VesselClass;
    feasibility: FeasibilityResult;
};

type PageState =
    | { status: "loading" }
    | { status: "success"; cargo: CargoRequestResponse; options: VesselOption[] }
    | { status: "error"; message: string }
    | { status: "empty" };

function isVesselList(value: unknown): value is VesselClass[] {
    return Array.isArray(value) && value.every((vessel) =>
        typeof vessel === "object" && vessel !== null &&
        typeof vessel.vessel_class_id === "string" && vessel.vessel_class_id.trim().length > 0 &&
        typeof vessel.vessel_class_name === "string" &&
        typeof vessel.dwt_min_mt === "number" && Number.isFinite(vessel.dwt_min_mt) &&
        typeof vessel.dwt_max_mt === "number" && Number.isFinite(vessel.dwt_max_mt) &&
        typeof vessel.loa_m === "number" && Number.isFinite(vessel.loa_m) &&
        typeof vessel.beam_m === "number" && Number.isFinite(vessel.beam_m) &&
        typeof vessel.draft_m === "number" && Number.isFinite(vessel.draft_m) &&
        typeof vessel.speed_knots === "number" && Number.isFinite(vessel.speed_knots) &&
        typeof vessel.cargo_capacity_mt === "number" && Number.isFinite(vessel.cargo_capacity_mt) &&
        typeof vessel.fuel_consumption_mt_day === "number" && Number.isFinite(vessel.fuel_consumption_mt_day) &&
        typeof vessel.source === "string" && typeof vessel.data_type === "string",
    );
}

function isReusableCargo(value: CargoRequestResponse | null, userId: string, cargoRequestId: string): value is CargoRequestResponse {
    return Boolean(value && value.user_id === userId && value.cargo_request_id === cargoRequestId &&
        typeof value.commodity === "string" && typeof value.cargo_volume_mt === "number" &&
        Number.isFinite(value.cargo_volume_mt) && typeof value.origin_port_id === "string" &&
        typeof value.destination_port_id === "string");
}

function isValidFeasibility(
    value: FeasibilityResult | null,
    vessel: VesselClass,
    cargo: CargoRequestResponse,
): value is FeasibilityResult {
    return Boolean(value && typeof value.is_feasible === "boolean" && typeof value.status === "string" &&
        value.vessel_class_id === vessel.vessel_class_id &&
        value.origin_port_id === cargo.origin_port_id && value.destination_port_id === cargo.destination_port_id &&
        value.commodity === cargo.commodity && value.cargo_volume_mt === cargo.cargo_volume_mt &&
        (value.required_voyages === null || (typeof value.required_voyages === "number" && Number.isFinite(value.required_voyages))) &&
        (value.rejection_reason_code === null || typeof value.rejection_reason_code === "string") &&
        (value.rejection_reason === null || typeof value.rejection_reason === "string"));
}

function VesselOptions() {
    const storedCargo = useCargoRequest();
    const user = useAuthenticatedUser();
    const cargoRequestId = storedCargo?.cargo_request_id;
    const cargoUserId = user?.user_id;
    const workflow = useWorkflowState();
    const workflowRef = useRef(workflow);
    const [retryCount, setRetryCount] = useState(0);
    const [pageState, setPageState] = useState<PageState>(
        cargoRequestId ? { status: "loading" } : { status: "empty" },
    );
    const loadOperationRef = useRef<{ key: string; promise: Promise<{ cargo: CargoRequestResponse; options: VesselOption[] }> } | null>(null);

    useEffect(() => {
        workflowRef.current = workflow;
    }, [workflow]);

    useEffect(() => {
        if (!cargoRequestId || !cargoUserId) return;

        let active = true;
        const workflowState = workflowRef.current;
        const scope: WorkflowScope = { userId: cargoUserId, cargoRequestId };
        workflowState.setActiveScope(cargoUserId, cargoRequestId);
        const finishTiming = startPageLoadTiming("Vessel Options");
        const loadOptions = async (): Promise<{ cargo: CargoRequestResponse; options: VesselOption[] }> => {
            const cachedCargo = workflowState.getVerifiedCargo(scope);
            let cargo: CargoRequestResponse;
            if (isReusableCargo(cachedCargo, cargoUserId, cargoRequestId)) {
                cargo = cachedCargo;
            } else {
                cargo = await apiRequest<CargoRequestResponse>(
                    `/api/v1/cargo-requests/${encodeURIComponent(cargoRequestId)}`,
                );
            }
            if (
                cargo.cargo_request_id !== cargoRequestId ||
                cargo.user_id !== cargoUserId
            ) {
                throw new Error("The active cargo request could not be verified.");
            }
            if (!isReusableCargo(cachedCargo, cargoUserId, cargoRequestId) &&
                isReusableCargo(cargo, cargoUserId, cargoRequestId)) {
                workflowState.setVerifiedCargo(scope, cargo);
            }

            const cachedVessels = workflowState.getVessels(scope);
            let vessels = isVesselList(cachedVessels) ? cachedVessels : null;
            if (!vessels) {
                const response = await apiRequest<VesselClass[]>("/api/v1/vessels");
                if (!isVesselList(response)) {
                    throw new Error("The backend returned invalid vessel reference data.");
                }
                vessels = response;
                workflowState.setVessels(scope, vessels);
            }

            const options = await Promise.all(vessels.map(async (vessel) => {
                const cachedFeasibility = workflowState.getFeasibility(scope, vessel.vessel_class_id);
                let feasibility = isValidFeasibility(cachedFeasibility, vessel, cargo)
                    ? cachedFeasibility
                    : null;
                if (!feasibility) {
                    const response = await apiRequest<FeasibilityResult>(
                        "/api/v1/feasibility",
                        {
                            method: "POST",
                            body: JSON.stringify({
                                origin_port_id: cargo.origin_port_id,
                                destination_port_id: cargo.destination_port_id,
                                commodity: cargo.commodity,
                                vessel_class_id: vessel.vessel_class_id,
                                cargo_volume_mt: cargo.cargo_volume_mt,
                            }),
                        },
                    );
                    feasibility = response;
                }
                if (
                    feasibility.vessel_class_id !== vessel.vessel_class_id ||
                    feasibility.origin_port_id !== cargo.origin_port_id ||
                    feasibility.destination_port_id !== cargo.destination_port_id ||
                    feasibility.commodity !== cargo.commodity ||
                    feasibility.cargo_volume_mt !== cargo.cargo_volume_mt
                ) {
                    throw new Error(`Feasibility response did not match ${vessel.vessel_class_id} and the active cargo request.`);
                }
                if (!isValidFeasibility(cachedFeasibility, vessel, cargo) &&
                    isValidFeasibility(feasibility, vessel, cargo)) {
                    workflowState.setFeasibility(scope, vessel.vessel_class_id, feasibility);
                }
                return { vessel, feasibility };
            }));

            return { cargo, options };
        };

        const operationKey = `${cargoUserId}:${cargoRequestId}:${retryCount}`;
        let operation = loadOperationRef.current?.key === operationKey
            ? loadOperationRef.current.promise
            : null;
        if (!operation) {
            operation = loadOptions();
            loadOperationRef.current = { key: operationKey, promise: operation };
        }

        void operation.then(({ cargo, options }) => {
            if (active) setPageState({ status: "success", cargo, options });
        }).catch((loadError: unknown) => {
            if (active) {
                setPageState({
                    status: "error",
                    message: loadError instanceof Error
                        ? loadError.message
                        : "Unable to load vessel feasibility. Please try again.",
                });
            }
        }).finally(() => {
            if (loadOperationRef.current?.key === operationKey) loadOperationRef.current = null;
            finishTiming();
        });

        return () => { active = false; };
    }, [cargoRequestId, cargoUserId, retryCount]);

    const retry = () => {
        if (cargoRequestId && cargoUserId) {
            const scope = { userId: cargoUserId, cargoRequestId };
            const knownVessels = workflowRef.current.getVessels(scope);
            workflowRef.current.invalidateWorkflowEntry({ type: "verifiedCargo" });
            workflowRef.current.invalidateWorkflowEntry({ type: "vessels" });
            if (isVesselList(knownVessels)) {
                knownVessels.forEach((vessel) => {
                    workflowRef.current.invalidateWorkflowEntry({
                        type: "feasibility",
                        vesselClassId: vessel.vessel_class_id,
                    });
                });
            }
        }
        setPageState({ status: "loading" });
        setRetryCount((count) => count + 1);
    };

    const cargo = pageState.status === "success" ? pageState.cargo : null;
    const options = pageState.status === "success" ? pageState.options : [];
    const feasibleCount = options.filter(({ feasibility }) => feasibility.is_feasible).length;
    const noActiveCargo = !cargoRequestId || !cargoUserId;

    return (
        <div className="vessel-options-page">
            <Sidebar activePage="vessel-options" />

            <main className="vessel-options-main">
                <Link to="/decision-overview" className="vessel-back-link">
                    <ArrowLeft size={16} />
                    Back to Decision Overview
                </Link>

                <header className="vessel-page-header">
                    <div>
                        <span className="vessel-eyebrow">VESSEL FEASIBILITY</span>
                        <h1>Vessel Options</h1>
                        <p>Compare backend feasibility results for the active cargo request.</p>
                    </div>
                    <div className="vessel-status" role={pageState.status === "error" ? "alert" : undefined}>
                        <span className="vessel-status-dot"></span>
                        {pageState.status === "loading" ? "Loading vessels" :
                            pageState.status === "success" ? `${feasibleCount} feasible` :
                                pageState.status === "error" ? "Unable to load" : "No active request"}
                    </div>
                </header>

                {pageState.status === "empty" || noActiveCargo ? (
                    <section className="vessel-table-card">
                        <div className="vessel-empty-state" role="status">
                            <div className="vessel-empty-icon"><Ship size={25} /></div>
                            <h3>No active cargo request</h3>
                            <p>Create a cargo request before comparing vessel feasibility.</p>
                            <Link to="/cargo-request">Create Cargo Request</Link>
                        </div>
                    </section>
                ) : pageState.status === "error" ? (
                    <section className="vessel-table-card">
                        <div className="vessel-empty-state" role="alert">
                            <div className="vessel-empty-icon"><AlertCircle size={25} /></div>
                            <h3>Vessel feasibility unavailable</h3>
                            <p>{pageState.message}</p>
                            <button type="button" onClick={retry}>Retry</button>
                        </div>
                    </section>
                ) : (
                    <>
                        {pageState.status === "success" && (
                            <section className="vessel-request-card">
                                <div className="vessel-request-icon"><Ship size={19} /></div>
                                <div>
                                    <span>Verified Cargo Request</span>
                                    <strong>{cargo?.commodity.replace(/_/g, " ")}</strong>
                                    <p>{cargo?.cargo_volume_mt} MT · {cargo?.origin_port_id} → {cargo?.destination_port_id}</p>
                                </div>
                            </section>
                        )}

                        <section className="vessel-table-card">
                            <div className="vessel-card-header">
                                <div>
                                    <h2>Vessel Feasibility</h2>
                                    <p>Feasibility is evaluated separately for each canonical vessel class.</p>
                                </div>
                                <span className="vessel-count">
                                    {pageState.status === "loading" ? "Loading…" : `${options.length} options · ${feasibleCount} feasible`}
                                </span>
                            </div>

                            {pageState.status === "loading" ? (
                                <div className="vessel-empty-state" role="status" aria-live="polite">
                                    <div className="vessel-empty-icon"><Ship size={25} /></div>
                                    <h3>Loading vessel options</h3>
                                    <p>Verifying cargo and evaluating canonical vessel classes.</p>
                                </div>
                            ) : options.length === 0 ? (
                                <div className="vessel-empty-state" role="status">
                                    <div className="vessel-empty-icon"><Ship size={25} /></div>
                                    <h3>No vessel classes available</h3>
                                    <p>The backend returned no vessel reference records.</p>
                                </div>
                            ) : (
                                <div className="vessel-table-wrapper">
                                    <table className="vessel-comparison-table">
                                        <thead>
                                            <tr>
                                                <th>Vessel Class</th>
                                                <th>Feasibility</th>
                                                <th>Rejection Reason</th>
                                                <th>Capacity</th>
                                                <th>Required Voyages</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {options.map(({ vessel, feasibility }) => (
                                                <tr key={vessel.vessel_class_id}>
                                                    <td>{vessel.vessel_class_name}<br /><small>{vessel.vessel_class_id}</small><br /><small>{vessel.source} · {vessel.data_type}</small></td>
                                                    <td>{feasibility.status}</td>
                                                    <td>{feasibility.rejection_reason || "—"}{feasibility.rejection_reason_code && <><br /><small>{feasibility.rejection_reason_code}</small></>}</td>
                                                    <td>{vessel.cargo_capacity_mt.toLocaleString()} MT</td>
                                                    <td>{feasibility.required_voyages ?? "—"}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </section>
                    </>
                )}

                <section className="vessel-info-grid">
                    <div className="vessel-info-card">
                        <div className="vessel-info-title"><CheckCircle2 size={18} /><h2>Feasibility Checks</h2></div>
                        <p>The backend evaluates the vessel class against the cargo, commodity, origin, and destination.</p>
                    </div>
                </section>
            </main>
        </div>
    );
}

export default VesselOptions;
