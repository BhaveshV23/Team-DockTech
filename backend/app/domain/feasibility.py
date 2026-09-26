"""
DockTech V1 — Vessel & Port Feasibility Domain Engine
Pure domain functions and evaluation logic for two-ended physical and commodity feasibility.
Sources: PRD.md, DATA_DICTIONARY.md, ARCHITECTURE.md
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from backend.app.domain.constants import (
    CANONICAL_COMMODITIES,
    FeasibilityStatus,
    RejectionReasonCode,
)
from backend.app.domain.entities import Berth, Port, Route, VesselClass


_ROUTE_UNSPECIFIED = object()



@dataclass(frozen=True)
class ConstraintCheckItem:
    """Individual constraint check record."""
    constraint_name: str
    passed: bool
    actual_value: Optional[float] = None
    limit_value: Optional[float] = None
    unit: str = "m"
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "constraint_name": self.constraint_name,
            "passed": self.passed,
            "actual_value": self.actual_value,
            "limit_value": self.limit_value,
            "unit": self.unit,
            "message": self.message,
        }


@dataclass(frozen=True)
class BerthFeasibilityEvaluation:
    """Evaluation of a candidate vessel against a single berth."""
    berth_id: str
    berth_name: str
    port_id: str
    commodity: str
    is_commodity_match: bool
    loa_ok: bool
    beam_ok: bool
    draft_ok: bool
    is_feasible: bool
    rejection_reasons: List[str] = field(default_factory=list)
    rejection_codes: List[RejectionReasonCode] = field(default_factory=list)


@dataclass(frozen=True)
class PortFeasibilityEvaluation:
    """Evaluation of a candidate vessel across all berths at a port."""
    port_id: str
    port_name: str
    role: str  # "ORIGIN" or "DESTINATION"
    commodity: str
    has_commodity_berths: bool
    is_feasible: bool
    compatible_berth_ids: List[str] = field(default_factory=list)
    berth_evaluations: List[BerthFeasibilityEvaluation] = field(default_factory=list)
    rejection_reasons: List[str] = field(default_factory=list)
    rejection_codes: List[RejectionReasonCode] = field(default_factory=list)
    insufficient_data_reasons: List[str] = field(default_factory=list)


@dataclass
class VesselFeasibilityResult:
    """Complete two-ended feasibility evaluation result for a vessel class."""
    is_feasible: bool
    status: FeasibilityStatus
    vessel_class_id: str
    vessel_class_name: str
    origin_port_id: str
    origin_port_name: str
    destination_port_id: str
    destination_port_name: str
    commodity: str
    cargo_volume_mt: float
    cargo_capacity_mt: float
    required_voyages: Optional[int]
    constraints_checked: Dict[str, Any]
    rejection_reasons: List[str] = field(default_factory=list)
    rejection_codes: List[str] = field(default_factory=list)
    insufficient_data_reasons: List[str] = field(default_factory=list)
    compatible_origin_berth_ids: List[str] = field(default_factory=list)
    compatible_destination_berth_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_feasible": self.is_feasible,
            "status": self.status.value if isinstance(self.status, FeasibilityStatus) else str(self.status),
            "vessel_class_id": self.vessel_class_id,
            "vessel_class_name": self.vessel_class_name,
            "origin_port_id": self.origin_port_id,
            "origin_port_name": self.origin_port_name,
            "destination_port_id": self.destination_port_id,
            "destination_port_name": self.destination_port_name,
            "commodity": self.commodity,
            "cargo_volume_mt": self.cargo_volume_mt,
            "cargo_capacity_mt": self.cargo_capacity_mt,
            "required_voyages": self.required_voyages,
            "constraints_checked": self.constraints_checked,
            "rejection_reasons": list(self.rejection_reasons),
            "rejection_codes": list(self.rejection_codes),
            "insufficient_data_reasons": list(self.insufficient_data_reasons),
            "compatible_origin_berth_ids": list(self.compatible_origin_berth_ids),
            "compatible_destination_berth_ids": list(self.compatible_destination_berth_ids),
        }


# ==============================================================================
# PURE CALCULATION FUNCTIONS
# ==============================================================================

def calculate_required_voyages(cargo_volume_mt: float, cargo_capacity_mt: float) -> int:
    """
    Calculates the required number of voyages for a cargo parcel.
    Formula: required_voyages = ceil(cargo_volume_mt / vessel.cargo_capacity_mt)
    Strictly uses cargo_capacity_mt, never DWT.
    """
    if cargo_capacity_mt <= 0:
        raise ValueError(f"cargo_capacity_mt must be > 0, got {cargo_capacity_mt}")
    if cargo_volume_mt <= 0:
        raise ValueError(f"cargo_volume_mt must be > 0, got {cargo_volume_mt}")
    return math.ceil(cargo_volume_mt / cargo_capacity_mt)


def evaluate_berth_feasibility(
    vessel: VesselClass,
    berth: Berth,
    commodity: str,
    role: str = "ORIGIN",
) -> BerthFeasibilityEvaluation:
    """
    Evaluates physical and commodity compatibility for a vessel at a single berth.
    """
    is_commodity_match = (berth.commodity == commodity)
    rejection_reasons: List[str] = []
    rejection_codes: List[RejectionReasonCode] = []

    if not is_commodity_match:
        rejection_reasons.append(
            f"Berth {berth.berth_id} handles {berth.commodity}, not requested commodity {commodity}."
        )
        rejection_codes.append(RejectionReasonCode.REJECTED_COMMODITY_INCOMPATIBLE)
        return BerthFeasibilityEvaluation(
            berth_id=berth.berth_id,
            berth_name=berth.berth_name,
            port_id=berth.port_id,
            commodity=berth.commodity,
            is_commodity_match=False,
            loa_ok=False,
            beam_ok=False,
            draft_ok=False,
            is_feasible=False,
            rejection_reasons=rejection_reasons,
            rejection_codes=rejection_codes,
        )

    loa_ok = (vessel.loa_m <= berth.max_loa_m)
    beam_ok = (vessel.beam_m <= berth.max_beam_m)
    draft_ok = (vessel.draft_m <= berth.max_draft_m)

    role_label = "origin" if role.upper() == "ORIGIN" else "destination"

    if not loa_ok:
        rejection_reasons.append(
            f"Vessel LOA ({vessel.loa_m}m) exceeds {role_label} berth {berth.berth_id} limit ({berth.max_loa_m}m)."
        )
        code = (
            RejectionReasonCode.REJECTED_LOA_EXCEEDED_ORIGIN_BERTH
            if role.upper() == "ORIGIN"
            else RejectionReasonCode.REJECTED_LOA_EXCEEDED_DESTINATION_BERTH
        )
        rejection_codes.append(code)

    if not beam_ok:
        rejection_reasons.append(
            f"Vessel beam ({vessel.beam_m}m) exceeds {role_label} berth {berth.berth_id} limit ({berth.max_beam_m}m)."
        )
        code = (
            RejectionReasonCode.REJECTED_BEAM_EXCEEDED_ORIGIN_BERTH
            if role.upper() == "ORIGIN"
            else RejectionReasonCode.REJECTED_BEAM_EXCEEDED_DESTINATION_BERTH
        )
        rejection_codes.append(code)

    if not draft_ok:
        rejection_reasons.append(
            f"Vessel draft ({vessel.draft_m}m) exceeds {role_label} berth {berth.berth_id} limit ({berth.max_draft_m}m)."
        )
        code = (
            RejectionReasonCode.REJECTED_DRAFT_EXCEEDED_ORIGIN_BERTH
            if role.upper() == "ORIGIN"
            else RejectionReasonCode.REJECTED_DRAFT_EXCEEDED_DESTINATION_BERTH
        )
        rejection_codes.append(code)

    is_feasible = loa_ok and beam_ok and draft_ok

    return BerthFeasibilityEvaluation(
        berth_id=berth.berth_id,
        berth_name=berth.berth_name,
        port_id=berth.port_id,
        commodity=berth.commodity,
        is_commodity_match=True,
        loa_ok=loa_ok,
        beam_ok=beam_ok,
        draft_ok=draft_ok,
        is_feasible=is_feasible,
        rejection_reasons=rejection_reasons,
        rejection_codes=rejection_codes,
    )


def evaluate_port_feasibility(
    vessel: VesselClass,
    port: Port,
    berths: Sequence[Berth],
    commodity: str,
    role: str = "ORIGIN",
) -> PortFeasibilityEvaluation:
    """
    Evaluates port-level and berth-level feasibility for a candidate vessel.
    Enforces the Authoritative Operational Berth Rule:
    - At least one commodity-specific berth must exist at the port.
    - If zero commodity berths exist, returns INSUFFICIENT_FEASIBILITY_DATA.
    - A vessel is feasible at the port if at least one commodity berth accommodates its LOA, beam, and draft.
    """
    role_upper = role.upper()
    role_label = "origin" if role_upper == "ORIGIN" else "destination"

    # Filter berths for the requested commodity at this port
    commodity_berths = [b for b in berths if b.port_id == port.port_id and b.commodity == commodity]

    if not commodity_berths:
        msg = f"INSUFFICIENT_FEASIBILITY_DATA: No compatible berth for commodity {commodity} at {role_label} port {port.port_id}."
        code = (
            RejectionReasonCode.INSUFFICIENT_FEASIBILITY_DATA_NO_ORIGIN_BERTH
            if role_upper == "ORIGIN"
            else RejectionReasonCode.INSUFFICIENT_FEASIBILITY_DATA_NO_DESTINATION_BERTH
        )
        return PortFeasibilityEvaluation(
            port_id=port.port_id,
            port_name=port.port_name,
            role=role_upper,
            commodity=commodity,
            has_commodity_berths=False,
            is_feasible=False,
            rejection_reasons=[msg],
            rejection_codes=[code],
            insufficient_data_reasons=[msg],
        )

    berth_evals: List[BerthFeasibilityEvaluation] = []
    compatible_berth_ids: List[str] = []

    for b in commodity_berths:
        eval_result = evaluate_berth_feasibility(vessel, b, commodity, role=role_upper)
        berth_evals.append(eval_result)
        if eval_result.is_feasible:
            compatible_berth_ids.append(b.berth_id)

    is_feasible = len(compatible_berth_ids) > 0
    rejection_reasons: List[str] = []
    rejection_codes: List[RejectionReasonCode] = []

    if not is_feasible:
        # Vessel could not fit in any commodity-matching berth at this port.
        # Collect best-fit / all rejection reasons
        best_loa_berth = max(commodity_berths, key=lambda b: b.max_loa_m)
        best_beam_berth = max(commodity_berths, key=lambda b: b.max_beam_m)
        best_draft_berth = max(commodity_berths, key=lambda b: b.max_draft_m)

        if vessel.loa_m > best_loa_berth.max_loa_m:
            rejection_reasons.append(
                f"Vessel LOA ({vessel.loa_m}m) exceeds maximum available {role_label} berth LOA ({best_loa_berth.max_loa_m}m at {best_loa_berth.berth_id}) at {port.port_name}."
            )
            code = (
                RejectionReasonCode.REJECTED_LOA_EXCEEDED_ORIGIN_BERTH
                if role_upper == "ORIGIN"
                else RejectionReasonCode.REJECTED_LOA_EXCEEDED_DESTINATION_BERTH
            )
            rejection_codes.append(code)

        if vessel.beam_m > best_beam_berth.max_beam_m:
            rejection_reasons.append(
                f"Vessel beam ({vessel.beam_m}m) exceeds maximum available {role_label} berth beam ({best_beam_berth.max_beam_m}m at {best_beam_berth.berth_id}) at {port.port_name}."
            )
            code = (
                RejectionReasonCode.REJECTED_BEAM_EXCEEDED_ORIGIN_BERTH
                if role_upper == "ORIGIN"
                else RejectionReasonCode.REJECTED_BEAM_EXCEEDED_DESTINATION_BERTH
            )
            rejection_codes.append(code)

        if vessel.draft_m > best_draft_berth.max_draft_m:
            rejection_reasons.append(
                f"Vessel draft ({vessel.draft_m}m) exceeds maximum available {role_label} berth draft ({best_draft_berth.max_draft_m}m at {best_draft_berth.berth_id}) at {port.port_name}."
            )
            code = (
                RejectionReasonCode.REJECTED_DRAFT_EXCEEDED_ORIGIN_BERTH
                if role_upper == "ORIGIN"
                else RejectionReasonCode.REJECTED_DRAFT_EXCEEDED_DESTINATION_BERTH
            )
            rejection_codes.append(code)

        # Fallback explanation if no specific dimension exceeded max but combinations failed
        if not rejection_reasons:
            rejection_reasons.append(
                f"Vessel does not meet combined physical constraints at any {commodity} berth at {role_label} port {port.port_name}."
            )

    return PortFeasibilityEvaluation(
        port_id=port.port_id,
        port_name=port.port_name,
        role=role_upper,
        commodity=commodity,
        has_commodity_berths=True,
        is_feasible=is_feasible,
        compatible_berth_ids=compatible_berth_ids,
        berth_evaluations=berth_evals,
        rejection_reasons=rejection_reasons,
        rejection_codes=rejection_codes,
    )


def evaluate_port_envelope_constraints(
    vessel: VesselClass,
    port: Port,
    role: str = "ORIGIN",
) -> Dict[str, Any]:
    """Evaluates the canonical port planning envelope for a vessel at a port end."""
    role_upper = role.upper()
    role_label = "origin" if role_upper == "ORIGIN" else "destination"
    rejection_reasons: List[str] = []
    rejection_codes: List[str] = []

    dimension_checks = {
        "loa": (vessel.loa_m, port.max_loa_m),
        "beam": (vessel.beam_m, port.max_beam_m),
        "draft": (vessel.draft_m, port.max_draft_m),
    }

    for dimension_name, (actual_value, limit_value) in dimension_checks.items():
        if actual_value > limit_value:
            dimension_label = {
                "loa": "LOA",
                "beam": "beam",
                "draft": "draft",
            }[dimension_name]
            rejection_reasons.append(
                f"Vessel {dimension_label} ({actual_value}m) exceeds {role_label} port envelope limit ({limit_value}m) at {port.port_id}."
            )
            code = (
                RejectionReasonCode.REJECTED_ORIGIN_PORT_ENVELOPE_EXCEEDED
                if role_upper == "ORIGIN"
                else RejectionReasonCode.REJECTED_DESTINATION_PORT_ENVELOPE_EXCEEDED
            )
            rejection_codes.append(code.value)

    return {
        "passed": not rejection_reasons,
        "role": role_upper,
        "port_id": port.port_id,
        "port_name": port.port_name,
        "dimensions": {
            "loa": {
                "actual_value_m": vessel.loa_m,
                "limit_value_m": port.max_loa_m,
                "passed": vessel.loa_m <= port.max_loa_m,
            },
            "beam": {
                "actual_value_m": vessel.beam_m,
                "limit_value_m": port.max_beam_m,
                "passed": vessel.beam_m <= port.max_beam_m,
            },
            "draft": {
                "actual_value_m": vessel.draft_m,
                "limit_value_m": port.max_draft_m,
                "passed": vessel.draft_m <= port.max_draft_m,
            },
        },
        "rejection_reasons": rejection_reasons,
        "rejection_codes": rejection_codes,
    }


def evaluate_vessel_feasibility(
    vessel: Optional[VesselClass],
    origin_port: Optional[Port],
    destination_port: Optional[Port],
    origin_berths: Sequence[Berth],
    destination_berths: Sequence[Berth],
    commodity: str,
    cargo_volume_mt: float,
    vessel_class_id: str,
    origin_port_id: str,
    destination_port_id: str,
    route: Optional[Route] = _ROUTE_UNSPECIFIED,
) -> VesselFeasibilityResult:
    """
    Executes the full formal DockTech V1 Feasibility Evaluation Sequence:
    1. Commodity compatibility validation.
    2. Missing reference data checks (fail safe with INSUFFICIENT_FEASIBILITY_DATA).
    3. Origin port and commodity-specific berth validation.
    4. Destination port and commodity-specific berth validation.
    5. Two-ended physical constraint check (LOA, beam, draft).
    6. Cargo capacity and required voyage calculation.
    """
    constraints_checked: Dict[str, Any] = {}
    rejection_reasons: List[str] = []
    rejection_codes: List[str] = []
    insufficient_data_reasons: List[str] = []

    # 1. Commodity validation
    is_valid_commodity = commodity in CANONICAL_COMMODITIES
    constraints_checked["commodity_compatibility"] = {
        "commodity": commodity,
        "is_canonical": is_valid_commodity,
        "passed": is_valid_commodity,
    }
    if not is_valid_commodity:
        rejection_reasons.append(
            f"Commodity '{commodity}' is not supported. Supported commodities: {sorted(list(CANONICAL_COMMODITIES))}."
        )
        rejection_codes.append(RejectionReasonCode.REJECTED_COMMODITY_INCOMPATIBLE.value)
        # Return INFEASIBLE immediately — an unsupported commodity is a hard input rejection,
        # not a missing-reference-data condition. Do not proceed to berth evaluation.
        return VesselFeasibilityResult(
            is_feasible=False,
            status=FeasibilityStatus.INFEASIBLE,
            vessel_class_id=vessel_class_id,
            vessel_class_name=vessel.vessel_class_name if vessel else vessel_class_id,
            origin_port_id=origin_port_id,
            origin_port_name=origin_port.port_name if origin_port else origin_port_id,
            destination_port_id=destination_port_id,
            destination_port_name=destination_port.port_name if destination_port else destination_port_id,
            commodity=commodity,
            cargo_volume_mt=cargo_volume_mt,
            cargo_capacity_mt=vessel.cargo_capacity_mt if vessel else 0.0,
            required_voyages=None,
            constraints_checked=constraints_checked,
            rejection_reasons=rejection_reasons,
            rejection_codes=rejection_codes,
            insufficient_data_reasons=[],
            compatible_origin_berth_ids=[],
            compatible_destination_berth_ids=[],
        )

    # 2. Cargo volume validation
    is_valid_volume = cargo_volume_mt > 0
    constraints_checked["cargo_volume_valid"] = {
        "cargo_volume_mt": cargo_volume_mt,
        "passed": is_valid_volume,
    }
    if not is_valid_volume:
        rejection_reasons.append(
            f"Cargo volume must be greater than 0, got {cargo_volume_mt} MT."
        )
        rejection_codes.append(RejectionReasonCode.INVALID_CARGO_VOLUME.value)

    # 3. Same origin & destination check
    if origin_port_id == destination_port_id:
        rejection_reasons.append(
            f"Origin port '{origin_port_id}' cannot be identical to destination port '{destination_port_id}'."
        )
        rejection_codes.append(RejectionReasonCode.SAME_ORIGIN_DESTINATION.value)

    # 4. Check missing reference data
    if origin_port is None:
        msg = f"INSUFFICIENT_FEASIBILITY_DATA: Unknown origin port '{origin_port_id}'."
        insufficient_data_reasons.append(msg)
        rejection_codes.append(RejectionReasonCode.INSUFFICIENT_FEASIBILITY_DATA_UNKNOWN_ORIGIN_PORT.value)

    if destination_port is None:
        msg = f"INSUFFICIENT_FEASIBILITY_DATA: Unknown destination port '{destination_port_id}'."
        insufficient_data_reasons.append(msg)
        rejection_codes.append(RejectionReasonCode.INSUFFICIENT_FEASIBILITY_DATA_UNKNOWN_DESTINATION_PORT.value)

    if vessel is None:
        msg = f"INSUFFICIENT_FEASIBILITY_DATA: Unknown vessel class '{vessel_class_id}'."
        insufficient_data_reasons.append(msg)
        rejection_codes.append(RejectionReasonCode.INSUFFICIENT_FEASIBILITY_DATA_UNKNOWN_VESSEL_CLASS.value)

    if insufficient_data_reasons:
        return VesselFeasibilityResult(
            is_feasible=False,
            status=FeasibilityStatus.INSUFFICIENT_DATA,
            vessel_class_id=vessel_class_id,
            vessel_class_name=vessel.vessel_class_name if vessel else vessel_class_id,
            origin_port_id=origin_port_id,
            origin_port_name=origin_port.port_name if origin_port else origin_port_id,
            destination_port_id=destination_port_id,
            destination_port_name=destination_port.port_name if destination_port else destination_port_id,
            commodity=commodity,
            cargo_volume_mt=cargo_volume_mt,
            cargo_capacity_mt=vessel.cargo_capacity_mt if vessel else 0.0,
            required_voyages=None,
            constraints_checked=constraints_checked,
            rejection_reasons=rejection_reasons + insufficient_data_reasons,
            rejection_codes=rejection_codes,
            insufficient_data_reasons=insufficient_data_reasons,
            compatible_origin_berth_ids=[],
            compatible_destination_berth_ids=[],
        )

    # At this point, vessel, origin_port, destination_port are non-None
    assert vessel is not None
    assert origin_port is not None
    assert destination_port is not None

    # Route validation is required by the authoritative V1 source-of-truth,
    # but only when the caller explicitly supplies a missing route result.
    if route is not _ROUTE_UNSPECIFIED and route is None:
        msg = (
            f"INSUFFICIENT_FEASIBILITY_DATA: No canonical route exists for origin '{origin_port_id}', "
            f"destination '{destination_port_id}', commodity '{commodity}'."
        )
        insufficient_data_reasons.append(msg)
        rejection_reasons.append(msg)
        rejection_codes.append(RejectionReasonCode.ERROR_ROUTE_NOT_FOUND.value)

    # Calculate required voyages
    required_voyages: Optional[int] = None
    if is_valid_volume and vessel.cargo_capacity_mt > 0:
        required_voyages = calculate_required_voyages(cargo_volume_mt, vessel.cargo_capacity_mt)
        constraints_checked["cargo_capacity"] = {
            "vessel_cargo_capacity_mt": vessel.cargo_capacity_mt,
            "cargo_volume_mt": cargo_volume_mt,
            "required_voyages": required_voyages,
            "passed": True,
        }

    origin_port_envelope = evaluate_port_envelope_constraints(vessel, origin_port, role="ORIGIN")
    destination_port_envelope = evaluate_port_envelope_constraints(vessel, destination_port, role="DESTINATION")
    constraints_checked["origin_port_envelope"] = origin_port_envelope
    constraints_checked["destination_port_envelope"] = destination_port_envelope

    if not origin_port_envelope["passed"]:
        rejection_reasons.extend(origin_port_envelope["rejection_reasons"])
        for code in origin_port_envelope["rejection_codes"]:
            if code not in rejection_codes:
                rejection_codes.append(code)

    if not destination_port_envelope["passed"]:
        rejection_reasons.extend(destination_port_envelope["rejection_reasons"])
        for code in destination_port_envelope["rejection_codes"]:
            if code not in rejection_codes:
                rejection_codes.append(code)

    # 5. Evaluate Origin Feasibility
    orig_eval = evaluate_port_feasibility(
        vessel=vessel,
        port=origin_port,
        berths=origin_berths,
        commodity=commodity,
        role="ORIGIN",
    )

    # 6. Evaluate Destination Feasibility
    dest_eval = evaluate_port_feasibility(
        vessel=vessel,
        port=destination_port,
        berths=destination_berths,
        commodity=commodity,
        role="DESTINATION",
    )

    # Build constraint checks dictionary
    max_orig_loa = max((b.max_loa_m for b in origin_berths if b.commodity == commodity), default=0.0)
    max_orig_beam = max((b.max_beam_m for b in origin_berths if b.commodity == commodity), default=0.0)
    max_orig_draft = max((b.max_draft_m for b in origin_berths if b.commodity == commodity), default=0.0)

    max_dest_loa = max((b.max_loa_m for b in destination_berths if b.commodity == commodity), default=0.0)
    max_dest_beam = max((b.max_beam_m for b in destination_berths if b.commodity == commodity), default=0.0)
    max_dest_draft = max((b.max_draft_m for b in destination_berths if b.commodity == commodity), default=0.0)

    constraints_checked["origin_commodity_berth_available"] = {
        "passed": orig_eval.has_commodity_berths,
        "matching_berths_count": len([b for b in origin_berths if b.commodity == commodity]),
    }
    constraints_checked["destination_commodity_berth_available"] = {
        "passed": dest_eval.has_commodity_berths,
        "matching_berths_count": len([b for b in destination_berths if b.commodity == commodity]),
    }

    constraints_checked["origin_loa"] = {
        "vessel_loa_m": vessel.loa_m,
        "max_available_berth_loa_m": max_orig_loa,
        "passed": (vessel.loa_m <= max_orig_loa) if orig_eval.has_commodity_berths else False,
    }
    constraints_checked["origin_beam"] = {
        "vessel_beam_m": vessel.beam_m,
        "max_available_berth_beam_m": max_orig_beam,
        "passed": (vessel.beam_m <= max_orig_beam) if orig_eval.has_commodity_berths else False,
    }
    constraints_checked["origin_draft"] = {
        "vessel_draft_m": vessel.draft_m,
        "max_available_berth_draft_m": max_orig_draft,
        "passed": (vessel.draft_m <= max_orig_draft) if orig_eval.has_commodity_berths else False,
    }

    constraints_checked["destination_loa"] = {
        "vessel_loa_m": vessel.loa_m,
        "max_available_berth_loa_m": max_dest_loa,
        "passed": (vessel.loa_m <= max_dest_loa) if dest_eval.has_commodity_berths else False,
    }
    constraints_checked["destination_beam"] = {
        "vessel_beam_m": vessel.beam_m,
        "max_available_berth_beam_m": max_dest_beam,
        "passed": (vessel.beam_m <= max_dest_beam) if dest_eval.has_commodity_berths else False,
    }
    constraints_checked["destination_draft"] = {
        "vessel_draft_m": vessel.draft_m,
        "max_available_berth_draft_m": max_dest_draft,
        "passed": (vessel.draft_m <= max_dest_draft) if dest_eval.has_commodity_berths else False,
    }

    if orig_eval.insufficient_data_reasons:
        insufficient_data_reasons.extend(orig_eval.insufficient_data_reasons)
    if dest_eval.insufficient_data_reasons:
        insufficient_data_reasons.extend(dest_eval.insufficient_data_reasons)

    for code in orig_eval.rejection_codes:
        code_val = code.value if isinstance(code, RejectionReasonCode) else str(code)
        if code_val not in rejection_codes:
            rejection_codes.append(code_val)

    for code in dest_eval.rejection_codes:
        code_val = code.value if isinstance(code, RejectionReasonCode) else str(code)
        if code_val not in rejection_codes:
            rejection_codes.append(code_val)

    rejection_reasons.extend(orig_eval.rejection_reasons)
    rejection_reasons.extend(dest_eval.rejection_reasons)

    # Determine status
    if insufficient_data_reasons:
        status = FeasibilityStatus.INSUFFICIENT_DATA
        is_feasible = False
    elif not is_valid_commodity or not is_valid_volume or origin_port_id == destination_port_id:
        status = FeasibilityStatus.INFEASIBLE
        is_feasible = False
    elif (
        origin_port_envelope["passed"]
        and destination_port_envelope["passed"]
        and orig_eval.is_feasible
        and dest_eval.is_feasible
    ):
        status = FeasibilityStatus.FEASIBLE
        is_feasible = True
    else:
        status = FeasibilityStatus.INFEASIBLE
        is_feasible = False

    return VesselFeasibilityResult(
        is_feasible=is_feasible,
        status=status,
        vessel_class_id=vessel.vessel_class_id,
        vessel_class_name=vessel.vessel_class_name,
        origin_port_id=origin_port.port_id,
        origin_port_name=origin_port.port_name,
        destination_port_id=destination_port.port_id,
        destination_port_name=destination_port.port_name,
        commodity=commodity,
        cargo_volume_mt=cargo_volume_mt,
        cargo_capacity_mt=vessel.cargo_capacity_mt,
        required_voyages=required_voyages,
        constraints_checked=constraints_checked,
        rejection_reasons=rejection_reasons,
        rejection_codes=rejection_codes,
        insufficient_data_reasons=insufficient_data_reasons,
        compatible_origin_berth_ids=orig_eval.compatible_berth_ids,
        compatible_destination_berth_ids=dest_eval.compatible_berth_ids,
    )
