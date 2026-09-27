"""Pure Domain Scenario Simulation Models for DockTech V1.

Applies parameter shocks to baseline decision inputs and generates structured comparison results.
"""

from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

from backend.app.domain.constants import CongestionLevel, RiskLevel, ScenarioType
from backend.app.domain.cost import CostInputs, CostResult, FreightUnit, calculate_cost
from backend.app.domain.entities import (
    DecisionInputs,
    ScenarioResult,
    VoyageCostBreakdown,
)
from backend.app.domain.risk import RiskEvaluator


def _to_cost_breakdown(cost_result: CostResult) -> VoyageCostBreakdown:
    """Convert canonical CostResult into the historical VoyageCostBreakdown shape used by Scenario/Risk consumers."""
    turnaround_per_voyage = (
        cost_result.estimated_turnaround_hours / cost_result.required_voyages
        if cost_result.required_voyages
        else Decimal("0")
    )
    return VoyageCostBreakdown(
        sailing_days=float(cost_result.sailing_days_per_voyage),
        required_voyages=cost_result.required_voyages,
        origin_handling_hours_total=float(cost_result.origin_handling_hours_total),
        destination_handling_hours_total=float(cost_result.dest_handling_hours_total),
        waiting_hours_total=float(cost_result.waiting_hours_total),
        scenario_delay_total=float(cost_result.scenario_delay_hours_total),
        estimated_turnaround_hours=float(cost_result.estimated_turnaround_hours),
        turnaround_hours_per_voyage=float(turnaround_per_voyage),
        port_days_per_voyage=float(cost_result.port_days_per_voyage),
        vessel_days_per_voyage=float(cost_result.vessel_days_per_voyage),
        total_fuel_cost_usd=float(round(cost_result.total_fuel_cost_usd, 2)),
        expected_freight_cost=float(round(cost_result.expected_freight_cost, 2)),
        expected_total_cost=float(round(cost_result.expected_total_cost, 2)),
        effective_cost_per_mt=float(cost_result.effective_cost_per_mt),
    )


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

        freight_unit = FreightUnit(base_inputs.freight_unit.value)

        canonical_inputs = CostInputs(
            cargo_volume_mt=Decimal(str(base_inputs.cargo_request.cargo_volume_mt)),
            distance_nm=Decimal(str(base_inputs.route.distance_nm)),
            vessel_cargo_capacity_mt=Decimal(str(base_inputs.vessel_class.cargo_capacity_mt)),
            vessel_speed_knots=Decimal(str(base_inputs.vessel_class.speed_knots)),
            vessel_fuel_consumption_tpd=Decimal(str(base_inputs.vessel_class.fuel_consumption_mt_day)),
            freight_rate_value=Decimal(str(shocked_freight_rate)),
            freight_unit=freight_unit,
            vlsfo_price_usd_per_mt=Decimal(str(shocked_vlsfo_price)),
            origin_handling_rate_tpd=Decimal(str(base_inputs.origin_berth.handling_rate_tpd)),
            dest_handling_rate_tpd=Decimal(str(base_inputs.destination_berth.handling_rate_tpd)),
            origin_waiting_hours=Decimal(str(base_inputs.origin_waiting_hours)),
            dest_waiting_hours=Decimal(str(base_inputs.destination_waiting_hours)),
            scenario_delay_hours=Decimal(str(shock.delay_hours)),
        )
        cost_result = calculate_cost(canonical_inputs, base_inputs.cost_reference_date)
        cost_breakdown = _to_cost_breakdown(cost_result)

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
