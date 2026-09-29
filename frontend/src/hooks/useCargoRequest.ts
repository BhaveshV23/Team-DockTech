import { useAuthenticatedUser } from "../services/api";
import type { CargoRequest, CargoRequestResponse } from "../types/cargo";

const STORAGE_KEY = "docktech-cargo-request";

function readCargoRequest(currentUserId: string): CargoRequest | null {
    const storedRequest = sessionStorage.getItem(STORAGE_KEY);

    if (!storedRequest) {
        return null;
    }

    try {
        const response = JSON.parse(storedRequest) as CargoRequestResponse;
        if (!response.cargo_request_id || !response.user_id) return null;
        if (response.user_id !== currentUserId) {
            sessionStorage.removeItem(STORAGE_KEY);
            return null;
        }
        return {
            ...response,
            cargoVolume: response.cargo_volume_mt,
            originPort: response.origin_port_id,
            destinationPort: response.destination_port_id,
            deliveryStartDate: response.earliest_delivery_date,
            deliveryEndDate: response.latest_delivery_date,
            contractHorizon: response.contract_horizon,
        };
    } catch {
        return null;
    }
}

export function useCargoRequest(): CargoRequest | null {
    const user = useAuthenticatedUser();
    return user ? readCargoRequest(user.user_id) : null;
}
