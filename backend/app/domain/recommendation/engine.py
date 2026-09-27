"""Pure, deterministic Recommendation Engine for V1."""

from __future__ import annotations

from backend.app.domain.constants import ContractStrategy, FeasibilityStatus, MarketEntryAction, RiskLevel
from .errors import InconsistentRecommendationEvidenceError, NoFeasibleVesselError
from .models import RecommendationConfidence, RecommendationInput, RecommendationResult
from .rules import RISK_ORDER, forecast_trend, ordered_forecast_points, validate_candidate, worst_risk


class RecommendationEngine:
    """Select a feasible vessel and produce a reproducible recommendation result."""

    @classmethod
    def recommend(cls, evidence: RecommendationInput) -> RecommendationResult:
        if evidence.cargo_volume_mt <= 0:
            raise InconsistentRecommendationEvidenceError("Cargo volume must be positive")
        if evidence.laycan_end_date < evidence.laycan_start_date:
            raise InconsistentRecommendationEvidenceError("Laycan end precedes laycan start")
        if not evidence.candidates:
            raise NoFeasibleVesselError("No vessel candidates were supplied")

        feasible_candidates = []
        for candidate in evidence.candidates:
            marked_feasible = candidate.feasibility_status == FeasibilityStatus.FEASIBLE
            if marked_feasible != candidate.feasibility_is_feasible:
                raise InconsistentRecommendationEvidenceError(
                    f"Candidate {candidate.vessel_class_id} has contradictory feasibility evidence"
                )
            if marked_feasible:
                feasible_candidates.append(candidate)
        if not feasible_candidates:
            raise NoFeasibleVesselError("No candidate passed two-ended feasibility")

        ranked = []
        for candidate in feasible_candidates:
            ordered_points = ordered_forecast_points(candidate.forecast_run.points)
            validate_candidate(candidate, evidence)
            aggregate_risk = worst_risk(item.risk_level for item in candidate.scenario_risks)
            cost = candidate.cost
            # One deterministic run is retained per candidate.  Do not allow
            # duplicate class records to make selection input-order dependent.
            ranked.append((
                (cost.effective_cost_per_mt, RISK_ORDER[aggregate_risk],
                 cost.estimated_turnaround_hours, cost.required_voyages,
                 candidate.vessel_class_id),
                candidate, ordered_points, aggregate_risk,
            ))
        ranked.sort(key=lambda item: item[0])
        if len({item[1].vessel_class_id for item in ranked}) != len(ranked):
            raise InconsistentRecommendationEvidenceError("Duplicate vessel candidate IDs are not allowed")

        _, selected, points, risk = ranked[0]
        trend = forecast_trend(points)
        cost = selected.cost
        laycan_days = (evidence.laycan_end_date - evidence.laycan_start_date).days
        operation_days = cost.sailing_days_per_voyage + cost.estimated_turnaround_hours / 24
        fits_laycan = laycan_days > 0 and operation_days <= laycan_days

        if trend == "FALLING" and risk != RiskLevel.HIGH and fits_laycan:
            action = MarketEntryAction.WAIT
        else:
            action = MarketEntryAction.FIX_NOW

        if trend == "INSUFFICIENT":
            confidence = RecommendationConfidence.LOW
        elif trend in {"RISING", "FALLING"} and len({item.risk_level for item in selected.scenario_risks}) == 1:
            confidence = RecommendationConfidence.HIGH
        else:
            confidence = RecommendationConfidence.MEDIUM

        strategy = (
            ContractStrategy.SHORT_TERM_MULTIPLE_VOYAGE
            if cost.required_voyages > 1 else ContractStrategy.SPOT
        )
        assumptions = (
            f"Expected freight uses the first chronological central forecast value "
            f"({points[0].central_value} {points[0].unit.value}); trend compares first and final central values. "
            f"Risk is the worst of baseline, adverse, and favorable. Contract horizon "
            f"{evidence.contract_horizon.value} is advisory; strategy follows required voyages."
        )
        rationale = (
            f"Selected {selected.vessel_class_id} by cost/MT, aggregate risk, turnaround, "
            f"required voyages, then vessel ID. Forecast trend is {trend}; action is "
            f"{action.value}; aggregate risk is {risk.value}."
        )
        if trend == "INSUFFICIENT":
            rationale += " Fewer than two forecast points provide insufficient directional evidence."

        return RecommendationResult(
            recommendation_id=evidence.recommendation_id,
            cargo_request_id=evidence.cargo_request_id,
            forecast_run_id=selected.forecast_run.forecast_run_id,
            recommended_vessel_class_id=selected.vessel_class_id,
            market_entry_action=action,
            contract_strategy=strategy,
            expected_freight_cost=cost.expected_freight_cost,
            expected_total_cost=cost.expected_total_cost,
            estimated_turnaround_hours=cost.estimated_turnaround_hours,
            risk_level=risk,
            confidence=confidence,
            rationale=rationale,
            assumptions=assumptions,
            created_at=evidence.created_at,
            trend=trend,
            forecast_uncertainty=(points[0].lower_value, points[0].central_value, points[0].upper_value),
            required_voyages=cost.required_voyages,
        )
