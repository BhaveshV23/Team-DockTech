"""
DockTech V1 — Cost Engine Service Unit Tests
==============================================
Tests for the CostEngineService application orchestration layer (C5).

Validates:
  1. Successful end-to-end service flow using CSVReferenceRepository → Resolver → Engine.
  2. Forecast freight rate override mechanism.
  3. Missing route/vessel/reference data domain error propagation.
  4. CostResult structural integrity and correctness.
  5. Scenario adjustment parameters passed through correctly.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from backend.app.domain.cost.models import CostInputs, CostResult, FreightUnit
from backend.app.domain.cost.errors import (
    InsufficientFeasibilityDataError,
    InsufficientFreightDataError,
    InsufficientFuelPriceDataError,
    InsufficientPortActivityDataError,
    RouteNotFoundError,
    VesselClassNotFoundError,
)
from backend.app.repositories.reference_repository import CSVReferenceRepository
from backend.app.services.cost_service import CostEngineService


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def reference_repo() -> CSVReferenceRepository:
    repo_root = Path(__file__).resolve().parent.parent
    data_dir = repo_root / "data" / "reference"
    return CSVReferenceRepository(data_dir=data_dir)


@pytest.fixture
def cost_service(reference_repo: CSVReferenceRepository) -> CostEngineService:
    return CostEngineService(repository=reference_repo)


# Standard test parameters
REF_DATE = datetime.date(2025, 6, 15)
CARGO_VOLUME = Decimal("75000.0")
ORIGIN = "NEWCASTLE"
DESTINATION = "PARADIP"
COMMODITY = "THERMAL_COAL"
VESSEL_CLASS = "PANAMAX"


# ==============================================================================
# 1. SUCCESSFUL END-TO-END SERVICE FLOW
# ==============================================================================

class TestCostEngineServiceEndToEnd:
    """Tests the full Repository → Resolver → Engine → CostResult pipeline."""

    def test_successful_usd_per_mt_calculation(self, cost_service: CostEngineService):
        result = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_MT",
            cost_reference_date=REF_DATE,
        )

        assert isinstance(result, CostResult)
        assert result.required_voyages == 2  # 75,000 MT / 72,000 MT capacity
        assert result.sailing_days_per_voyage > Decimal("0")
        assert result.expected_freight_cost > Decimal("0")
        assert result.total_fuel_cost_usd > Decimal("0")
        assert result.expected_total_cost > Decimal("0")
        assert result.effective_cost_per_mt > Decimal("0")
        assert result.freight_unit == FreightUnit.USD_PER_MT
        assert result.cost_reference_date == REF_DATE
        assert len(result.assumptions) > 0

    def test_successful_usd_per_day_calculation(self, cost_service: CostEngineService):
        result = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_DAY",
            cost_reference_date=REF_DATE,
        )

        assert isinstance(result, CostResult)
        assert result.required_voyages == 2
        assert result.freight_unit == FreightUnit.USD_PER_DAY
        assert result.expected_freight_cost > Decimal("0")
        assert result.expected_total_cost > Decimal("0")
        assert result.vessel_days_per_voyage > result.sailing_days_per_voyage

    def test_single_voyage_parcel(self, cost_service: CostEngineService):
        result = cost_service.calculate(
            cargo_volume_mt=Decimal("50000.0"),
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_MT",
            cost_reference_date=REF_DATE,
        )

        assert result.required_voyages == 1

    def test_result_is_deterministic(self, cost_service: CostEngineService):
        result_1 = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_MT",
            cost_reference_date=REF_DATE,
        )
        result_2 = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_MT",
            cost_reference_date=REF_DATE,
        )

        assert result_1 == result_2


# ==============================================================================
# 2. FORECAST FREIGHT RATE OVERRIDE
# ==============================================================================

class TestFreightRateOverride:
    """Tests the approved freight_rate_override mechanism."""

    def test_override_uses_supplied_rate(self, cost_service: CostEngineService):
        override_rate = Decimal("18.50")
        result = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_MT",
            cost_reference_date=REF_DATE,
            freight_rate_override=override_rate,
        )

        assert result.freight_rate_used == override_rate
        assert result.expected_freight_cost == CARGO_VOLUME * override_rate

    def test_override_differs_from_historical(self, cost_service: CostEngineService):
        # Without override → historical rate from CSV
        result_historical = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_MT",
            cost_reference_date=REF_DATE,
        )

        # With override → explicit forecast rate
        override_rate = Decimal("99.99")
        result_override = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_MT",
            cost_reference_date=REF_DATE,
            freight_rate_override=override_rate,
        )

        assert result_override.freight_rate_used == override_rate
        assert result_override.freight_rate_used != result_historical.freight_rate_used
        assert result_override.expected_freight_cost != result_historical.expected_freight_cost

    def test_override_usd_per_day(self, cost_service: CostEngineService):
        override_rate = Decimal("20000.0")
        result = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_DAY",
            cost_reference_date=REF_DATE,
            freight_rate_override=override_rate,
        )

        assert result.freight_rate_used == override_rate
        assert result.freight_unit == FreightUnit.USD_PER_DAY


# ==============================================================================
# 3. MISSING REFERENCE DATA ERROR PROPAGATION
# ==============================================================================

class TestErrorPropagation:
    """Tests that canonical domain errors propagate transparently through the service."""

    def test_route_not_found(self, cost_service: CostEngineService):
        with pytest.raises(RouteNotFoundError):
            cost_service.calculate(
                cargo_volume_mt=CARGO_VOLUME,
                origin_port_id="NON_EXISTENT_PORT",
                destination_port_id=DESTINATION,
                commodity=COMMODITY,
                vessel_class_id=VESSEL_CLASS,
                freight_unit="USD_PER_MT",
                cost_reference_date=REF_DATE,
            )

    def test_vessel_class_not_found(self, cost_service: CostEngineService):
        with pytest.raises(VesselClassNotFoundError):
            cost_service.calculate(
                cargo_volume_mt=CARGO_VOLUME,
                origin_port_id=ORIGIN,
                destination_port_id=DESTINATION,
                commodity=COMMODITY,
                vessel_class_id="NONEXISTENT_VESSEL",
                freight_unit="USD_PER_MT",
                cost_reference_date=REF_DATE,
            )

    def test_berth_infeasibility_propagates(self, cost_service: CostEngineService):
        # Capesize draft exceeds Paradip thermal berth constraints
        with pytest.raises(InsufficientFeasibilityDataError):
            cost_service.calculate(
                cargo_volume_mt=Decimal("150000.0"),
                origin_port_id=ORIGIN,
                destination_port_id=DESTINATION,
                commodity=COMMODITY,
                vessel_class_id="CAPESIZE",
                freight_unit="USD_PER_MT",
                cost_reference_date=REF_DATE,
            )

    def test_no_vlsfo_price_before_date(self, cost_service: CostEngineService):
        # Reference date before any observations
        with pytest.raises(InsufficientFuelPriceDataError):
            cost_service.calculate(
                cargo_volume_mt=CARGO_VOLUME,
                origin_port_id=ORIGIN,
                destination_port_id=DESTINATION,
                commodity=COMMODITY,
                vessel_class_id=VESSEL_CLASS,
                freight_unit="USD_PER_MT",
                cost_reference_date=datetime.date(2020, 1, 1),
            )

    def test_no_port_activity_before_date(self, cost_service: CostEngineService):
        # Reference date before any port activity observations
        with pytest.raises((InsufficientPortActivityDataError, InsufficientFuelPriceDataError)):
            cost_service.calculate(
                cargo_volume_mt=CARGO_VOLUME,
                origin_port_id=ORIGIN,
                destination_port_id=DESTINATION,
                commodity=COMMODITY,
                vessel_class_id=VESSEL_CLASS,
                freight_unit="USD_PER_MT",
                cost_reference_date=datetime.date(2019, 1, 1),
            )

    def test_no_freight_rate_without_override(self, cost_service: CostEngineService):
        # Very early date where no freight rate exists — but VLSFO or port_activity
        # may fail first. Accept either domain error.
        with pytest.raises((
            InsufficientFreightDataError,
            InsufficientFuelPriceDataError,
            InsufficientPortActivityDataError,
        )):
            cost_service.calculate(
                cargo_volume_mt=CARGO_VOLUME,
                origin_port_id=ORIGIN,
                destination_port_id=DESTINATION,
                commodity=COMMODITY,
                vessel_class_id=VESSEL_CLASS,
                freight_unit="USD_PER_MT",
                cost_reference_date=datetime.date(2018, 1, 1),
            )


# ==============================================================================
# 4. COST RESULT STRUCTURAL INTEGRITY
# ==============================================================================

class TestCostResultIntegrity:
    """Tests that CostResult fields are structurally correct and consistent."""

    def test_total_cost_is_sum_of_components(self, cost_service: CostEngineService):
        result = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_MT",
            cost_reference_date=REF_DATE,
        )

        expected_total = (
            result.expected_freight_cost
            + result.total_fuel_cost_usd
            + result.port_costs_usd
        )
        assert result.expected_total_cost == expected_total

    def test_effective_cost_per_mt_calculation(self, cost_service: CostEngineService):
        result = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_MT",
            cost_reference_date=REF_DATE,
        )

        expected_per_mt = result.expected_total_cost / CARGO_VOLUME
        assert result.effective_cost_per_mt == expected_per_mt

    def test_vessel_days_equals_sailing_plus_port(self, cost_service: CostEngineService):
        result = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_MT",
            cost_reference_date=REF_DATE,
        )

        expected_vessel_days = result.sailing_days_per_voyage + result.port_days_per_voyage
        assert result.vessel_days_per_voyage == expected_vessel_days

    def test_cost_reference_date_preserved(self, cost_service: CostEngineService):
        result = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_MT",
            cost_reference_date=REF_DATE,
        )

        assert result.cost_reference_date == REF_DATE

    def test_port_costs_default_zero(self, cost_service: CostEngineService):
        result = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_MT",
            cost_reference_date=REF_DATE,
        )

        assert result.port_costs_usd == Decimal("0.0")

    def test_explicit_port_costs_included(self, cost_service: CostEngineService):
        port_costs = Decimal("25000.0")
        result = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_MT",
            cost_reference_date=REF_DATE,
            port_costs_usd=port_costs,
        )

        assert result.port_costs_usd == port_costs
        # Total = freight + fuel + port_costs
        expected_total = (
            result.expected_freight_cost
            + result.total_fuel_cost_usd
            + port_costs
        )
        assert result.expected_total_cost == expected_total


# ==============================================================================
# 5. SCENARIO PARAMETERS PASSED CORRECTLY
# ==============================================================================

class TestScenarioPassthrough:
    """Tests that scenario adjustments flow through correctly without service-level logic."""

    def test_scenario_delay_increases_turnaround(self, cost_service: CostEngineService):
        result_baseline = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_MT",
            cost_reference_date=REF_DATE,
            scenario_delay_hours=Decimal("0.0"),
        )
        result_delayed = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_MT",
            cost_reference_date=REF_DATE,
            scenario_delay_hours=Decimal("48.0"),
        )

        assert result_delayed.scenario_delay_hours_total > result_baseline.scenario_delay_hours_total
        assert result_delayed.estimated_turnaround_hours > result_baseline.estimated_turnaround_hours

    def test_freight_adjustment_changes_freight_cost(self, cost_service: CostEngineService):
        result_baseline = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_MT",
            cost_reference_date=REF_DATE,
            freight_adjustment_pct=Decimal("0.0"),
        )
        result_shocked = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_MT",
            cost_reference_date=REF_DATE,
            freight_adjustment_pct=Decimal("15.0"),
        )

        assert result_shocked.freight_rate_used > result_baseline.freight_rate_used
        assert result_shocked.expected_freight_cost > result_baseline.expected_freight_cost

    def test_fuel_adjustment_changes_fuel_cost(self, cost_service: CostEngineService):
        result_baseline = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_MT",
            cost_reference_date=REF_DATE,
            fuel_adjustment_pct=Decimal("0.0"),
        )
        result_shocked = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_MT",
            cost_reference_date=REF_DATE,
            fuel_adjustment_pct=Decimal("20.0"),
        )

        assert result_shocked.vlsfo_price_used > result_baseline.vlsfo_price_used
        assert result_shocked.total_fuel_cost_usd > result_baseline.total_fuel_cost_usd

    def test_combined_scenario_adjustments(self, cost_service: CostEngineService):
        result_baseline = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_MT",
            cost_reference_date=REF_DATE,
        )
        result_adverse = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_MT",
            cost_reference_date=REF_DATE,
            scenario_delay_hours=Decimal("72.0"),
            freight_adjustment_pct=Decimal("20.0"),
            fuel_adjustment_pct=Decimal("15.0"),
        )

        assert result_adverse.expected_total_cost > result_baseline.expected_total_cost
        assert result_adverse.scenario_delay_hours_total > Decimal("0")
        assert result_adverse.freight_rate_used > result_baseline.freight_rate_used
        assert result_adverse.vlsfo_price_used > result_baseline.vlsfo_price_used

    def test_negative_freight_adjustment_reduces_cost(self, cost_service: CostEngineService):
        result_baseline = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_MT",
            cost_reference_date=REF_DATE,
        )
        result_favorable = cost_service.calculate(
            cargo_volume_mt=CARGO_VOLUME,
            origin_port_id=ORIGIN,
            destination_port_id=DESTINATION,
            commodity=COMMODITY,
            vessel_class_id=VESSEL_CLASS,
            freight_unit="USD_PER_MT",
            cost_reference_date=REF_DATE,
            freight_adjustment_pct=Decimal("-10.0"),
        )

        assert result_favorable.freight_rate_used < result_baseline.freight_rate_used
        assert result_favorable.expected_freight_cost < result_baseline.expected_freight_cost
