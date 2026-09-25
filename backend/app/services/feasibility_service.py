"""
DockTech V1 — Feasibility Service
Coordinates the complete Vessel & Port Feasibility module.
Orchestrates repository queries and the domain evaluation engine.
Sources: PRD.md, DATA_DICTIONARY.md, ARCHITECTURE.md

Conceptual operation:
    check_feasibility(origin_port_id, destination_port_id, commodity, vessel_class_id, cargo_volume_mt)

Result provides:
    - Feasible / Not Feasible
    - Vessel class details
    - Origin and destination port details
    - Commodity
    - Constraints checked (LOA, beam, draft at both ends + cargo capacity)
    - Clear rejection reasons with codes
    - Required voyages (ceil(cargo_volume_mt / cargo_capacity_mt))
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence

from backend.app.domain.constants import (
    CANONICAL_COMMODITIES,
    FeasibilityStatus,
    RejectionReasonCode,
)
from backend.app.domain.entities import VesselClass
from backend.app.domain.feasibility import (
    VesselFeasibilityResult,
    evaluate_vessel_feasibility,
)
from backend.app.repositories.berth_repository import BerthRepository
from backend.app.repositories.port_repository import PortRepository
from backend.app.repositories.route_repository import RouteRepository
from backend.app.repositories.vessel_repository import VesselRepository


class FeasibilityService:
    """
    Service layer for Vessel & Port Feasibility evaluation.

    Responsibilities:
    - Load reference data via repositories.
    - Apply the formal V1 two-ended feasibility evaluation.
    - Support single-vessel and multi-vessel candidate evaluation.
    - Return structured VesselFeasibilityResult with reasons and codes.

    Does NOT:
    - Recommend vessels.
    - Calculate freight costs.
    - Build or modify frontend components.
    - Access live AIS, weather, or external data feeds.
    """

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self._port_repo = PortRepository(data_dir=data_dir)
        self._berth_repo = BerthRepository(data_dir=data_dir)
        self._vessel_repo = VesselRepository(data_dir=data_dir)
        self._route_repo = RouteRepository(data_dir=data_dir)

    def check_feasibility(
        self,
        origin_port_id: str,
        destination_port_id: str,
        commodity: str,
        vessel_class_id: str,
        cargo_volume_mt: float,
    ) -> VesselFeasibilityResult:
        """
        Evaluates whether a single candidate vessel class can physically and
        operationally transport the specified commodity from origin to destination.

        Implements the formal V1 Feasibility Evaluation Sequence:
        1. Commodity validation.
        2. Cargo volume validation.
        3. Same-port check.
        4. Reference data existence checks (fail safely with INSUFFICIENT_DATA).
        5. Origin commodity-specific berth query (INSUFFICIENT_DATA if none exist).
        6. Destination commodity-specific berth query (INSUFFICIENT_DATA if none exist).
        7. Two-ended physical constraint checks: LOA, beam, draft at BOTH ends.
        8. Cargo capacity and required voyage calculation.

        Args:
            origin_port_id: Canonical port_id for the loading port.
            destination_port_id: Canonical port_id for the discharge port.
            commodity: One of 'THERMAL_COAL' or 'COKING_COAL'.
            vessel_class_id: One of the 6 canonical vessel class IDs.
            cargo_volume_mt: Total cargo parcel volume in metric tonnes (must be > 0).

        Returns:
            VesselFeasibilityResult with full constraint details, reason codes, and voyage count.
        """
        # Load reference entities via repositories
        origin_port = self._port_repo.get_by_id(origin_port_id)
        destination_port = self._port_repo.get_by_id(destination_port_id)
        vessel = self._vessel_repo.get_by_id(vessel_class_id)

        # Load berths only if ports exist (avoid querying with unknown port IDs)
        origin_berths = (
            self._berth_repo.get_by_port(origin_port_id) if origin_port else []
        )
        destination_berths = (
            self._berth_repo.get_by_port(destination_port_id) if destination_port else []
        )

        # Optionally check route existence (required by V1 spec)
        route = None
        if origin_port and destination_port:
            route = self._route_repo.get_by_origin_dest_commodity(
                origin_port_id, destination_port_id, commodity
            )

        return evaluate_vessel_feasibility(
            vessel=vessel,
            origin_port=origin_port,
            destination_port=destination_port,
            origin_berths=origin_berths,
            destination_berths=destination_berths,
            commodity=commodity,
            cargo_volume_mt=cargo_volume_mt,
            vessel_class_id=vessel_class_id,
            origin_port_id=origin_port_id,
            destination_port_id=destination_port_id,
            route=route,
        )

    def check_feasibility_multiple(
        self,
        origin_port_id: str,
        destination_port_id: str,
        commodity: str,
        cargo_volume_mt: float,
        vessel_class_ids: Optional[Sequence[str]] = None,
    ) -> List[VesselFeasibilityResult]:
        """
        Evaluates feasibility for multiple candidate vessel classes against the same
        cargo request. If vessel_class_ids is None, evaluates all canonical vessel classes.

        Returns a list of VesselFeasibilityResult, one per candidate class.
        """
        if vessel_class_ids is None:
            candidate_ids = [v.vessel_class_id for v in self._vessel_repo.get_all()]
        else:
            candidate_ids = list(vessel_class_ids)

        results: List[VesselFeasibilityResult] = []
        for vc_id in candidate_ids:
            result = self.check_feasibility(
                origin_port_id=origin_port_id,
                destination_port_id=destination_port_id,
                commodity=commodity,
                vessel_class_id=vc_id,
                cargo_volume_mt=cargo_volume_mt,
            )
            results.append(result)
        return results

    def get_feasible_vessel_classes(
        self,
        origin_port_id: str,
        destination_port_id: str,
        commodity: str,
        cargo_volume_mt: float,
        vessel_class_ids: Optional[Sequence[str]] = None,
    ) -> List[VesselFeasibilityResult]:
        """
        Returns only the feasible vessel classes for a given cargo request.
        """
        all_results = self.check_feasibility_multiple(
            origin_port_id=origin_port_id,
            destination_port_id=destination_port_id,
            commodity=commodity,
            cargo_volume_mt=cargo_volume_mt,
            vessel_class_ids=vessel_class_ids,
        )
        return [r for r in all_results if r.is_feasible]
