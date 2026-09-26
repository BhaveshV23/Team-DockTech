"""DockTech V1 repositories package."""

from .reference_repository import (
    BerthRecord,
    CSVReferenceRepository,
    FreightRateRecord,
    FuelPriceRecord,
    PortActivityRecord,
    PortRecord,
    ReferenceRepositoryProtocol,
    RouteRecord,
    VesselClassRecord,
)

__all__ = [
    "ReferenceRepositoryProtocol",
    "CSVReferenceRepository",
    "PortRecord",
    "BerthRecord",
    "VesselClassRecord",
    "RouteRecord",
    "FreightRateRecord",
    "FuelPriceRecord",
    "PortActivityRecord",
    "ScenarioRepository",
]


def __getattr__(name):
    """Load implementations lazily to avoid cost/repository import cycles."""
    if name == "ScenarioRepository":
        from .scenario_repository import ScenarioRepository
        return ScenarioRepository
    if name in __all__:
        from . import reference_repository
        return getattr(reference_repository, name)
    raise AttributeError(name)
