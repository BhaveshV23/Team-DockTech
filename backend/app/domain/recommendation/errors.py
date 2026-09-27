"""Typed failures raised by the pure Recommendation Engine."""


class RecommendationError(ValueError):
    """Base class for invalid or insufficient recommendation evidence."""


class MissingRecommendationEvidenceError(RecommendationError):
    """Required forecast, cost, feasibility, or scenario evidence is absent."""


class InconsistentRecommendationEvidenceError(RecommendationError):
    """Evidence disagrees about cargo, route, vessel, forecast, or units."""


class NoFeasibleVesselError(RecommendationError):
    """No candidate passed the two-ended feasibility gate."""
