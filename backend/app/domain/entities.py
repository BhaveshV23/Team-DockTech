"""Framework-independent domain entities for DockTech V1."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from backend.app.domain.constants import (
    Commodity,
    CongestionLevel,
    ContractHorizon,
    FreightUnit,
    RiskLevel,
    ScenarioType,
)


@dataclass(frozen=True)
class Port:
    """Port domain entity representing macro-level planning envelope."""

    port_id: str
    port_name: str
    country: str
    max_loa_m: float
    max_beam_m: float
    max_draft_m: float
    handling_rate_tpd: float
    typical_turnaround_hours: float
    source: str = "SYNTHETIC_GENERATOR_V1"
    data_type: str = "SYNTHETIC"


@dataclass(frozen=True)
class Berth:
    """Berth domain entity representing terminal operational constraints."""

    berth_id: str
    port_id: str
    berth_name: str
    commodity: str
    max_loa_m: float
    max_beam_m: float
    max_draft_m: float
    handling_rate_tpd: float
    source: str = "SYNTHETIC_GENERATOR_V1"
    data_type: str = "SYNTHETIC"


@dataclass(frozen=True)
class VesselClass:
    """Vessel class domain entity representing physical dimensions and payload capacity."""

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
    source: str = "SYNTHETIC_GENERATOR_V1"
    data_type: str = "SYNTHETIC"


@dataclass(frozen=True)
class Route:
    """Route domain entity representing origin-destination trade lane."""

    route_id: str
    origin_port_id: str
    destination_port_id: str
    commodity: str
    distance_nm: float
    typical_sailing_days: float
    source: str = "SYNTHETIC_GENERATOR_V1"
    data_type: str = "SYNTHETIC"


@dataclass(frozen=True)
class CargoRequest:
    cargo_request_id: UUID
    user_id: UUID
    commodity: Commodity
    cargo_volume_mt: float
    origin_port_id: str
    destination_port_id: str
    laycan_start_date: date
    laycan_end_date: date
    contract_horizon: ContractHorizon
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class ScenarioDefault:
    scenario_id: ScenarioType
    scenario_name: str
    freight_change_pct: float
    fuel_change_pct: float
    delay_hours: float
    port_congestion_level: CongestionLevel
    description: str


@dataclass(frozen=True)
class DecisionInputs:
    cargo_request: CargoRequest
    vessel_class: VesselClass
    origin_berth: Berth
    destination_berth: Berth
    route: Route
    base_freight_rate: float
    freight_unit: FreightUnit
    base_vlsfo_price_usd_mt: float
    origin_waiting_hours: float
    destination_waiting_hours: float
    cost_reference_date: date
    forecast_spread_pct: float = 0.0


@dataclass(frozen=True)
class VoyageCostBreakdown:
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


@dataclass(frozen=True)
class ScenarioResult:
    scenario_instance_id: UUID
    cargo_request_id: UUID
    scenario_type: ScenarioType
    freight_change_pct: float
    fuel_change_pct: float
    delay_hours: float
    congestion_level: CongestionLevel
    estimated_total_cost: float
    estimated_turnaround_hours: float
    cost_breakdown: VoyageCostBreakdown
    risk_level: RiskLevel
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class ScenarioResultSet:
    baseline: ScenarioResult
    adverse: ScenarioResult
    favorable: ScenarioResult

    def as_list(self) -> list[ScenarioResult]:
        return [self.baseline, self.adverse, self.favorable]
