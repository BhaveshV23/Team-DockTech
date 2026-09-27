import { useState } from "react";
import type { CargoRequest as CargoRequestData } from "../types/cargo";

const STORAGE_KEY = "docktech-cargo-request";

function readCargoRequest(): CargoRequestData | null {
    const storedRequest = sessionStorage.getItem(STORAGE_KEY);

    if (!storedRequest) {
        return null;
    }

    try {
        return JSON.parse(storedRequest) as CargoRequestData;
    } catch {
        return null;
    }
}

export function useCargoRequest(): CargoRequestData | null {
    const [cargoRequest] = useState<CargoRequestData | null>(
        readCargoRequest
    );

    return cargoRequest;
}