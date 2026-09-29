import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { ArrowLeft, ArrowRight, CalendarDays } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import { apiRequest } from "../services/api";
import "./CargoRequest.css";
import type {
    CargoRequestCreate,
    CargoRequestResponse,
    CommodityType,
    ContractHorizon,
} from "../types/cargo";

type PortOption = {
    port_id: string;
    port_name: string;
};

type CargoField =
    | "commodity"
    | "cargoVolume"
    | "originPort"
    | "destinationPort"
    | "deliveryStart"
    | "deliveryEnd"
    | "contractHorizon";

function CargoRequest() {
    const navigate = useNavigate();
    const [commodity, setCommodity] = useState<CommodityType | "">("");
    const [cargoVolume, setCargoVolume] = useState("");
    const [originPort, setOriginPort] = useState("");
    const [destinationPort, setDestinationPort] = useState("");
    const [deliveryStart, setDeliveryStart] = useState("");
    const [deliveryEnd, setDeliveryEnd] = useState("");
    const [contractHorizon, setContractHorizon] = useState<ContractHorizon | "">("");

    const [error, setError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [ports, setPorts] = useState<PortOption[]>([]);
    const [isLoadingPorts, setIsLoadingPorts] = useState(true);
    const [portsError, setPortsError] = useState("");
    const [retryPorts, setRetryPorts] = useState(0);
    const [touched, setTouched] = useState<Partial<Record<CargoField, boolean>>>({});
    const [submitAttempted, setSubmitAttempted] = useState(false);
    const submissionInProgress = useRef(false);

    const validationErrors: Partial<Record<CargoField, string>> = {};
    if (!commodity) validationErrors.commodity = "Please select a commodity.";
    const volume = Number(cargoVolume);
    if (!cargoVolume) {
        validationErrors.cargoVolume = "Please enter the cargo volume.";
    } else if (!Number.isFinite(volume) || volume <= 0) {
        validationErrors.cargoVolume = "Cargo volume must be greater than 0 MT.";
    }
    if (!originPort) validationErrors.originPort = "Please select the origin port.";
    if (!destinationPort) validationErrors.destinationPort = "Please select the destination port.";
    if (originPort && destinationPort && originPort === destinationPort) {
        validationErrors.destinationPort = "Origin port and destination port must be different.";
    }
    if (!deliveryStart) validationErrors.deliveryStart = "Please select the delivery start date.";
    if (!deliveryEnd) {
        validationErrors.deliveryEnd = "Please select the delivery end date.";
    } else if (deliveryStart && deliveryEnd < deliveryStart) {
        validationErrors.deliveryEnd = "Delivery end date cannot be before the delivery start date.";
    }
    if (!contractHorizon) validationErrors.contractHorizon = "Please select the contract horizon.";

    const isFormValid =
        Object.keys(validationErrors).length === 0 &&
        ports.length > 0 &&
        !isLoadingPorts &&
        !portsError;

    useEffect(() => {
        let active = true;
        void apiRequest<PortOption[]>("/api/v1/ports")
            .then((result) => {
                if (!active) return;
                setPorts(result);
                setPortsError("");
            })
            .catch((portsLoadError: unknown) => {
                if (!active) return;
                setPorts([]);
                setPortsError(
                    portsLoadError instanceof Error
                        ? portsLoadError.message
                        : "Unable to load ports. Please try again."
                );
            })
            .finally(() => {
                if (active) setIsLoadingPorts(false);
            });
        return () => { active = false; };
    }, [retryPorts]);

    const markTouched = (field: CargoField) => {
        setTouched((current) => ({ ...current, [field]: true }));
    };

    const fieldError = (field: CargoField) =>
        (touched[field] || submitAttempted) ? validationErrors[field] : undefined;

    const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (submissionInProgress.current) return;
        setSubmitAttempted(true);
        if (!isFormValid || !commodity || !contractHorizon) {
            setError("Please correct the highlighted fields before continuing.");
            return;
        }

        setError("");

        const payload: CargoRequestCreate = {
            commodity,
            cargo_volume_mt: volume,
            origin_port_id: originPort,
            destination_port_id: destinationPort,
            earliest_delivery_date: deliveryStart,
            latest_delivery_date: deliveryEnd,
            contract_horizon: contractHorizon,
        };

        submissionInProgress.current = true;
        setIsSubmitting(true);
        try {
            const created = await apiRequest<CargoRequestResponse>(
                "/api/v1/cargo-requests",
                { method: "POST", body: JSON.stringify(payload) }
            );
            sessionStorage.setItem("docktech-cargo-request", JSON.stringify(created));
            navigate("/decision-overview");
        } catch (submitError) {
            setError(
                submitError instanceof Error
                    ? submitError.message
                    : "Unable to create the cargo request. Please try again."
            );
        } finally {
            submissionInProgress.current = false;
            setIsSubmitting(false);
        }
    };

    return (
        <div className="cargo-request-page">
            <Sidebar activePage="cargo-request" />

            {/* Main */}
            <main className="cargo-request-main">
                <Link to="/dashboard" className="cargo-back-link">
                    <ArrowLeft size={16} />
                    Back to Dashboard
                </Link>

                <section className="cargo-request-intro">
                    <div>
                        <p className="cargo-eyebrow">Cargo Request</p>

                        <h1>Start a Freight Decision</h1>

                        <p>
                            Enter the cargo and delivery requirements to begin the DockTech
                            decision workflow.
                        </p>
                    </div>

                </section>

                {/* Form */}
                <form className="cargo-request-card" onSubmit={handleSubmit}>
                    <div className="cargo-section-heading">
                        <div>
                            <h2>Cargo Requirements</h2>
                            <p>Provide the basic requirements for the procurement request.</p>
                        </div>
                    </div>

                    <div className="cargo-form-grid">
                        {/* Commodity */}
                        <div className="cargo-field">
                            <label htmlFor="commodity">
                                Commodity <span>*</span>
                            </label>

                            <select
                                id="commodity"
                                value={commodity}
                                onBlur={() => markTouched("commodity")}
                                aria-invalid={Boolean(fieldError("commodity"))}
                                onChange={(event) => {
                                    const value = event.target.value;
                                    setCommodity(
                                        value === "THERMAL_COAL" || value === "COKING_COAL"
                                            ? value
                                            : ""
                                    );
                                }}
                            >
                                <option value="">Select commodity</option>
                                <option value="THERMAL_COAL">Thermal Coal</option>
                                <option value="COKING_COAL">Coking Coal</option>
                            </select>
                            {fieldError("commodity") && <small className="cargo-field-error">{fieldError("commodity")}</small>}
                        </div>

                        {/* Cargo Volume */}
                        <div className="cargo-field">
                            <label htmlFor="cargoVolume">
                                Cargo Volume <span>*</span>
                            </label>

                            <div className="cargo-input-with-unit">
                                <input
                                    id="cargoVolume"
                                    type="number"
                                    min="0"
                                    onBlur={() => markTouched("cargoVolume")}
                                    aria-invalid={Boolean(fieldError("cargoVolume"))}
                                    placeholder="Enter volume"
                                    value={cargoVolume}
                                    onChange={(event) => setCargoVolume(event.target.value)}
                                />

                                <span>MT</span>
                            </div>
                            {fieldError("cargoVolume") && <small className="cargo-field-error">{fieldError("cargoVolume")}</small>}
                        </div>

                        {/* Origin */}
                        <div className="cargo-field">
                            <label htmlFor="originPort">
                                Origin Port <span>*</span>
                            </label>

                            <select
                                id="originPort"
                                value={originPort}
                                onBlur={() => markTouched("originPort")}
                                aria-invalid={Boolean(fieldError("originPort"))}
                                onChange={(event) => setOriginPort(event.target.value)}
                                disabled={isLoadingPorts || Boolean(portsError) || ports.length === 0}
                            >
                                <option value="">
                                    {isLoadingPorts ? "Loading ports…" : portsError ? "Ports unavailable" : ports.length === 0 ? "No ports available" : "Select origin port"}
                                </option>
                                {ports.map((port) => <option key={port.port_id} value={port.port_id}>{port.port_name}</option>)}
                            </select>
                            {fieldError("originPort") && <small className="cargo-field-error">{fieldError("originPort")}</small>}
                        </div>

                        {/* Destination */}
                        <div className="cargo-field">
                            <label htmlFor="destinationPort">
                                Destination Port <span>*</span>
                            </label>

                            <select
                                id="destinationPort"
                                value={destinationPort}
                                onBlur={() => markTouched("destinationPort")}
                                aria-invalid={Boolean(fieldError("destinationPort"))}
                                onChange={(event) =>
                                    setDestinationPort(event.target.value)
                                }
                                disabled={isLoadingPorts || Boolean(portsError) || ports.length === 0}
                            >
                                <option value="">
                                    {isLoadingPorts ? "Loading ports…" : portsError ? "Ports unavailable" : ports.length === 0 ? "No ports available" : "Select destination port"}
                                </option>
                                {ports.map((port) => <option key={port.port_id} value={port.port_id}>{port.port_name}</option>)}
                            </select>
                            {fieldError("destinationPort") && <small className="cargo-field-error">{fieldError("destinationPort")}</small>}
                        </div>
                    </div>

                    {(portsError || (!isLoadingPorts && ports.length === 0)) && (
                        <div className="cargo-form-error" role="alert">
                            <span>{portsError || "No ports are currently available."}</span>
                            {portsError && (
                                <button type="button" onClick={() => {
                                    setIsLoadingPorts(true);
                                    setPortsError("");
                                    setRetryPorts((count) => count + 1);
                                }}>
                                    Retry loading ports
                                </button>
                            )}
                        </div>
                    )}
                    {isLoadingPorts && <p className="cargo-port-loading" role="status">Loading canonical ports…</p>}

                    {/* Delivery Window */}
                    <div className="cargo-subsection">
                        <div className="cargo-subsection-heading">
                            <CalendarDays size={18} />

                            <div>
                                <h3>Delivery Window</h3>
                                <p>Define when the cargo needs to be delivered.</p>
                            </div>
                        </div>

                        <div className="cargo-form-grid">
                            <div className="cargo-field">
                                <label htmlFor="deliveryStart">
                                    Delivery Start <span>*</span>
                                </label>

                            <input
                                id="deliveryStart"
                                type="date"
                                value={deliveryStart}
                                onBlur={() => markTouched("deliveryStart")}
                                aria-invalid={Boolean(fieldError("deliveryStart"))}
                                    onChange={(event) =>
                                        setDeliveryStart(event.target.value)
                                    }
                                />
                                {fieldError("deliveryStart") && <small className="cargo-field-error">{fieldError("deliveryStart")}</small>}
                            </div>

                            <div className="cargo-field">
                                <label htmlFor="deliveryEnd">
                                    Delivery End <span>*</span>
                                </label>

                                <input
                                    id="deliveryEnd"
                                    type="date"
                                    value={deliveryEnd}
                                    onBlur={() => markTouched("deliveryEnd")}
                                    aria-invalid={Boolean(fieldError("deliveryEnd"))}
                                    onChange={(event) => setDeliveryEnd(event.target.value)}
                                />
                                {fieldError("deliveryEnd") && <small className="cargo-field-error">{fieldError("deliveryEnd")}</small>}
                            </div>
                        </div>
                    </div>

                    {/* Contract Horizon */}
                    <div className="cargo-subsection">
                        <div className="cargo-field cargo-contract-field">
                            <label htmlFor="contractHorizon">
                                Contract Horizon <span>*</span>
                            </label>

                            <select
                                id="contractHorizon"
                                value={contractHorizon}
                                onBlur={() => markTouched("contractHorizon")}
                                aria-invalid={Boolean(fieldError("contractHorizon"))}
                                onChange={(event) => {
                                    const value = event.target.value;
                                    setContractHorizon(
                                        value === "SPOT" || value === "SHORT_TERM" || value === "FLEXIBLE"
                                            ? value
                                            : ""
                                    );
                                }}
                            >
                                <option value="">Select contract horizon</option>
                                <option value="SPOT">Spot</option>
                                <option value="SHORT_TERM">Short Term</option>
                                <option value="FLEXIBLE">Flexible</option>
                            </select>
                            {fieldError("contractHorizon") && <small className="cargo-field-error">{fieldError("contractHorizon")}</small>}

                            <small>
                                Select the procurement horizon for this cargo requirement.
                            </small>
                        </div>
                    </div>

                    {/* Error */}
                    {error && (
                        <div className="cargo-form-error" role="alert">
                            {error}
                        </div>
                    )}

                    {/* Actions */}
                    <div className="cargo-form-actions">
                        <Link to="/dashboard" className="cargo-cancel-button">
                            Cancel
                        </Link>

                        <button type="submit" className="cargo-submit-button" disabled={!isFormValid || isSubmitting}>
                            {isSubmitting ? "Submitting…" : "Continue to Decision"}
                            {!isSubmitting && <ArrowRight size={17} />}
                        </button>
                    </div>
                </form>
            </main>
        </div>
    );
}

export default CargoRequest;
