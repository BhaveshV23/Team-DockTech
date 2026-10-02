export interface SourceDataType {
    source: string;
    data_type: string;
}

export interface DatasetProvenance {
    dataset: string;
    provenance: SourceDataType[];
    date_start: string | null;
    date_end: string | null;
    units: string[];
}

export interface ProvenanceResponse {
    generator_name: string;
    generator_version: string;
    generation_timestamp: string;
    history_start_date: string;
    history_end_date: string;
    datasets: DatasetProvenance[];
}
