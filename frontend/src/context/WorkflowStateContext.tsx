import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { CargoRequestResponse } from "../types/cargo";
import type { FreightHistoryResponse, ForecastRunResponse, FreightUnit, ForecastHorizon } from "../types/forecast";
import type { CanonicalScenarioSet, ScenarioDefault } from "../types/scenario";
import type { ProvenanceResponse } from "../types/provenance";

export interface WorkflowScope {
    userId: string;
    cargoRequestId: string;
}

export interface ForecastStateKey {
    routeId: string;
    vesselClassId: string;
    freightUnit: FreightUnit;
    horizon: ForecastHorizon;
}

export interface ForecastHistoryStateKey {
    routeId: string;
    vesselClassId: string;
    freightUnit: FreightUnit;
}

export interface WorkflowVessel {
    vessel_class_id: string;
    vessel_class_name: string;
    dwt_min_mt: number;
    dwt_max_mt: number;
    loa_m: number;
    beam_m: number;
    draft_m: number;
    speed_knots: number;
    cargo_capacity_mt: number;
    fuel_consumption_mt_day: number;
    source: string;
    data_type: string;
}

export interface WorkflowFeasibility {
    is_feasible: boolean;
    status: string;
    vessel_class_id: string;
    origin_port_id: string;
    destination_port_id: string;
    commodity: string;
    cargo_volume_mt: number;
    required_voyages: number | null;
    rejection_reason_code: string | null;
    rejection_reason: string | null;
}

export interface WorkflowCostResult {
    required_voyages: number;
    sailing_days_per_voyage: number;
    origin_handling_hours_total: number;
    dest_handling_hours_total: number;
    waiting_hours_total: number;
    scenario_delay_hours_total: number;
    estimated_turnaround_hours: number;
    port_days_per_voyage: number;
    vessel_days_per_voyage: number;
    vlsfo_price_used: number;
    total_fuel_consumption_mt: number;
    total_fuel_cost_usd: number;
    freight_rate_used: number;
    freight_unit: string;
    expected_freight_cost: number;
    port_costs_usd: number;
    expected_total_cost: number;
    effective_cost_per_mt: number;
    cost_reference_date: string;
    assumptions: string[];
}

export type WorkflowEntry =
    | { type: "verifiedCargo" }
    | { type: "forecast"; key: ForecastStateKey }
    | { type: "forecastHistory"; key: ForecastHistoryStateKey }
    | { type: "vessels" }
    | { type: "feasibility"; vesselClassId: string }
    | { type: "cost"; forecastRunId: string }
    | { type: "scenarioDefaults" }
    | { type: "canonicalScenarios"; forecastRunId: string }
    | { type: "provenance" };

interface WorkflowData {
    verifiedCargo: CargoRequestResponse | null;
    forecasts: Map<string, ForecastRunResponse>;
    forecastHistories: Map<string, FreightHistoryResponse>;
    vessels: WorkflowVessel[] | null;
    feasibility: Map<string, WorkflowFeasibility>;
    costs: Map<string, WorkflowCostResult>;
    scenarioDefaults: ScenarioDefault[] | null;
    canonicalScenarios: Map<string, CanonicalScenarioSet>;
    provenance: ProvenanceResponse | null;
}

interface WorkflowState {
    activeScope: WorkflowScope | null;
    data: WorkflowData;
}

interface WorkflowStateContextValue {
    activeScope: WorkflowScope | null;
    setActiveScope: (userId: string, cargoRequestId: string) => void;
    clearWorkflowState: () => void;
    getVerifiedCargo: (scope: WorkflowScope) => CargoRequestResponse | null;
    setVerifiedCargo: (scope: WorkflowScope, cargo: CargoRequestResponse) => void;
    getForecast: (scope: WorkflowScope, key: ForecastStateKey) => ForecastRunResponse | null;
    setForecast: (scope: WorkflowScope, key: ForecastStateKey, forecast: ForecastRunResponse) => void;
    getForecastHistory: (scope: WorkflowScope, key: ForecastHistoryStateKey) => FreightHistoryResponse | null;
    setForecastHistory: (scope: WorkflowScope, key: ForecastHistoryStateKey, history: FreightHistoryResponse) => void;
    getVessels: (scope: WorkflowScope) => WorkflowVessel[] | null;
    setVessels: (scope: WorkflowScope, vessels: WorkflowVessel[]) => void;
    getFeasibility: (scope: WorkflowScope, vesselClassId: string) => WorkflowFeasibility | null;
    setFeasibility: (scope: WorkflowScope, vesselClassId: string, result: WorkflowFeasibility) => void;
    getCost: (scope: WorkflowScope, forecastRunId: string) => WorkflowCostResult | null;
    setCost: (scope: WorkflowScope, forecastRunId: string, result: WorkflowCostResult) => void;
    getScenarioDefaults: (scope: WorkflowScope) => ScenarioDefault[] | null;
    setScenarioDefaults: (scope: WorkflowScope, defaults: ScenarioDefault[]) => void;
    getCanonicalScenarios: (scope: WorkflowScope, forecastRunId: string) => CanonicalScenarioSet | null;
    setCanonicalScenarios: (scope: WorkflowScope, forecastRunId: string, results: CanonicalScenarioSet) => void;
    getProvenance: () => ProvenanceResponse | null;
    setProvenance: (provenance: ProvenanceResponse) => void;
    invalidateWorkflowEntry: (entry: WorkflowEntry) => void;
}

const WorkflowStateContext = createContext<WorkflowStateContextValue | null>(null);

function emptyData(): WorkflowData {
    return {
        verifiedCargo: null,
        forecasts: new Map(),
        forecastHistories: new Map(),
        vessels: null,
        feasibility: new Map(),
        costs: new Map(),
        scenarioDefaults: null,
        canonicalScenarios: new Map(),
        provenance: null,
    };
}

function emptyState(): WorkflowState {
    return { activeScope: null, data: emptyData() };
}

function matchesScope(activeScope: WorkflowScope | null, scope: WorkflowScope, authenticatedUserId: string | null) {
    return authenticatedUserId === scope.userId &&
        activeScope?.userId === scope.userId &&
        activeScope.cargoRequestId === scope.cargoRequestId;
}

function forecastKey(key: ForecastStateKey) {
    return JSON.stringify([key.routeId, key.vesselClassId, key.freightUnit, key.horizon]);
}

function historyKey(key: ForecastHistoryStateKey) {
    return JSON.stringify([key.routeId, key.vesselClassId, key.freightUnit]);
}

export function WorkflowStateProvider({
    authenticatedUserId,
    children,
}: {
    authenticatedUserId: string | null;
    children: ReactNode;
}) {
    const [state, setState] = useState<WorkflowState>(emptyState);

    const setActiveScope = useCallback((userId: string, cargoRequestId: string) => {
        if (!authenticatedUserId || userId !== authenticatedUserId || !cargoRequestId) return;
        setState((current) => {
            if (current.activeScope?.userId === userId && current.activeScope.cargoRequestId === cargoRequestId) {
                return current;
            }
            return { activeScope: { userId, cargoRequestId }, data: emptyData() };
        });
    }, [authenticatedUserId]);

    const clearWorkflowState = useCallback(() => setState(emptyState()), []);

    const updateScopedData = useCallback((scope: WorkflowScope, update: (data: WorkflowData) => WorkflowData) => {
        if (!authenticatedUserId || scope.userId !== authenticatedUserId) return;
        setState((current) => matchesScope(current.activeScope, scope, authenticatedUserId)
            ? { ...current, data: update(current.data) }
            : current);
    }, [authenticatedUserId]);

    const getVerifiedCargo = useCallback((scope: WorkflowScope) => {
        if (!matchesScope(state.activeScope, scope, authenticatedUserId)) return null;
        const cargo = state.data.verifiedCargo;
        return cargo?.user_id === scope.userId && cargo.cargo_request_id === scope.cargoRequestId ? cargo : null;
    }, [authenticatedUserId, state]);

    const setVerifiedCargo = useCallback((scope: WorkflowScope, cargo: CargoRequestResponse) => {
        if (cargo.user_id !== scope.userId || cargo.cargo_request_id !== scope.cargoRequestId) return;
        updateScopedData(scope, (data) => ({ ...data, verifiedCargo: cargo }));
    }, [updateScopedData]);

    const getForecast = useCallback((scope: WorkflowScope, key: ForecastStateKey) => {
        if (!matchesScope(state.activeScope, scope, authenticatedUserId)) return null;
        return state.data.forecasts.get(forecastKey(key)) ?? null;
    }, [authenticatedUserId, state]);

    const setForecast = useCallback((scope: WorkflowScope, key: ForecastStateKey, forecast: ForecastRunResponse) => {
        if (forecast.cargo_request_id !== scope.cargoRequestId || forecast.route_id !== key.routeId ||
            forecast.vessel_class_id !== key.vesselClassId || forecast.freight_unit !== key.freightUnit) return;
        updateScopedData(scope, (data) => {
            const forecasts = new Map(data.forecasts);
            forecasts.set(forecastKey(key), forecast);
            return { ...data, forecasts };
        });
    }, [updateScopedData]);

    const getForecastHistory = useCallback((scope: WorkflowScope, key: ForecastHistoryStateKey) => {
        if (!matchesScope(state.activeScope, scope, authenticatedUserId)) return null;
        return state.data.forecastHistories.get(historyKey(key)) ?? null;
    }, [authenticatedUserId, state]);

    const setForecastHistory = useCallback((scope: WorkflowScope, key: ForecastHistoryStateKey, history: FreightHistoryResponse) => {
        if (history.route_id !== key.routeId || history.vessel_class_id !== key.vesselClassId || history.freight_unit !== key.freightUnit) return;
        updateScopedData(scope, (data) => {
            const forecastHistories = new Map(data.forecastHistories);
            forecastHistories.set(historyKey(key), history);
            return { ...data, forecastHistories };
        });
    }, [updateScopedData]);

    const getVessels = useCallback((scope: WorkflowScope) =>
        matchesScope(state.activeScope, scope, authenticatedUserId) ? state.data.vessels : null,
    [authenticatedUserId, state]);

    const setVessels = useCallback((scope: WorkflowScope, vessels: WorkflowVessel[]) => {
        updateScopedData(scope, (data) => ({ ...data, vessels }));
    }, [updateScopedData]);

    const getFeasibility = useCallback((scope: WorkflowScope, vesselClassId: string) =>
        matchesScope(state.activeScope, scope, authenticatedUserId)
            ? state.data.feasibility.get(vesselClassId) ?? null
            : null,
    [authenticatedUserId, state]);

    const setFeasibility = useCallback((scope: WorkflowScope, vesselClassId: string, result: WorkflowFeasibility) => {
        if (result.vessel_class_id !== vesselClassId) return;
        updateScopedData(scope, (data) => {
            const feasibility = new Map(data.feasibility);
            feasibility.set(vesselClassId, result);
            return { ...data, feasibility };
        });
    }, [updateScopedData]);

    const getCost = useCallback((scope: WorkflowScope, forecastRunId: string) =>
        matchesScope(state.activeScope, scope, authenticatedUserId) ? state.data.costs.get(forecastRunId) ?? null : null,
    [authenticatedUserId, state]);

    const setCost = useCallback((scope: WorkflowScope, forecastRunId: string, result: WorkflowCostResult) => {
        updateScopedData(scope, (data) => {
            const costs = new Map(data.costs);
            costs.set(forecastRunId, result);
            return { ...data, costs };
        });
    }, [updateScopedData]);

    const getScenarioDefaults = useCallback((scope: WorkflowScope) =>
        matchesScope(state.activeScope, scope, authenticatedUserId) ? state.data.scenarioDefaults : null,
    [authenticatedUserId, state]);

    const setScenarioDefaults = useCallback((scope: WorkflowScope, defaults: ScenarioDefault[]) => {
        updateScopedData(scope, (data) => ({ ...data, scenarioDefaults: defaults }));
    }, [updateScopedData]);

    const getCanonicalScenarios = useCallback((scope: WorkflowScope, forecastRunId: string) =>
        matchesScope(state.activeScope, scope, authenticatedUserId)
            ? state.data.canonicalScenarios.get(forecastRunId) ?? null
            : null,
    [authenticatedUserId, state]);

    const setCanonicalScenarios = useCallback((scope: WorkflowScope, forecastRunId: string, results: CanonicalScenarioSet) => {
        const cargoIds = [results.baseline?.cargo_request_id, results.adverse?.cargo_request_id, results.favorable?.cargo_request_id];
        if (cargoIds.some((cargoId) => cargoId !== scope.cargoRequestId)) return;
        updateScopedData(scope, (data) => {
            const canonicalScenarios = new Map(data.canonicalScenarios);
            canonicalScenarios.set(forecastRunId, results);
            return { ...data, canonicalScenarios };
        });
    }, [updateScopedData]);

    const getProvenance = useCallback(() => authenticatedUserId ? state.data.provenance : null, [authenticatedUserId, state]);

    const setProvenance = useCallback((provenance: ProvenanceResponse) => {
        if (!authenticatedUserId) return;
        setState((current) => ({ ...current, data: { ...current.data, provenance } }));
    }, [authenticatedUserId]);

    const invalidateWorkflowEntry = useCallback((entry: WorkflowEntry) => {
        setState((current) => {
            const data = current.data;
            switch (entry.type) {
                case "verifiedCargo":
                    return { ...current, data: { ...data, verifiedCargo: null } };
                case "forecast": {
                    const forecasts = new Map(data.forecasts);
                    forecasts.delete(forecastKey(entry.key));
                    return { ...current, data: { ...data, forecasts } };
                }
                case "forecastHistory": {
                    const forecastHistories = new Map(data.forecastHistories);
                    forecastHistories.delete(historyKey(entry.key));
                    return { ...current, data: { ...data, forecastHistories } };
                }
                case "vessels":
                    return { ...current, data: { ...data, vessels: null } };
                case "feasibility": {
                    const feasibility = new Map(data.feasibility);
                    feasibility.delete(entry.vesselClassId);
                    return { ...current, data: { ...data, feasibility } };
                }
                case "cost": {
                    const costs = new Map(data.costs);
                    costs.delete(entry.forecastRunId);
                    return { ...current, data: { ...data, costs } };
                }
                case "scenarioDefaults":
                    return { ...current, data: { ...data, scenarioDefaults: null } };
                case "canonicalScenarios": {
                    const canonicalScenarios = new Map(data.canonicalScenarios);
                    canonicalScenarios.delete(entry.forecastRunId);
                    return { ...current, data: { ...data, canonicalScenarios } };
                }
                case "provenance":
                    return { ...current, data: { ...data, provenance: null } };
            }
        });
    }, []);

    const value = useMemo<WorkflowStateContextValue>(() => ({
        activeScope: state.activeScope,
        setActiveScope,
        clearWorkflowState,
        getVerifiedCargo,
        setVerifiedCargo,
        getForecast,
        setForecast,
        getForecastHistory,
        setForecastHistory,
        getVessels,
        setVessels,
        getFeasibility,
        setFeasibility,
        getCost,
        setCost,
        getScenarioDefaults,
        setScenarioDefaults,
        getCanonicalScenarios,
        setCanonicalScenarios,
        getProvenance,
        setProvenance,
        invalidateWorkflowEntry,
    }), [
        state.activeScope,
        setActiveScope,
        clearWorkflowState,
        getVerifiedCargo,
        setVerifiedCargo,
        getForecast,
        setForecast,
        getForecastHistory,
        setForecastHistory,
        getVessels,
        setVessels,
        getFeasibility,
        setFeasibility,
        getCost,
        setCost,
        getScenarioDefaults,
        setScenarioDefaults,
        getCanonicalScenarios,
        setCanonicalScenarios,
        getProvenance,
        setProvenance,
        invalidateWorkflowEntry,
    ]);

    return <WorkflowStateContext.Provider value={value}>{children}</WorkflowStateContext.Provider>;
}

// This hook intentionally shares the provider module; it is not a renderable component.
// eslint-disable-next-line react-refresh/only-export-components
export function useWorkflowState() {
    const context = useContext(WorkflowStateContext);
    if (!context) throw new Error("useWorkflowState must be used within WorkflowStateProvider.");
    return context;
}
