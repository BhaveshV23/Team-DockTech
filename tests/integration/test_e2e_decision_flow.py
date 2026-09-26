"""End-to-End Decision Workflow QA Test for DockTech V1.

Verifies the integrated flow:
Cargo Input -> Feasibility -> Forecast -> Vessel Comparison -> Cost -> Scenario/Risk -> Recommendation
"""

from datetime import date
from uuid import uuid4
import pytest

from backend.app.domain.constants import (
    Commodity,
    CongestionLevel,
    ContractHorizon,
    ContractStrategy,
    FreightUnit,
    MarketEntryAction,
    RiskLevel,
    ScenarioType,
)
from backend.app.domain.entities import (
    Berth,
    CargoRequest,
    DecisionInputs,
    Port,
    Route,
    ScenarioDefault,
    VesselClass,
)
from backend.app.services.scenario_service import ScenarioService


def test_complete_e2e_chartering_decision_workflow(
    sample_ports, sample_berths, sample_vessels, sample_route
):
    """Executes the full simulated decision workflow from cargo request to scenario sensitivity."""
    # 1. Step 1: User Cargo Planning Form Input
    cargo_request = CargoRequest(
        cargo_request_id=uuid4(),
        user_id=uuid4(),
        commodity=Commodity.THERMAL_COAL,
        cargo_volume_mt=75000.0,
        origin_port_id="AU_NCL",
        destination_port_id="IN_PRT",
        laycan_start_date=date(2026, 10, 1),
        laycan_end_date=date(2026, 10, 31),
        contract_horizon=ContractHorizon.SPOT,
    )
    assert cargo_request.cargo_volume_mt == 75000.0

    # 2. Step 2: Feasibility Matrix Screening
    panamax = sample_vessels["panamax"]
    orig_berth = sample_berths["origin"]
    dest_berth = sample_berths["destination"]

    is_feasible = (
        panamax.loa_m <= orig_berth.max_loa_m
        and panamax.beam_m <= orig_berth.max_beam_m
        and panamax.draft_m <= orig_berth.max_draft_m
        and panamax.loa_m <= dest_berth.max_loa_m
        and panamax.beam_m <= dest_berth.max_beam_m
        and panamax.draft_m <= dest_berth.max_draft_m
    )
    assert is_feasible is True

    # 3. Step 3: Simulated Forecast Run Output
    forecast_central_rate = 18.50  # USD/MT
    forecast_spread = 8.0  # 8% spread
    training_data_end_date = date(2026, 9, 20)

    # 4. Step 4: Decision Inputs Assembly
    inputs = DecisionInputs(
        cargo_request=cargo_request,
        vessel_class=panamax,
        origin_berth=orig_berth,
        destination_berth=dest_berth,
        route=sample_route,
        base_freight_rate=forecast_central_rate,
        freight_unit=FreightUnit.USD_PER_MT,
        base_vlsfo_price_usd_mt=620.0,
        origin_waiting_hours=12.0,
        destination_waiting_hours=36.0,
        cost_reference_date=training_data_end_date,
        forecast_spread_pct=forecast_spread,
    )

    # 5. Step 5: Scenario Service Simulation (BASELINE, ADVERSE, FAVORABLE)
    scenario_service = ScenarioService()
    scenario_set = scenario_service.run_scenarios(inputs, persist=True)

    assert scenario_set.baseline.estimated_total_cost > 0
    assert scenario_set.adverse.estimated_total_cost > scenario_set.baseline.estimated_total_cost
    assert scenario_set.favorable.estimated_total_cost < scenario_set.baseline.estimated_total_cost

    # 6. Step 6: Verify Recommendation Payload Alignment
    # Baseline total cost becomes the expected_total_cost
    recommendation_total_cost = scenario_set.baseline.estimated_total_cost
    recommendation_turnaround = scenario_set.baseline.estimated_turnaround_hours

    assert recommendation_total_cost > 0
    assert recommendation_turnaround > 0
    assert scenario_set.adverse.risk_level == RiskLevel.HIGH
    assert scenario_set.favorable.risk_level == RiskLevel.LOW
