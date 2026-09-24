"""Pure Domain Scenario Simulation Models for DockTech V1.

Applies parameter shocks to baseline decision inputs and generates structured comparison results.
"""

from dataclasses import dataclass
from uuid import uuid4

from backend.app.domain.constants import CongestionLevel, RiskLevel, ScenarioType
from backend.app.domain.entities import (
    DecisionInputs,
    ScenarioDefault,
    ScenarioResult,
    ScenarioResultSet,
)
from backend.app.domain.risk import RiskEvaluator
from backend.app.domain.voyage_cost import VoyageCostEngine


@dataclass(frozen=True)
class ScenarioParameterShock:
    freight_change_pct: float
    fuel_change_pct: float
    delay_hours: float
    congestion_level: CongestionLevel


@dataclass(frozen=True)
class ScenarioComparison:
    baseline_result: ScenarioResult
    scenario_result: ScenarioResult
    delta_cost_usd: float
    delta_cost_pct: float
    delta_turnaround_hours: float
    delta_effective_cost_per_mt: float
    risk_transition: str


class ScenarioEngine:
    """Core domain calculator for applying parameter shocks and computing scenario outcomes."""

    @classmethod
    def apply_scenario(
        cls,
        base_inputs: DecisionInputs,
        scenario_type: ScenarioType,
        shock: ScenarioParameterShock,
    ) -> ScenarioResult:
        """Applies a parameter shock to base decision inputs and calculates the scenario outcome.
        
        Strict rules:
        - Shocked freight rate = base_freight_rate * (1 + freight_change_pct / 100)
        - Shocked VLSFO price = base_vlsfo_price * (1 + fuel_change_pct / 100)
        - Delay hours applied per voyage call.
        - Risk evaluated based on scenario assumptions and resulting operation.
        """
        multiplier_freight = 1.0 + (shock.freight_change_pct / 100.0)
        multiplier_fuel = 1.0 + (shock.fuel_change_pct / 100.0)

        shocked_freight_rate = max(0.01, base_inputs.base_freight_rate * multiplier_freight)
        shocked_vlsfo_price = max(0.01, base_inputs.base_vlsfo_price_usd_mt * multiplier_fuel)

        cost_breakdown = VoyageCostEngine.calculate_voyage_cost(
            cargo_volume_mt=base_inputs.cargo_request.cargo_volume_mt,
            vessel_class=base_inputs.vessel_class,
            origin_berth=base_inputs.origin_berth,
            destination_berth=base_inputs.destination_berth,
            route=base_inputs.route,
            freight_rate=shocked_freight_rate,
            freight_unit=base_inputs.freight_unit,
            vlsfo_price_usd_mt=shocked_vlsfo_price,
            origin_waiting_hours=base_inputs.origin_waiting_hours,
            destination_waiting_hours=base_inputs.destination_waiting_hours,
            scenario_delay_hours=shock.delay_hours,
        )

        risk_level = RiskEvaluator.evaluate_scenario_risk(
            congestion_level=shock.congestion_level,
            delay_hours=shock.delay_hours,
            cost_breakdown=cost_breakdown,
            cargo_request=base_inputs.cargo_request,
            forecast_spread_pct=base_inputs.forecast_spread_pct,
        )

        return ScenarioResult(
            scenario_instance_id=uuid4(),
            cargo_request_id=base_inputs.cargo_request.cargo_request_id,
            scenario_type=scenario_type,
            freight_change_pct=shock.freight_change_pct,
            fuel_change_pct=shock.fuel_change_pct,
            delay_hours=shock.delay_hours,
            congestion_level=shock.congestion_level,
            estimated_total_cost=cost_breakdown.expected_total_cost,
            estimated_turnaround_hours=cost_breakdown.estimated_turnaround_hours,
            cost_breakdown=cost_breakdown,
            risk_level=risk_level,
        )

    @classmethod
    def compare_scenarios(
        cls, baseline: ScenarioResult, scenario: ScenarioResult
    ) -> ScenarioComparison:
        """Calculates delta comparison between baseline and scenario outcome."""
        delta_cost_usd = round(
            scenario.estimated_total_cost - baseline.estimated_total_cost, 2
        )
        delta_cost_pct = (
            round((delta_cost_usd / baseline.estimated_total_cost) * 100.0, 2)
            if baseline.estimated_total_cost > 0
            else 0.0
        )
        delta_turnaround_hours = round(
            scenario.estimated_turnaround_hours - baseline.estimated_turnaround_hours, 2
        )
        delta_effective_cost_per_mt = round(
            scenario.cost_breakdown.effective_cost_per_mt
            - baseline.cost_breakdown.effective_cost_per_mt,
            4,
        )
        risk_transition = f"{baseline.risk_level.value} -> {scenario.risk_level.value}"

        return ScenarioComparison(
            baseline_result=baseline,
            scenario_result=scenario,
            delta_cost_usd=delta_cost_usd,
            delta_cost_pct=delta_cost_pct,
            delta_turnaround_hours=delta_turnaround_hours,
            delta_effective_cost_per_mt=delta_effective_cost_per_mt,
            risk_transition=risk_transition,
        )
