-- ==============================================================================
-- DockTech V1 — Canonical Database Schema Migration
-- ==============================================================================
-- Project: DockTech (SIH 2026 PS ID: 26006)
-- Title: Development of an Intelligent Freight Forecasting Model for Optimized
--        Vessel Chartering and Bulk Cargo Procurement from overseas to East Coast of India
-- Authoritative Sources: PRD.md, DATA_DICTIONARY.md, ARCHITECTURE.md
-- ==============================================================================

-- Enable UUID extension if not already present
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==============================================================================
-- 1. REFERENCE DATA TABLES (9 Tables)
-- ==============================================================================

-- 1.1 Ports
CREATE TABLE IF NOT EXISTS ports (
    port_id TEXT PRIMARY KEY,
    port_name TEXT NOT NULL UNIQUE,
    country TEXT NOT NULL,
    max_loa_m NUMERIC NOT NULL CHECK (max_loa_m > 0),
    max_beam_m NUMERIC NOT NULL CHECK (max_beam_m > 0),
    max_draft_m NUMERIC NOT NULL CHECK (max_draft_m > 0),
    handling_rate_tpd NUMERIC NOT NULL CHECK (handling_rate_tpd > 0),
    typical_turnaround_hours NUMERIC NOT NULL CHECK (typical_turnaround_hours > 0),
    source TEXT NOT NULL,
    data_type TEXT NOT NULL CHECK (data_type IN ('SYNTHETIC', 'PROXY', 'ACTUAL', 'ESTIMATED'))
);

-- 1.2 Berths
CREATE TABLE IF NOT EXISTS berths (
    berth_id TEXT PRIMARY KEY,
    port_id TEXT NOT NULL REFERENCES ports(port_id) ON DELETE RESTRICT,
    berth_name TEXT NOT NULL,
    commodity TEXT NOT NULL CHECK (commodity IN ('THERMAL_COAL', 'COKING_COAL')),
    max_loa_m NUMERIC NOT NULL CHECK (max_loa_m > 0),
    max_beam_m NUMERIC NOT NULL CHECK (max_beam_m > 0),
    max_draft_m NUMERIC NOT NULL CHECK (max_draft_m > 0),
    handling_rate_tpd NUMERIC NOT NULL CHECK (handling_rate_tpd > 0),
    source TEXT NOT NULL,
    data_type TEXT NOT NULL CHECK (data_type IN ('SYNTHETIC', 'PROXY', 'ACTUAL', 'ESTIMATED'))
);

-- 1.3 Vessel Classes
CREATE TABLE IF NOT EXISTS vessel_classes (
    vessel_class_id TEXT PRIMARY KEY CHECK (vessel_class_id IN ('HANDYSIZE', 'SUPRAMAX', 'ULTRAMAX', 'PANAMAX', 'KAMSARMAX', 'CAPESIZE')),
    vessel_class_name TEXT NOT NULL,
    dwt_min_mt NUMERIC NOT NULL CHECK (dwt_min_mt > 0),
    dwt_max_mt NUMERIC NOT NULL CHECK (dwt_max_mt > dwt_min_mt),
    loa_m NUMERIC NOT NULL CHECK (loa_m > 0),
    beam_m NUMERIC NOT NULL CHECK (beam_m > 0),
    draft_m NUMERIC NOT NULL CHECK (draft_m > 0),
    speed_knots NUMERIC NOT NULL CHECK (speed_knots > 0),
    cargo_capacity_mt NUMERIC NOT NULL CHECK (cargo_capacity_mt > 0 AND cargo_capacity_mt < dwt_max_mt),
    fuel_consumption_mt_day NUMERIC NOT NULL CHECK (fuel_consumption_mt_day > 0),
    source TEXT NOT NULL,
    data_type TEXT NOT NULL CHECK (data_type IN ('SYNTHETIC', 'PROXY', 'ACTUAL', 'ESTIMATED'))
);

-- 1.4 Routes
CREATE TABLE IF NOT EXISTS routes (
    route_id TEXT PRIMARY KEY,
    origin_port_id TEXT NOT NULL REFERENCES ports(port_id) ON DELETE RESTRICT,
    destination_port_id TEXT NOT NULL REFERENCES ports(port_id) ON DELETE RESTRICT,
    commodity TEXT NOT NULL CHECK (commodity IN ('THERMAL_COAL', 'COKING_COAL')),
    distance_nm NUMERIC NOT NULL CHECK (distance_nm > 0),
    typical_sailing_days NUMERIC NOT NULL CHECK (typical_sailing_days > 0),
    source TEXT NOT NULL,
    data_type TEXT NOT NULL CHECK (data_type IN ('SYNTHETIC', 'PROXY', 'ACTUAL', 'ESTIMATED')),
    CONSTRAINT routes_origin_dest_commodity_key UNIQUE (origin_port_id, destination_port_id, commodity),
    CONSTRAINT routes_origin_diff_dest_check CHECK (origin_port_id <> destination_port_id)
);

-- 1.5 Freight Rates (Time-series)
CREATE TABLE IF NOT EXISTS freight_rates (
    freight_rate_id TEXT PRIMARY KEY,
    observation_date DATE NOT NULL,
    route_id TEXT NOT NULL REFERENCES routes(route_id) ON DELETE RESTRICT,
    vessel_class_id TEXT NOT NULL REFERENCES vessel_classes(vessel_class_id) ON DELETE RESTRICT,
    freight_value NUMERIC NOT NULL CHECK (freight_value > 0),
    freight_unit TEXT NOT NULL CHECK (freight_unit IN ('USD_PER_MT', 'USD_PER_DAY')),
    currency TEXT NOT NULL,
    data_type TEXT NOT NULL CHECK (data_type IN ('SYNTHETIC', 'PROXY', 'ACTUAL', 'ESTIMATED')),
    source TEXT NOT NULL,
    CONSTRAINT freight_rates_grain_key UNIQUE (observation_date, route_id, vessel_class_id, freight_unit)
);

-- 1.6 Commodity Prices (Time-series)
CREATE TABLE IF NOT EXISTS commodity_prices (
    commodity_price_id TEXT PRIMARY KEY,
    observation_date DATE NOT NULL,
    commodity TEXT NOT NULL CHECK (commodity IN ('THERMAL_COAL', 'COKING_COAL')),
    market TEXT NOT NULL,
    price_value NUMERIC NOT NULL CHECK (price_value > 0),
    currency TEXT NOT NULL,
    unit TEXT NOT NULL,
    data_type TEXT NOT NULL CHECK (data_type IN ('SYNTHETIC', 'PROXY', 'ACTUAL', 'ESTIMATED')),
    source TEXT NOT NULL,
    CONSTRAINT commodity_prices_grain_key UNIQUE (observation_date, commodity, market)
);

-- 1.7 Fuel Prices (Time-series)
CREATE TABLE IF NOT EXISTS fuel_prices (
    fuel_price_id TEXT PRIMARY KEY,
    observation_date DATE NOT NULL,
    fuel_type TEXT NOT NULL CHECK (fuel_type IN ('VLSFO', 'MGO')),
    price_value NUMERIC NOT NULL CHECK (price_value > 0),
    currency TEXT NOT NULL,
    unit TEXT NOT NULL,
    data_type TEXT NOT NULL CHECK (data_type IN ('SYNTHETIC', 'PROXY', 'ACTUAL', 'ESTIMATED')),
    source TEXT NOT NULL,
    CONSTRAINT fuel_prices_grain_key UNIQUE (observation_date, fuel_type)
);

-- 1.8 Port Activity (Time-series)
CREATE TABLE IF NOT EXISTS port_activity (
    activity_id TEXT PRIMARY KEY,
    observation_date DATE NOT NULL,
    port_id TEXT NOT NULL REFERENCES ports(port_id) ON DELETE RESTRICT,
    vessel_arrivals INTEGER NOT NULL CHECK (vessel_arrivals >= 0),
    average_waiting_hours NUMERIC NOT NULL CHECK (average_waiting_hours >= 0),
    average_turnaround_hours NUMERIC NOT NULL CHECK (average_turnaround_hours > 0),
    congestion_level TEXT NOT NULL CHECK (congestion_level IN ('LOW', 'MEDIUM', 'HIGH')),
    source TEXT NOT NULL,
    data_type TEXT NOT NULL CHECK (data_type IN ('SYNTHETIC', 'PROXY', 'ACTUAL', 'ESTIMATED')),
    CONSTRAINT port_activity_grain_key UNIQUE (observation_date, port_id)
);

-- 1.9 Scenario Defaults
CREATE TABLE IF NOT EXISTS scenario_defaults (
    scenario_id TEXT PRIMARY KEY CHECK (scenario_id IN ('BASELINE', 'ADVERSE', 'FAVORABLE')),
    scenario_name TEXT NOT NULL,
    freight_change_pct NUMERIC NOT NULL,
    fuel_change_pct NUMERIC NOT NULL,
    delay_hours NUMERIC NOT NULL CHECK (delay_hours >= 0),
    port_congestion_level TEXT NOT NULL CHECK (port_congestion_level IN ('LOW', 'MEDIUM', 'HIGH')),
    description TEXT NOT NULL,
    source TEXT NOT NULL,
    data_type TEXT NOT NULL CHECK (data_type IN ('SYNTHETIC', 'PROXY', 'ACTUAL', 'ESTIMATED'))
);

-- ==============================================================================
-- 2. APPLICATION TABLES (7 Tables)
-- ==============================================================================

-- 2.1 User Profiles (Linked to Supabase auth.users)
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL CHECK (role IN ('VIEWER', 'PLANNER', 'MANAGER', 'ADMINISTRATOR')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

-- 2.2 Cargo Requests
CREATE TABLE IF NOT EXISTS cargo_requests (
    cargo_request_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES user_profiles(user_id) ON DELETE RESTRICT,
    commodity TEXT NOT NULL CHECK (commodity IN ('THERMAL_COAL', 'COKING_COAL')),
    cargo_volume_mt NUMERIC NOT NULL CHECK (cargo_volume_mt > 0),
    origin_port_id TEXT NOT NULL REFERENCES ports(port_id) ON DELETE RESTRICT,
    destination_port_id TEXT NOT NULL REFERENCES ports(port_id) ON DELETE RESTRICT,
    earliest_delivery_date DATE NOT NULL,
    latest_delivery_date DATE NOT NULL,
    contract_horizon TEXT NOT NULL CHECK (contract_horizon IN ('SPOT', 'SHORT_TERM', 'FLEXIBLE')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT cargo_requests_delivery_dates_check CHECK (latest_delivery_date >= earliest_delivery_date),
    CONSTRAINT cargo_requests_ports_check CHECK (origin_port_id <> destination_port_id)
);

-- 2.3 Forecast Runs
CREATE TABLE IF NOT EXISTS forecast_runs (
    forecast_run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cargo_request_id UUID NOT NULL REFERENCES cargo_requests(cargo_request_id) ON DELETE RESTRICT,
    route_id TEXT NOT NULL REFERENCES routes(route_id) ON DELETE RESTRICT,
    vessel_class_id TEXT NOT NULL REFERENCES vessel_classes(vessel_class_id) ON DELETE RESTRICT,
    freight_unit TEXT NOT NULL CHECK (freight_unit IN ('USD_PER_MT', 'USD_PER_DAY')),
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    training_data_end_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

-- 2.4 Forecast Points
CREATE TABLE IF NOT EXISTS forecast_points (
    forecast_point_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    forecast_run_id UUID NOT NULL REFERENCES forecast_runs(forecast_run_id) ON DELETE CASCADE,
    forecast_date DATE NOT NULL,
    central_value NUMERIC NOT NULL CHECK (central_value > 0),
    lower_value NUMERIC NOT NULL CHECK (lower_value > 0),
    upper_value NUMERIC NOT NULL CHECK (upper_value > 0),
    unit TEXT NOT NULL CHECK (unit IN ('USD_PER_MT', 'USD_PER_DAY')),
    CONSTRAINT forecast_points_grain_key UNIQUE (forecast_run_id, forecast_date),
    CONSTRAINT forecast_points_bounds_check CHECK (lower_value <= central_value AND central_value <= upper_value)
);

-- 2.5 Scenarios
CREATE TABLE IF NOT EXISTS scenarios (
    scenario_instance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cargo_request_id UUID NOT NULL REFERENCES cargo_requests(cargo_request_id) ON DELETE RESTRICT,
    scenario_type TEXT NOT NULL CHECK (scenario_type IN ('BASELINE', 'ADVERSE', 'FAVORABLE')),
    freight_change_pct NUMERIC NOT NULL,
    fuel_change_pct NUMERIC NOT NULL,
    delay_hours NUMERIC NOT NULL CHECK (delay_hours >= 0),
    congestion_level TEXT NOT NULL CHECK (congestion_level IN ('LOW', 'MEDIUM', 'HIGH')),
    estimated_total_cost NUMERIC NOT NULL CHECK (estimated_total_cost > 0),
    risk_level TEXT NOT NULL CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

-- 2.6 Recommendations
CREATE TABLE IF NOT EXISTS recommendations (
    recommendation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cargo_request_id UUID NOT NULL REFERENCES cargo_requests(cargo_request_id) ON DELETE RESTRICT,
    forecast_run_id UUID NOT NULL REFERENCES forecast_runs(forecast_run_id) ON DELETE RESTRICT,
    recommended_vessel_class_id TEXT NOT NULL REFERENCES vessel_classes(vessel_class_id) ON DELETE RESTRICT,
    market_entry_action TEXT NOT NULL CHECK (market_entry_action IN ('FIX_NOW', 'WAIT')),
    contract_strategy TEXT NOT NULL CHECK (contract_strategy IN ('SPOT', 'SHORT_TERM_MULTIPLE_VOYAGE')),
    expected_freight_cost NUMERIC NOT NULL CHECK (expected_freight_cost > 0),
    expected_total_cost NUMERIC NOT NULL CHECK (expected_total_cost > 0),
    estimated_turnaround_hours NUMERIC NOT NULL CHECK (estimated_turnaround_hours > 0),
    risk_level TEXT NOT NULL CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH')),
    confidence TEXT NOT NULL CHECK (confidence IN ('LOW', 'MEDIUM', 'HIGH')),
    rationale TEXT NOT NULL,
    assumptions TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

-- 2.7 Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    audit_log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES user_profiles(user_id) ON DELETE RESTRICT,
    action TEXT NOT NULL CHECK (action IN ('CREATE', 'UPDATE', 'DELETE', 'EXPORT', 'GENERATE_FORECAST', 'GENERATE_RECOMMENDATION')),
    entity_type TEXT NOT NULL CHECK (entity_type IN ('CARGO_REQUEST', 'FORECAST_RUN', 'SCENARIO', 'RECOMMENDATION', 'REPORT', 'PORT', 'BERTH', 'VESSEL_CLASS', 'ROUTE', 'REFERENCE_DATA')),
    entity_id TEXT NOT NULL,
    details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

-- ==============================================================================
-- 3. INDEXES
-- ==============================================================================

-- Reference Data Time-Series & Query Indexes
CREATE INDEX IF NOT EXISTS idx_freight_rates_route_obs_date ON freight_rates (route_id, observation_date);
CREATE INDEX IF NOT EXISTS idx_freight_rates_vessel_obs_date ON freight_rates (vessel_class_id, observation_date);
CREATE INDEX IF NOT EXISTS idx_commodity_prices_comm_mkt_obs ON commodity_prices (commodity, market, observation_date);
CREATE INDEX IF NOT EXISTS idx_fuel_prices_fuel_obs ON fuel_prices (fuel_type, observation_date);
CREATE INDEX IF NOT EXISTS idx_port_activity_port_obs ON port_activity (port_id, observation_date);
CREATE INDEX IF NOT EXISTS idx_berths_port_id ON berths (port_id);
CREATE INDEX IF NOT EXISTS idx_routes_origin_dest ON routes (origin_port_id, destination_port_id);

-- Application Table Foreign Key & Lookup Indexes
CREATE INDEX IF NOT EXISTS idx_cargo_requests_user_id ON cargo_requests (user_id);
CREATE INDEX IF NOT EXISTS idx_forecast_runs_cargo_request_id ON forecast_runs (cargo_request_id);
CREATE INDEX IF NOT EXISTS idx_forecast_points_forecast_run_id ON forecast_points (forecast_run_id);
CREATE INDEX IF NOT EXISTS idx_scenarios_cargo_request_id ON scenarios (cargo_request_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_cargo_request_id ON recommendations (cargo_request_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_forecast_run_id ON recommendations (forecast_run_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs (created_at);

-- ==============================================================================
-- 4. ROW LEVEL SECURITY (RLS)
-- ==============================================================================
-- Establish default-deny RLS baseline across all 16 tables.
-- FastAPI server accesses PostgreSQL via service_role key bypassing RLS.
-- Frontend does NOT query database directly, maintaining architectural integrity.

ALTER TABLE ports ENABLE ROW LEVEL SECURITY;
ALTER TABLE berths ENABLE ROW LEVEL SECURITY;
ALTER TABLE vessel_classes ENABLE ROW LEVEL SECURITY;
ALTER TABLE routes ENABLE ROW LEVEL SECURITY;
ALTER TABLE freight_rates ENABLE ROW LEVEL SECURITY;
ALTER TABLE commodity_prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE fuel_prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE port_activity ENABLE ROW LEVEL SECURITY;
ALTER TABLE scenario_defaults ENABLE ROW LEVEL SECURITY;

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE cargo_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE forecast_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE forecast_points ENABLE ROW LEVEL SECURITY;
ALTER TABLE scenarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
