"""Scenario orchestration service for DockTech V1.

Coordinates baseline decision inputs with canonical scenario defaults,
computes parameter shocks, and produces structured scenario comparison results.
"""

from typing import List, Optional
from uuid import UUID

from backend.app.domain.constants import ScenarioType
from backend.app.domain.entities import (
    DecisionInputs,
    ScenarioDefault,
    ScenarioResult,
    ScenarioResultSet,
)
from backend.app.domain.scenario import (
    ScenarioComparison,
    ScenarioEngine,
    ScenarioParameterShock,
)
from backend.app.repositories.scenario_repository import ScenarioRepository


class ScenarioService:
    """Service layer orchestrating multi-scenario sensitivity and shock simulations."""

    def __init__(self, repository: Optional[ScenarioRepository] = None):
        self.repository = repository or ScenarioRepository()

    def get_scenario_defaults(self) -> List[ScenarioDefault]:
        """Loads canonical scenario presets (BASELINE, ADVERSE, FAVORABLE)."""
        return self.repository.get_scenario_defaults()

    def run_scenarios(
        self, base_inputs: DecisionInputs, persist: bool = True
    ) -> ScenarioResultSet:
        """Runs the three canonical scenarios (BASELINE, ADVERSE, FAVORABLE) for a chartering decision.
        
        Guarantees:
        - Exactly three scenario results returned.
        - Canonical default values used.
        - Results persisted to database if persist=True.
        """
        defaults = {d.scenario_id: d for d in self.get_scenario_defaults()}

        # 1. BASELINE
        baseline_def = defaults[ScenarioType.BASELINE]
        baseline_shock = ScenarioParameterShock(
            freight_change_pct=baseline_def.freight_change_pct,
            fuel_change_pct=baseline_def.fuel_change_pct,
            delay_hours=baseline_def.delay_hours,
            congestion_level=baseline_def.port_congestion_level,
        )
        baseline_result = ScenarioEngine.apply_scenario(
            base_inputs=base_inputs,
            scenario_type=ScenarioType.BASELINE,
            shock=baseline_shock,
        )

        # 2. ADVERSE
        adverse_def = defaults[ScenarioType.ADVERSE]
        adverse_shock = ScenarioParameterShock(
            freight_change_pct=adverse_def.freight_change_pct,
            fuel_change_pct=adverse_def.fuel_change_pct,
            delay_hours=adverse_def.delay_hours,
            congestion_level=adverse_def.port_congestion_level,
        )
        adverse_result = ScenarioEngine.apply_scenario(
            base_inputs=base_inputs,
            scenario_type=ScenarioType.ADVERSE,
            shock=adverse_shock,
        )

        # 3. FAVORABLE
        favorable_def = defaults[ScenarioType.FAVORABLE]
        favorable_shock = ScenarioParameterShock(
            freight_change_pct=favorable_def.freight_change_pct,
            fuel_change_pct=favorable_def.fuel_change_pct,
            delay_hours=favorable_def.delay_hours,
            congestion_level=favorable_def.port_congestion_level,
        )
        favorable_result = ScenarioEngine.apply_scenario(
            base_inputs=base_inputs,
            scenario_type=ScenarioType.FAVORABLE,
            shock=favorable_shock,
        )

        if persist:
            self.repository.save_scenario_result(baseline_result)
            self.repository.save_scenario_result(adverse_result)
            self.repository.save_scenario_result(favorable_result)

        return ScenarioResultSet(
            baseline=baseline_result,
            adverse=adverse_result,
            favorable=favorable_result,
        )

    def evaluate_custom_scenario(
        self,
        base_inputs: DecisionInputs,
        shock: ScenarioParameterShock,
        scenario_type: ScenarioType = ScenarioType.ADVERSE,
        persist: bool = False,
    ) -> ScenarioComparison:
        """Evaluates a user-adjusted parameter shock and compares against baseline."""
        # Baseline
        baseline_def = self.repository.get_scenario_default_by_type(ScenarioType.BASELINE)
        baseline_shock = ScenarioParameterShock(
            freight_change_pct=baseline_def.freight_change_pct,
            fuel_change_pct=baseline_def.fuel_change_pct,
            delay_hours=baseline_def.delay_hours,
            congestion_level=baseline_def.port_congestion_level,
        )
        baseline_result = ScenarioEngine.apply_scenario(
            base_inputs=base_inputs,
            scenario_type=ScenarioType.BASELINE,
            shock=baseline_shock,
        )

        # Custom scenario
        custom_result = ScenarioEngine.apply_scenario(
            base_inputs=base_inputs,
            scenario_type=scenario_type,
            shock=shock,
        )

        if persist:
            self.repository.save_scenario_result(custom_result)

        return ScenarioEngine.compare_scenarios(
            baseline=baseline_result, scenario=custom_result
        )

    def get_saved_scenarios(self, cargo_request_id: UUID) -> List[ScenarioResult]:
        """Retrieves stored scenario results for a cargo request."""
        return self.repository.get_scenarios_by_cargo_request(cargo_request_id)
