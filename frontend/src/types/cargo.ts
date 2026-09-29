export type CommodityType = "THERMAL_COAL" | "COKING_COAL";

export type ContractHorizon = "SPOT" | "SHORT_TERM" | "FLEXIBLE";

export interface CargoRequestCreate {
    commodity: CommodityType;
    cargo_volume_mt: number;
    origin_port_id: string;
    destination_port_id: string;
    earliest_delivery_date: string;
    latest_delivery_date: string;
    contract_horizon: ContractHorizon;
}

export interface CargoRequestResponse extends CargoRequestCreate {
    cargo_request_id: string;
    user_id: string;
    created_at: string;
}

/** Display adapter used by existing workflow pages. */
export interface CargoRequest extends CargoRequestResponse {
    cargoVolume: number;
    originPort: string;
    destinationPort: string;
    deliveryStartDate: string;
    deliveryEndDate: string;
    contractHorizon: ContractHorizon;
}
