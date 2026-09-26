"""
DockTech V1 — Cost Engine Domain Models & Value Objects
========================================================
Pure domain models and immutable value objects for the DockTech V1 Cost Engine.

Authoritative Source-of-Truth Documents:
  1. PRD.md
  2. DATA_DICTIONARY.md (Frozen Canonical Contract)
  3. ARCHITECTURE.md (Domain Layer Isolation)
  4. C1 Cost Engine Contract

Guarantees:
  - 100% Pure Python & Framework-Independent (No FastAPI, SQL, ORM, or network calls).
  - Exact Decimal representation for all monetary and physical measurement values.
  - Immutability via frozen dataclasses.
  - Strict domain validation for physical/operational quantities.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Sequence

from .errors import InvalidCargoVolumeError, InvalidFreightUnitError


# ==============================================================================
# 1. FREIGHT UNIT ENUMERATION
# ==============================================================================

class FreightUnit(str, Enum):
    """
    Canonical freight units supported in DockTech V1.
    
    Controlled values:
      - USD_PER_MT: Voyage Charter rate ($/MT of cargo parcel).
      - USD_PER_DAY: Time Charter Equivalent rate ($/day of vessel operating time).
    """

    USD_PER_MT = "USD_PER_MT"
    USD_PER_DAY = "USD_PER_DAY"

    @classmethod
    def from_str(cls, value: str | FreightUnit) -> FreightUnit:
        """Parses and validates a string into a FreightUnit enum member."""
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise InvalidFreightUnitError(f"Freight unit must be a string, got {type(value).__name__}.")
        cleaned = value.strip().upper()
        try:
            return cls(cleaned)
        except ValueError:
            raise InvalidFreightUnitError(
                f"Invalid freight unit '{value}'. Permitted values: '{cls.USD_PER_MT.value}', '{cls.USD_PER_DAY.value}'."
            )


# ==============================================================================
# 2. COST INPUTS VALUE OBJECT
# ==============================================================================

@dataclass(frozen=True)
class CostInputs:
    """
    Pure immutable domain input value object for the Cost Engine.

    All physical, rate, and monetary values are represented as Decimal to ensure
    exact deterministic arithmetic without floating-point inaccuracies.
    """

    # Parcel & Route Context
    cargo_volume_mt: Decimal
    distance_nm: Decimal

    # Feasible Vessel Technical Parameters
    vessel_cargo_capacity_mt: Decimal
    vessel_speed_knots: Decimal
    vessel_fuel_consumption_tpd: Decimal

    # Commercial Freight Rate
    freight_rate_value: Decimal
    freight_unit: FreightUnit

    # Bunker Benchmark
    vlsfo_price_usd_per_mt: Decimal

    # Port Operational & Handling Parameters
    origin_handling_rate_tpd: Decimal
    dest_handling_rate_tpd: Decimal
    origin_waiting_hours: Decimal
    dest_waiting_hours: Decimal

    # Scenario & Sensitivity Parameters (Defaults to baseline = 0.0)
    scenario_delay_hours: Decimal = Decimal("0.0")
    freight_adjustment_pct: Decimal = Decimal("0.0")
    fuel_adjustment_pct: Decimal = Decimal("0.0")
    port_costs_usd: Decimal = Decimal("0.0")

    def __post_init__(self) -> None:
        """Validates canonical domain invariants upon instantiation."""
        # Validate & normalize freight_unit
        if not isinstance(self.freight_unit, FreightUnit):
            object.__setattr__(self, "freight_unit", FreightUnit.from_str(str(self.freight_unit)))

        # Physical & Rate Strict Positivity Checks (> 0)
        if self.cargo_volume_mt <= Decimal("0"):
            raise InvalidCargoVolumeError(
                f"cargo_volume_mt must be strictly greater than 0, got {self.cargo_volume_mt}."
            )
        if self.distance_nm <= Decimal("0"):
            raise ValueError(f"distance_nm must be strictly greater than 0, got {self.distance_nm}.")
        if self.vessel_cargo_capacity_mt <= Decimal("0"):
            raise ValueError(
                f"vessel_cargo_capacity_mt must be strictly greater than 0, got {self.vessel_cargo_capacity_mt}."
            )
        if self.vessel_speed_knots <= Decimal("0"):
            raise ValueError(
                f"vessel_speed_knots must be strictly greater than 0, got {self.vessel_speed_knots}."
            )
        if self.vessel_fuel_consumption_tpd <= Decimal("0"):
            raise ValueError(
                f"vessel_fuel_consumption_tpd must be strictly greater than 0, got {self.vessel_fuel_consumption_tpd}."
            )
        if self.freight_rate_value <= Decimal("0"):
            raise ValueError(
                f"freight_rate_value must be strictly greater than 0, got {self.freight_rate_value}."
            )
        if self.vlsfo_price_usd_per_mt <= Decimal("0"):
            raise ValueError(
                f"vlsfo_price_usd_per_mt must be strictly greater than 0, got {self.vlsfo_price_usd_per_mt}."
            )
        if self.origin_handling_rate_tpd <= Decimal("0"):
            raise ValueError(
                f"origin_handling_rate_tpd must be strictly greater than 0, got {self.origin_handling_rate_tpd}."
            )
        if self.dest_handling_rate_tpd <= Decimal("0"):
            raise ValueError(
                f"dest_handling_rate_tpd must be strictly greater than 0, got {self.dest_handling_rate_tpd}."
            )

        # Non-Negative Operational & Financial Checks (>= 0)
        if self.origin_waiting_hours < Decimal("0"):
            raise ValueError(
                f"origin_waiting_hours must be non-negative (>= 0), got {self.origin_waiting_hours}."
            )
        if self.dest_waiting_hours < Decimal("0"):
            raise ValueError(
                f"dest_waiting_hours must be non-negative (>= 0), got {self.dest_waiting_hours}."
            )
        if self.scenario_delay_hours < Decimal("0"):
            raise ValueError(
                f"scenario_delay_hours must be non-negative (>= 0), got {self.scenario_delay_hours}."
            )
        if self.port_costs_usd < Decimal("0"):
            raise ValueError(f"port_costs_usd must be non-negative (>= 0), got {self.port_costs_usd}.")


# ==============================================================================
# 3. COST RESULT VALUE OBJECT
# ==============================================================================

@dataclass(frozen=True)
class CostResult:
    """
    Pure immutable domain output value object containing the full structural cost
    breakdown, voyage duration metrics, and explainable assumptions.
    """

    # Voyage & Operational Metrics
    required_voyages: int
    sailing_days_per_voyage: Decimal
    origin_handling_hours_total: Decimal
    dest_handling_hours_total: Decimal
    waiting_hours_total: Decimal
    scenario_delay_hours_total: Decimal
    estimated_turnaround_hours: Decimal
    port_days_per_voyage: Decimal
    vessel_days_per_voyage: Decimal

    # Fuel Metrics
    vlsfo_price_used: Decimal
    total_fuel_consumption_mt: Decimal
    total_fuel_cost_usd: Decimal

    # Freight & Summary Costs
    freight_rate_used: Decimal
    freight_unit: FreightUnit
    expected_freight_cost: Decimal
    port_costs_usd: Decimal
    expected_total_cost: Decimal
    effective_cost_per_mt: Decimal

    # Metadata & Explainability
    cost_reference_date: datetime.date
    assumptions: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Enforces immutable tuple representation for assumptions and basic integrity."""
        if not isinstance(self.freight_unit, FreightUnit):
            object.__setattr__(self, "freight_unit", FreightUnit.from_str(str(self.freight_unit)))

        if not isinstance(self.assumptions, tuple):
            object.__setattr__(self, "assumptions", tuple(self.assumptions))

        if self.required_voyages < 1:
            raise ValueError(f"required_voyages must be at least 1, got {self.required_voyages}.")
