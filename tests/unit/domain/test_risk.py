"""Unit tests for DockTech V1 Risk Evaluator."""

from datetime import date
from uuid import uuid4
import pytest

from backend.app.domain.constants import Commodity, CongestionLevel, ContractHorizon, RiskLevel
from backend.app.domain.entities import CargoRequest
from backend.app.domain.risk import RiskEvaluator


def test_high_congestion_triggers_high_risk():
    """HIGH congestion must trigger HIGH risk."""
    risk = RiskEvaluator.evaluate_scenario_risk(
        congestion_level=CongestionLevel.HIGH,
        delay_hours=0.0,
    )
    assert risk == RiskLevel.HIGH


def test_severe_delay_triggers_high_risk():
    """Delay >= 36 hours must trigger HIGH risk."""
    risk = RiskEvaluator.evaluate_scenario_risk(
        congestion_level=CongestionLevel.LOW,
        delay_hours=48.0,
    )
    assert risk == RiskLevel.HIGH


def test_high_forecast_spread_triggers_high_risk():
    """Forecast spread >= 25% must trigger HIGH risk."""
    risk = RiskEvaluator.evaluate_scenario_risk(
        congestion_level=CongestionLevel.LOW,
        delay_hours=0.0,
        forecast_spread_pct=30.0,
    )
    assert risk == RiskLevel.HIGH


def test_medium_congestion_triggers_medium_risk():
    """MEDIUM congestion with moderate delay triggers MEDIUM risk."""
    risk = RiskEvaluator.evaluate_scenario_risk(
        congestion_level=CongestionLevel.MEDIUM,
        delay_hours=0.0,
    )
    assert risk == RiskLevel.MEDIUM


def test_moderate_delay_triggers_medium_risk():
    """Delay >= 12h triggers MEDIUM risk."""
    risk = RiskEvaluator.evaluate_scenario_risk(
        congestion_level=CongestionLevel.LOW,
        delay_hours=24.0,
    )
    assert risk == RiskLevel.MEDIUM


def test_low_risk_scenario():
    """LOW congestion, zero delay, low spread triggers LOW risk."""
    risk = RiskEvaluator.evaluate_scenario_risk(
        congestion_level=CongestionLevel.LOW,
        delay_hours=0.0,
        forecast_spread_pct=5.0,
    )
    assert risk == RiskLevel.LOW
