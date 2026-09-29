import { createClient } from "@supabase/supabase-js";
import { useSyncExternalStore } from "react";

const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;

let rememberSession = true;

const authStorage = {
    getItem(key: string) {
        if (typeof window === "undefined") return null;
        return rememberSession
            ? window.localStorage.getItem(key) ?? window.sessionStorage.getItem(key)
            : window.sessionStorage.getItem(key) ?? window.localStorage.getItem(key);
    },
    setItem(key: string, value: string) {
        if (typeof window === "undefined") return;
        const target = rememberSession ? window.localStorage : window.sessionStorage;
        const other = rememberSession ? window.sessionStorage : window.localStorage;
        other.removeItem(key);
        target.setItem(key, value);
    },
    removeItem(key: string) {
        if (typeof window === "undefined") return;
        window.localStorage.removeItem(key);
        window.sessionStorage.removeItem(key);
    },
};

export const supabase = SUPABASE_URL && SUPABASE_ANON_KEY
    ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
        auth: {
            persistSession: true,
            autoRefreshToken: true,
            detectSessionInUrl: true,
            storage: authStorage,
        },
    })
    : null;

export type AuthProfile = {
    user_id: string;
    auth_user_id: string;
    display_name: string;
    email: string;
    role: "VIEWER" | "PLANNER" | "MANAGER" | "ADMINISTRATOR";
    created_at: string;
    updated_at: string;
};

export type AuthenticatedUser = {
    user_id: string;
    name: string;
    email: string;
    role: AuthProfile["role"];
};

const ROLE_LABELS: Record<AuthenticatedUser["role"], string> = {
    VIEWER: "Viewer",
    PLANNER: "Planner",
    MANAGER: "Manager",
    ADMINISTRATOR: "Administrator",
};

const ROLE_DESCRIPTIONS: Record<AuthenticatedUser["role"], string> = {
    VIEWER: "Views freight, vessel, and decision information.",
    PLANNER: "Plans cargo requirements and reviews freight decisions.",
    MANAGER: "Reviews planning decisions and business outcomes.",
    ADMINISTRATOR: "Oversees DockTech access and system configuration.",
};

let authenticatedUser: AuthenticatedUser | null = null;
const userListeners = new Set<() => void>();

function subscribeToUser(listener: () => void) {
    userListeners.add(listener);
    return () => userListeners.delete(listener);
}

function getUserSnapshot() {
    return authenticatedUser;
}

export function setAuthenticatedProfile(profile: AuthProfile | null) {
    authenticatedUser = profile
        ? {
            user_id: profile.user_id,
            name: profile.display_name,
            email: profile.email,
            role: profile.role,
        }
        : null;
    userListeners.forEach((listener) => listener());
}

export function useAuthenticatedUser() {
    return useSyncExternalStore(subscribeToUser, getUserSnapshot, () => null);
}

export function getRoleLabel(role: AuthenticatedUser["role"]) {
    return ROLE_LABELS[role];
}

export function getRoleDescription(role: AuthenticatedUser["role"]) {
    return ROLE_DESCRIPTIONS[role];
}

export function setRememberSession(remember: boolean) {
    rememberSession = remember;
}

export function getAuthConfigurationError(): string | null {
    if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
        return "Authentication is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.";
    }
    return null;
}

export class ApiRequestError extends Error {
    readonly status: number;
    readonly code: string | null;

    constructor(
        message: string,
        status: number,
        code: string | null
    ) {
        super(message);
        this.name = "ApiRequestError";
        this.status = status;
        this.code = code;
    }
}

export async function apiRequest<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> {
    const headers = new Headers(options.headers);
    if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
        headers.set("Content-Type", "application/json");
    }

    if (!headers.has("Authorization") && supabase) {
        const { data, error } = await supabase.auth.getSession();
        if (error) throw new Error(error.message);
        if (data.session?.access_token) {
            headers.set("Authorization", `Bearer ${data.session.access_token}`);
        }
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
    });

    if (!response.ok) {
        let message = `Request failed with status ${response.status}`;
        let code: string | null = null;
        try {
            const errorData = await response.json();
            const detail = errorData?.detail;
            if (typeof detail === "string") {
                message = detail;
            } else if (detail && typeof detail === "object" && !Array.isArray(detail)) {
                if (typeof detail.code === "string") code = detail.code;
                if (typeof detail.message === "string") message = detail.message;
            } else if (Array.isArray(detail)) {
                const validationMessages = detail
                    .map((item: unknown) =>
                        item && typeof item === "object" && "msg" in item && typeof item.msg === "string"
                            ? item.msg
                            : null
                    )
                    .filter((item): item is string => item !== null);
                if (validationMessages.length > 0) {
                    message = validationMessages.join("; ");
                }
            } else if (typeof errorData?.message === "string") {
                message = errorData.message;
            }
        } catch {
            // Keep the default HTTP error message.
        }
        throw new ApiRequestError(message, response.status, code);
    }

    if (response.status === 204) return undefined as T;
    return response.json() as Promise<T>;
}

export async function signOut() {
    if (!supabase) {
        setAuthenticatedProfile(null);
        return;
    }
    const { error } = await supabase.auth.signOut();
    if (error) throw new Error(error.message);
    setAuthenticatedProfile(null);
}
