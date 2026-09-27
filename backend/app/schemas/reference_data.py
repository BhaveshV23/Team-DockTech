from pydantic import BaseModel, ConfigDict


class PortResponse(BaseModel):
    port_id: str
    port_name: str
    country: str
    max_loa_m: float
    max_beam_m: float
    max_draft_m: float
    handling_rate_tpd: float
    typical_turnaround_hours: float
    source: str
    data_type: str

    model_config = ConfigDict(from_attributes=True)


class VesselClassResponse(BaseModel):
    vessel_class_id: str
    vessel_class_name: str
    dwt_min_mt: float
    dwt_max_mt: float
    loa_m: float
    beam_m: float
    draft_m: float
    speed_knots: float
    cargo_capacity_mt: float
    fuel_consumption_mt_day: float
    source: str
    data_type: str

    model_config = ConfigDict(from_attributes=True)


class RouteResponse(BaseModel):
    route_id: str
    origin_port_id: str
    destination_port_id: str
    commodity: str
    distance_nm: float
    typical_sailing_days: float
    source: str
    data_type: str

    model_config = ConfigDict(from_attributes=True)
