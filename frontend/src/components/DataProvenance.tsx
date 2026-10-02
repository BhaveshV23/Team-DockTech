import { useEffect, useState } from "react";
import { apiRequest } from "../services/api";
import type { ProvenanceResponse } from "../types/provenance";
import "./DataProvenance.css";

function DataProvenance() {
    const [metadata, setMetadata] = useState<ProvenanceResponse | null>(null);
    const [unavailable, setUnavailable] = useState(false);

    useEffect(() => {
        let active = true;
        void apiRequest<ProvenanceResponse>("/api/v1/provenance")
            .then((response) => {
                if (active) setMetadata(response);
            })
            .catch(() => {
                if (active) setUnavailable(true);
            });
        return () => { active = false; };
    }, []);

    if (!metadata) {
        return unavailable
            ? <aside className="data-provenance-unavailable" role="status">Data provenance is unavailable.</aside>
            : <aside className="data-provenance-loading" role="status">Loading data provenance…</aside>;
    }

    const dataTypes = [...new Set(metadata.datasets.flatMap((dataset) => dataset.provenance.map((item) => item.data_type)))].sort();
    const sources = [...new Set(metadata.datasets.flatMap((dataset) => dataset.provenance.map((item) => item.source)))].sort();
    const generatedAt = new Date(metadata.generation_timestamp);
    const generatedLabel = Number.isNaN(generatedAt.getTime())
        ? metadata.generation_timestamp
        : generatedAt.toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });

    return (
        <details className="data-provenance">
            <summary>
                <span className="data-provenance-badge">{dataTypes.join(" · ")}</span>
                <span className="data-provenance-caption">Repository seed data provenance</span>
                <span className="data-provenance-toggle">Details</span>
            </summary>
            <div className="data-provenance-details">
                <div className="data-provenance-overview">
                    <span><strong>Generator</strong>{metadata.generator_name} v{metadata.generator_version}</span>
                    <span><strong>Generated</strong>{generatedLabel}</span>
                    <span><strong>Historical coverage</strong>{metadata.history_start_date} – {metadata.history_end_date}</span>
                    <span><strong>Sources</strong>{sources.join(", ")}</span>
                    <span><strong>Data types</strong>{dataTypes.join(", ")}</span>
                </div>
                <div className="data-provenance-table-wrap">
                    <table className="data-provenance-table">
                        <thead><tr><th>Dataset</th><th>Source / type</th><th>Observation dates</th><th>Units</th></tr></thead>
                        <tbody>{metadata.datasets.map((dataset) => (
                            <tr key={dataset.dataset}>
                                <td>{dataset.dataset}</td>
                                <td>{dataset.provenance.map((item) => `${item.source} · ${item.data_type}`).join("; ")}</td>
                                <td>{dataset.date_start && dataset.date_end ? `${dataset.date_start} – ${dataset.date_end}` : "—"}</td>
                                <td>{dataset.units.length ? dataset.units.join(", ") : "—"}</td>
                            </tr>
                        ))}</tbody>
                    </table>
                </div>
            </div>
        </details>
    );
}

export default DataProvenance;
