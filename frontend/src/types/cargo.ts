export type ContractHorizon =
    | "SPOT"
    | "SHORT_TERM"
    | "MULTIPLE_VOYAGE";

export interface CargoRequest {
    commodity: string;
    cargoVolume: number;
    originPort: string;
    destinationPort: string;
    deliveryStartDate: string;
    deliveryEndDate: string;
    contractHorizon: ContractHorizon;
}