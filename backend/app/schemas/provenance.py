from pydantic import BaseModel


class SourceDataType(BaseModel):
    source: str
    data_type: str


class DatasetProvenance(BaseModel):
    dataset: str
    provenance: list[SourceDataType]
    date_start: str | None = None
    date_end: str | None = None
    units: list[str]


class ProvenanceResponse(BaseModel):
    generator_name: str
    generator_version: str
    generation_timestamp: str
    history_start_date: str
    history_end_date: str
    datasets: list[DatasetProvenance]
