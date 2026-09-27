"""Immutable evidence and result types for recommendation decisions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from backend.app.domain.constants import (
    Commodity,
    ContractHorizon,
    ContractStrategy,
    FeasibilityStatus,
    FreightUnit,
    MarketEntryAction,
    RiskLevel,
    ScenarioType,
)
from backend.app.domain.entities import Route


class RecommendationConfidence(str, Enum):
    """Qualitative evidence-strength label, never a probability."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class ForecastPointEvidence:
    forecast_date: date
    lower_value: Decimal
    central_value: Decimal
    upper_value: Decimal
    unit: FreightUnit


@dataclass(frozen=True)
class ForecastRunEvidence:
    forecast_run_id: UUID
    cargo_request_id: UUID
    route_id: str
    vessel_class_id: str
    freight_unit: FreightUnit
    points: tuple[ForecastPointEvidence, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "points", tuple(self.points))


@dataclass(frozen=True)
class CostEvidence:
    cargo_request_id: UUID
    route_id: str
    vessel_class_id: str
    forecast_run_id: UUID
    freight_unit: FreightUnit
    freight_rate_used: Decimal
    expected_freight_cost: Decimal
    expected_total_cost: Decimal
    effective_cost_per_mt: Decimal
    estimated_turnaround_hours: Decimal
    sailing_days_per_voyage: Decimal
    required_voyages: int


@dataclass(frozen=True)
class ScenarioRiskEvidence:
    scenario_type: ScenarioType
    risk_level: RiskLevel
    cargo_request_id: UUID
    route_id: str
    vessel_class_id: str
    forecast_run_id: UUID


@dataclass(frozen=True)
class CandidateEvidence:
    vessel_class_id: str
    cargo_capacity_mt: Decimal
    feasibility_status: FeasibilityStatus
    feasibility_is_feasible: bool
    feasibility_cargo_request_id: UUID
    feasibility_commodity: Commodity
    feasibility_origin_port_id: str
    feasibility_destination_port_id: str
    feasibility_cargo_volume_mt: Decimal
    feasibility_required_voyages: int | None
    forecast_run: ForecastRunEvidence
    cost: CostEvidence
    scenario_risks: tuple[ScenarioRiskEvidence, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "scenario_risks", tuple(self.scenario_risks))


@dataclass(frozen=True)
class RecommendationInput:
    recommendation_id: UUID
    created_at: datetime
    cargo_request_id: UUID
    commodity: Commodity
    cargo_volume_mt: Decimal
    origin_port_id: str
    destination_port_id: str
    route: Route
    laycan_start_date: date
    laycan_end_date: date
    contract_horizon: ContractHorizon
    candidates: tuple[CandidateEvidence, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidates", tuple(self.candidates))


@dataclass(frozen=True)
class RecommendationResult:
    recommendation_id: UUID
    cargo_request_id: UUID
    forecast_run_id: UUID
    recommended_vessel_class_id: str
    market_entry_action: MarketEntryAction
    contract_strategy: ContractStrategy
    expected_freight_cost: Decimal
    expected_total_cost: Decimal
    estimated_turnaround_hours: Decimal
    risk_level: RiskLevel
    confidence: RecommendationConfidence
    rationale: str
    assumptions: str
    created_at: datetime
    trend: str
    forecast_uncertainty: tuple[Decimal, Decimal, Decimal]
    required_voyages: int
