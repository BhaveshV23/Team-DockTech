import { useEffect, useState } from "react";
import {
    AlertCircle,
    ArrowLeft,
    CheckCircle2,
    Ship,
} from "lucide-react";
import { Link } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import DataProvenance from "../components/DataProvenance";
import { useCargoRequest } from "../hooks/useCargoRequest";
import { apiRequest } from "../services/api";
import type { CargoRequestResponse } from "../types/cargo";
import "./VesselOptions.css";

type VesselClass = {
    vessel_class_id: string;
    vessel_class_name: string;
    dwt_min_mt: number;
    dwt_max_mt: number;
    loa_m: number;
    beam_m: number;
    draft_m: number;
    speed_knots: number;
    cargo_capacity_mt: number;
    fuel_consumption_mt_day: number;
    source: string;
    data_type: string;
};

type FeasibilityResult = {
    is_feasible: boolean;
    status: string;
    vessel_class_id: string;
    origin_port_id: string;
    destination_port_id: string;
    commodity: string;
    cargo_volume_mt: number;
    required_voyages: number | null;
    rejection_reason_code: string | null;
    rejection_reason: string | null;
};

type VesselOption = {
    vessel: VesselClass;
    feasibility: FeasibilityResult;
};

type PageState =
    | { status: "loading" }
    | { status: "success"; cargo: CargoRequestResponse; options: VesselOption[] }
    | { status: "error"; message: string }
    | { status: "empty" };

function VesselOptions() {
    const storedCargo = useCargoRequest();
    const cargoRequestId = storedCargo?.cargo_request_id;
    const cargoUserId = storedCargo?.user_id;
    const [retryCount, setRetryCount] = useState(0);
    const [pageState, setPageState] = useState<PageState>(
        cargoRequestId ? { status: "loading" } : { status: "empty" },
    );

    useEffect(() => {
        if (!cargoRequestId || !cargoUserId) return;

        let active = true;
        const loadOptions = async () => {
            const cargo = await apiRequest<CargoRequestResponse>(
                `/api/v1/cargo-requests/${encodeURIComponent(cargoRequestId)}`,
            );
            if (
                cargo.cargo_request_id !== cargoRequestId ||
                cargo.user_id !== cargoUserId
            ) {
                throw new Error("The active cargo request could not be verified.");
            }

            const vessels = await apiRequest<VesselClass[]>("/api/v1/vessels");
            const options = await Promise.all(vessels.map(async (vessel) => {
                const feasibility = await apiRequest<FeasibilityResult>(
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
                if (
                    feasibility.vessel_class_id !== vessel.vessel_class_id ||
                    feasibility.origin_port_id !== cargo.origin_port_id ||
                    feasibility.destination_port_id !== cargo.destination_port_id ||
                    feasibility.commodity !== cargo.commodity ||
                    feasibility.cargo_volume_mt !== cargo.cargo_volume_mt
                ) {
                    throw new Error(`Feasibility response did not match ${vessel.vessel_class_id} and the active cargo request.`);
                }
                return { vessel, feasibility };
            }));

            return { cargo, options };
        };

        void loadOptions().then(({ cargo, options }) => {
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
        });

        return () => { active = false; };
    }, [cargoRequestId, cargoUserId, retryCount]);

    const retry = () => {
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

                <DataProvenance />

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
