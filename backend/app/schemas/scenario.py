"""Scenario Pydantic schemas for DockTech V1 API."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from backend.app.domain.constants import (
    Commodity,
    CongestionLevel,
    ContractHorizon,
    FreightUnit,
    RiskLevel,
    ScenarioType,
)


class ScenarioDefaultResponse(BaseModel):
    scenario_id: ScenarioType
    scenario_name: str
    freight_change_pct: float
    fuel_change_pct: float
    delay_hours: float
    port_congestion_level: CongestionLevel
    description: str


class VoyageCostBreakdownSchema(BaseModel):
    sailing_days: float
    required_voyages: int
    origin_handling_hours_total: float
    destination_handling_hours_total: float
    waiting_hours_total: float
    scenario_delay_total: float
    estimated_turnaround_hours: float
    turnaround_hours_per_voyage: float
    port_days_per_voyage: float
    vessel_days_per_voyage: float
    total_fuel_cost_usd: float
    expected_freight_cost: float
    expected_total_cost: float
    effective_cost_per_mt: float


class ScenarioResultResponse(BaseModel):
    scenario_instance_id: UUID
    cargo_request_id: UUID
    scenario_type: ScenarioType
    freight_change_pct: float
    fuel_change_pct: float
    delay_hours: float
    congestion_level: CongestionLevel
    estimated_total_cost: float
    estimated_turnaround_hours: float
    cost_breakdown: VoyageCostBreakdownSchema
    risk_level: RiskLevel
    created_at: datetime


class ScenarioComparisonResponse(BaseModel):
    baseline_result: ScenarioResultResponse
    scenario_result: ScenarioResultResponse
    delta_cost_usd: float
    delta_cost_pct: float
    delta_turnaround_hours: float
    delta_effective_cost_per_mt: float
    risk_transition: str


class CanonicalScenarioSetResponse(BaseModel):
    baseline: ScenarioResultResponse
    adverse: ScenarioResultResponse
    favorable: ScenarioResultResponse


class ScenarioEvaluateRequest(BaseModel):
    cargo_request_id: UUID
    commodity: Commodity
    cargo_volume_mt: float = Field(gt=0, description="Total cargo quantity in metric tonnes")
    vessel_class_id: str
    speed_knots: float = Field(gt=0)
    cargo_capacity_mt: float = Field(gt=0)
    fuel_consumption_mt_day: float = Field(gt=0)
    origin_berth_handling_rate_tpd: float = Field(gt=0)
    destination_berth_handling_rate_tpd: float = Field(gt=0)
    distance_nm: float = Field(ge=0)
    base_freight_rate: float = Field(gt=0)
    freight_unit: FreightUnit
    base_vlsfo_price_usd_mt: float = Field(gt=0)
    origin_waiting_hours: float = Field(ge=0)
    destination_waiting_hours: float = Field(ge=0)
    freight_change_pct: float = 0.0
    fuel_change_pct: float = 0.0
    delay_hours: float = Field(ge=0, default=0.0)
    congestion_level: CongestionLevel = CongestionLevel.MEDIUM
    forecast_spread_pct: float = Field(ge=0, default=0.0)


class RunCanonicalScenariosRequest(BaseModel):
    cargo_request_id: UUID
    commodity: Commodity
    cargo_volume_mt: float = Field(gt=0)
    vessel_class_id: str
    speed_knots: float = Field(gt=0)
    cargo_capacity_mt: float = Field(gt=0)
    fuel_consumption_mt_day: float = Field(gt=0)
    origin_berth_handling_rate_tpd: float = Field(gt=0)
    destination_berth_handling_rate_tpd: float = Field(gt=0)
    distance_nm: float = Field(ge=0)
    base_freight_rate: float = Field(gt=0)
    freight_unit: FreightUnit
    base_vlsfo_price_usd_mt: float = Field(gt=0)
    origin_waiting_hours: float = Field(ge=0)
    destination_waiting_hours: float = Field(ge=0)
    forecast_spread_pct: float = Field(ge=0, default=0.0)
