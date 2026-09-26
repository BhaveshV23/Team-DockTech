"""
DockTech V1 — Cost Engine Domain Errors
========================================
Pure domain exceptions representing error conditions in cost calculation,
data resolution, and input validation.

Authoritative Source-of-Truth Documents:
  1. PRD.md
  2. DATA_DICTIONARY.md (Frozen Canonical Contract)
  3. ARCHITECTURE.md (Domain Boundaries & Fail-Safe Invariants)
  4. C1 Cost Engine Contract

Guarantees:
  - Framework-independent (zero FastAPI / HTTP / database dependencies).
  - Explicit machine-readable error codes matching canonical specifications.
"""

from __future__ import annotations


class CostDomainError(Exception):
    """Base domain exception for all Cost Engine error conditions."""

    def __init__(self, message: str, code: str = "COST_DOMAIN_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class RouteNotFoundError(CostDomainError):
    """Raised when no matching trade route exists for the given origin, destination, and commodity."""

    def __init__(
        self,
        message: str = "Trade route not found for the requested origin, destination, and commodity.",
    ) -> None:
        super().__init__(message, code="ERROR_ROUTE_NOT_FOUND")


class VesselClassNotFoundError(CostDomainError):
    """Raised when an unknown or unsupported vessel class identifier is requested."""

    def __init__(
        self,
        message: str = "Specified vessel class identifier was not found in reference catalog.",
    ) -> None:
        super().__init__(message, code="ERROR_VESSEL_CLASS_NOT_FOUND")


class InsufficientFeasibilityDataError(CostDomainError):
    """Raised when required berth handling rates or physical constraints are missing at a port."""

    def __init__(
        self,
        message: str = "Insufficient berth feasibility data: no compatible berth handling rate available.",
    ) -> None:
        super().__init__(message, code="INSUFFICIENT_FEASIBILITY_DATA")


class InsufficientFuelPriceDataError(CostDomainError):
    """Raised when no valid VLSFO observation exists on or before the cost reference date."""

    def __init__(
        self,
        message: str = "Insufficient fuel price data: no valid VLSFO observation on or before cost reference date.",
    ) -> None:
        super().__init__(message, code="ERROR_INSUFFICIENT_FUEL_PRICE_DATA")


class InsufficientPortActivityDataError(CostDomainError):
    """Raised when no valid port_activity observation exists on or before the cost reference date."""

    def __init__(
        self,
        message: str = "Insufficient port activity data: no valid observation on or before cost reference date.",
    ) -> None:
        super().__init__(message, code="ERROR_INSUFFICIENT_PORT_ACTIVITY_DATA")


class InsufficientFreightDataError(CostDomainError):
    """Raised when required freight rate time-series or forecast data is missing for the route/vessel."""

    def __init__(
        self,
        message: str = "Insufficient freight rate data for the specified route and vessel class.",
    ) -> None:
        super().__init__(message, code="ERROR_INSUFFICIENT_FREIGHT_DATA")


class InvalidCargoVolumeError(CostDomainError):
    """Raised when requested cargo parcel volume is non-positive or violates domain bounds."""

    def __init__(
        self,
        message: str = "Cargo volume must be strictly greater than zero.",
    ) -> None:
        super().__init__(message, code="INVALID_CARGO_VOLUME")


class InvalidFreightUnitError(CostDomainError):
    """Raised when a freight unit token is unrecognized or not permitted in V1."""

    def __init__(
        self,
        message: str = "Freight unit must be either 'USD_PER_MT' or 'USD_PER_DAY'.",
    ) -> None:
        super().__init__(message, code="INVALID_FREIGHT_UNIT")
