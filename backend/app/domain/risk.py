"""Risk Evaluation Engine for DockTech V1.

Implements qualitative, explainable risk assessment heuristics according to PRD.md Section 5
and DATA_DICTIONARY.md Section 6.
"""

from typing import Optional

from backend.app.domain.constants import CongestionLevel, RiskLevel
from backend.app.domain.entities import CargoRequest, VoyageCostBreakdown


class RiskEvaluator:
    """Evaluates qualitative operational and market risk levels (LOW, MEDIUM, HIGH)."""

    @classmethod
    def evaluate_scenario_risk(
        cls,
        congestion_level: CongestionLevel,
        delay_hours: float,
        cost_breakdown: Optional[VoyageCostBreakdown] = None,
        cargo_request: Optional[CargoRequest] = None,
        forecast_spread_pct: float = 0.0,
    ) -> RiskLevel:
        """Evaluates overall scenario risk using transparent, documented decision rules.
        
        Rules:
        - HIGH:
          * Congestion level is HIGH, OR
          * Scenario delay >= 36 hours, OR
          * Delivery window laycan is exceeded by total turnaround + transit, OR
          * Forecast uncertainty spread >= 25%.
        - MEDIUM:
          * Congestion level is MEDIUM, OR
          * Scenario delay >= 12 hours, OR
          * Forecast uncertainty spread >= 10%.
        - LOW:
          * Congestion level is LOW, AND
          * Scenario delay < 12 hours, AND
          * Forecast uncertainty spread < 10%.
        """
        # 1. Check HIGH risk criteria
        if congestion_level == CongestionLevel.HIGH:
            return RiskLevel.HIGH
        if delay_hours >= 36.0:
            return RiskLevel.HIGH
        if forecast_spread_pct >= 25.0:
            return RiskLevel.HIGH

        if cargo_request and cost_breakdown:
            laycan_duration_days = (
                cargo_request.laycan_end_date - cargo_request.laycan_start_date
            ).days
            total_operation_days = (
                cost_breakdown.sailing_days + (cost_breakdown.estimated_turnaround_hours / 24.0)
            )
            if laycan_duration_days > 0 and total_operation_days > laycan_duration_days:
                return RiskLevel.HIGH

        # 2. Check MEDIUM risk criteria
        if congestion_level == CongestionLevel.MEDIUM:
            return RiskLevel.MEDIUM
        if delay_hours >= 12.0:
            return RiskLevel.MEDIUM
        if forecast_spread_pct >= 10.0:
            return RiskLevel.MEDIUM

        # 3. LOW risk criteria
        return RiskLevel.LOW
