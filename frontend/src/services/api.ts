const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function apiRequest<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...options.headers,
        },
    });

    if (!response.ok) {
        let message = `Request failed with status ${response.status}`;

        try {
            const errorData = await response.json();

            if (errorData?.detail) {
                message = errorData.detail;
            } else if (errorData?.message) {
                message = errorData.message;
            }
        } catch {
            // Keep the default HTTP error message.
        }

        throw new Error(message);
    }

    if (response.status === 204) {
        return undefined as T;
    }

    return response.json() as Promise<T>;
}