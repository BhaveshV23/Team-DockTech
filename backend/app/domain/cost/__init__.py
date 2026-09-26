"""
DockTech V1 — Cost Domain Package
==================================
Exports pure domain models, value objects, domain exceptions,
formulas, cost input resolver, and calculation engine for the DockTech V1 Cost Engine.
"""

from .engine import calculate_cost
from .errors import (
    CostDomainError,
    InsufficientFeasibilityDataError,
    InsufficientFreightDataError,
    InsufficientFuelPriceDataError,
    InsufficientPortActivityDataError,
    InvalidCargoVolumeError,
    InvalidFreightUnitError,
    RouteNotFoundError,
    VesselClassNotFoundError,
)
from .formulas import (
    apply_percentage_adjustment,
    calculate_effective_cost_per_mt,
    calculate_estimated_turnaround_hours,
    calculate_expected_total_cost,
    calculate_freight_cost_usd_per_day,
    calculate_freight_cost_usd_per_mt,
    calculate_handling_hours_total,
    calculate_port_days_per_voyage,
    calculate_required_voyages,
    calculate_sailing_days,
    calculate_scenario_delay_hours_total,
    calculate_total_fuel_consumption_mt,
    calculate_total_fuel_cost,
    calculate_vessel_days_per_voyage,
    calculate_waiting_hours_total,
)
from .models import (
    CostInputs,
    CostResult,
    FreightUnit,
)
from .resolver import CostInputResolver

__all__ = [
    "CostInputs",
    "CostResult",
    "FreightUnit",
    "CostInputResolver",
    "calculate_cost",
    "calculate_required_voyages",
    "calculate_sailing_days",
    "calculate_handling_hours_total",
    "calculate_waiting_hours_total",
    "calculate_scenario_delay_hours_total",
    "calculate_estimated_turnaround_hours",
    "calculate_port_days_per_voyage",
    "calculate_vessel_days_per_voyage",
    "calculate_total_fuel_consumption_mt",
    "calculate_total_fuel_cost",
    "calculate_freight_cost_usd_per_mt",
    "calculate_freight_cost_usd_per_day",
    "calculate_expected_total_cost",
    "calculate_effective_cost_per_mt",
    "apply_percentage_adjustment",
    "CostDomainError",
    "RouteNotFoundError",
    "VesselClassNotFoundError",
    "InsufficientFeasibilityDataError",
    "InsufficientFuelPriceDataError",
    "InsufficientPortActivityDataError",
    "InsufficientFreightDataError",
    "InvalidCargoVolumeError",
    "InvalidFreightUnitError",
]
