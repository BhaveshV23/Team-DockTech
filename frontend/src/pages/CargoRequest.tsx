import { useState } from "react";
import type { FormEvent } from "react";
import { ArrowLeft, ArrowRight, CalendarDays } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import "./CargoRequest.css";
import type { CargoRequest as CargoRequestData } from "../types/cargo";

function CargoRequest() {
    const navigate = useNavigate();
    const [commodity, setCommodity] = useState("");
    const [cargoVolume, setCargoVolume] = useState("");
    const [originPort, setOriginPort] = useState("");
    const [destinationPort, setDestinationPort] = useState("");
    const [deliveryStart, setDeliveryStart] = useState("");
    const [deliveryEnd, setDeliveryEnd] = useState("");
    const [contractHorizon, setContractHorizon] = useState("");

    const [error, setError] = useState("");

    const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();

        // 1. Required fields
        if (!commodity) {
            setError("Please select a commodity.");
            return;
        }

        if (!cargoVolume) {
            setError("Please enter the cargo volume.");
            return;
        }

        if (!originPort.trim()) {
            setError("Please enter the origin port.");
            return;
        }

        if (!destinationPort.trim()) {
            setError("Please enter the destination port.");
            return;
        }

        if (!deliveryStart) {
            setError("Please select the delivery start date.");
            return;
        }

        if (!deliveryEnd) {
            setError("Please select the delivery end date.");
            return;
        }

        if (!contractHorizon) {
            setError("Please select the contract horizon.");
            return;
        }

        // 2. Cargo volume validation
        const volume = Number(cargoVolume);

        if (!Number.isFinite(volume) || volume <= 0) {
            setError("Cargo volume must be greater than 0 MT.");
            return;
        }

        // 3. Delivery date validation
        const startDate = new Date(`${deliveryStart}T00:00:00`);
        const endDate = new Date(`${deliveryEnd}T00:00:00`);

        if (endDate < startDate) {
            setError("Delivery end date cannot be before the delivery start date.");
            return;
        }

        // 4. Everything is valid
        setError("");

        const cargoRequest: CargoRequestData = {
            commodity,
            cargoVolume: volume,
            originPort: originPort.trim(),
            destinationPort: destinationPort.trim(),
            deliveryStartDate: deliveryStart,
            deliveryEndDate: deliveryEnd,
            contractHorizon:
                contractHorizon as CargoRequestData["contractHorizon"],
        };

        sessionStorage.setItem(
            "docktech-cargo-request",
            JSON.stringify(cargoRequest)
        );

        navigate("/decision-overview");
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

                    <div className="cargo-step-indicator">
                        <span className="cargo-step-active">01</span>
                        <span>Cargo Input</span>
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
                                onChange={(event) => setCommodity(event.target.value)}
                            >
                                <option value="">Select commodity</option>
                                <option value="iron_ore">Iron Ore</option>
                                <option value="coal">Coal</option>
                                <option value="limestone">Limestone</option>
                                <option value="bauxite">Bauxite</option>
                                <option value="other">Other</option>
                            </select>
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
                                    placeholder="Enter volume"
                                    value={cargoVolume}
                                    onChange={(event) => setCargoVolume(event.target.value)}
                                />

                                <span>MT</span>
                            </div>
                        </div>

                        {/* Origin */}
                        <div className="cargo-field">
                            <label htmlFor="originPort">
                                Origin Port <span>*</span>
                            </label>

                            <input
                                id="originPort"
                                type="text"
                                placeholder="Enter origin port"
                                value={originPort}
                                onChange={(event) => setOriginPort(event.target.value)}
                            />
                        </div>

                        {/* Destination */}
                        <div className="cargo-field">
                            <label htmlFor="destinationPort">
                                Destination Port <span>*</span>
                            </label>

                            <input
                                id="destinationPort"
                                type="text"
                                placeholder="Enter destination port"
                                value={destinationPort}
                                onChange={(event) =>
                                    setDestinationPort(event.target.value)
                                }
                            />
                        </div>
                    </div>

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
                                    onChange={(event) =>
                                        setDeliveryStart(event.target.value)
                                    }
                                />
                            </div>

                            <div className="cargo-field">
                                <label htmlFor="deliveryEnd">
                                    Delivery End <span>*</span>
                                </label>

                                <input
                                    id="deliveryEnd"
                                    type="date"
                                    value={deliveryEnd}
                                    onChange={(event) => setDeliveryEnd(event.target.value)}
                                />
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
                                onChange={(event) =>
                                    setContractHorizon(event.target.value)
                                }
                            >
                                <option value="">Select contract horizon</option>
                                <option value="spot">Spot</option>
                                <option value="short_term_multiple_voyage">
                                    Short Term / Multiple Voyage
                                </option>
                            </select>

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

                        <button type="submit" className="cargo-submit-button">
                            Generate Decision
                            <ArrowRight size={17} />
                        </button>
                    </div>
                </form>
            </main>
        </div>
    );
}

export default CargoRequest;