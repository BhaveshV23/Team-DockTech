"""Request and frozen response schemas for recommendations."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.app.domain.constants import ContractStrategy, FeasibilityStatus, MarketEntryAction, RiskLevel
from backend.app.domain.cost.models import FreightUnit
from backend.app.domain.recommendation.models import RecommendationConfidence


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cargo_request_id: UUID
    forecast_horizon: int = Field(default=30, ge=1, le=365)
    freight_unit: FreightUnit = FreightUnit.USD_PER_MT


class CandidateComparisonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vessel_class_id: str
    feasibility_status: FeasibilityStatus
    expected_freight_cost: Decimal
    expected_total_cost: Decimal
    effective_cost_per_mt: Decimal
    estimated_turnaround_hours: Decimal
    required_voyages: int
    risk_level: RiskLevel


class RecommendationResponse(BaseModel):
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
    candidate_comparisons: list[CandidateComparisonResponse] = Field(default_factory=list)
