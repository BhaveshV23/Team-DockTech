"""Supabase repository for frozen Recommendation records."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any
from uuid import UUID

import httpx

from backend.app.core.config import settings
from backend.app.domain.constants import ContractStrategy, MarketEntryAction, RiskLevel
from backend.app.domain.recommendation.models import RecommendationConfidence, RecommendationResult


class RecommendationPersistenceError(Exception):
    """Recommendation storage is unavailable or did not confirm a complete insert."""


class InvalidRecommendationError(RecommendationPersistenceError):
    """A recommendation is missing required fields or violates its frozen schema."""


class RecommendationProvenanceError(RecommendationPersistenceError):
    """Forecast run does not belong to the recommendation cargo, route, and vessel."""


class RecommendationRepository:
    """Validate provenance and persist one complete recommendation via Supabase REST."""

    FROZEN_FIELDS = (
        "recommendation_id",
        "cargo_request_id",
        "forecast_run_id",
        "recommended_vessel_class_id",
        "market_entry_action",
        "contract_strategy",
        "expected_freight_cost",
        "expected_total_cost",
        "estimated_turnaround_hours",
        "risk_level",
        "confidence",
        "rationale",
        "assumptions",
        "created_at",
    )

    def __init__(self) -> None:
        self.supabase_url = settings.SUPABASE_URL
        self.service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY

    def _configuration(self, table: str) -> tuple[str, dict[str, str]]:
        if not self.supabase_url or not self.service_role_key:
            raise RecommendationPersistenceError("Recommendation persistence is not configured")
        return (
            f"{self.supabase_url.rstrip('/')}/rest/v1/{table}",
            {
                "apikey": self.service_role_key,
                "Authorization": f"Bearer {self.service_role_key}",
                "Accept": "application/json",
            },
        )

    @staticmethod
    def _check_response(response: httpx.Response, operation: str) -> None:
        if response.status_code < 200 or response.status_code >= 300:
            raise RecommendationPersistenceError(
                f"Recommendation {operation} failed with status {response.status_code}"
            )

    def _get_one(self, table: str, params: dict[str, str], label: str) -> dict[str, Any]:
        url, headers = self._configuration(table)
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=headers, params={**params, "select": "*", "limit": "2"})
            self._check_response(response, "provenance lookup")
            rows = response.json()
            if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
                raise RecommendationProvenanceError(f"{label} was not found uniquely")
            return rows[0]
        except RecommendationPersistenceError:
            raise
        except Exception as exc:
            raise RecommendationPersistenceError("Recommendation provenance lookup failed") from exc

    @staticmethod
    def _uuid(value: Any, field: str) -> UUID:
        try:
            return value if isinstance(value, UUID) else UUID(str(value))
        except (ValueError, TypeError, AttributeError) as exc:
            raise InvalidRecommendationError(f"{field} must be a valid UUID") from exc

    @staticmethod
    def _decimal(value: Any, field: str) -> Decimal:
        if value is None or isinstance(value, bool):
            raise InvalidRecommendationError(f"{field} is required and must be numeric")
        try:
            result = value if isinstance(value, Decimal) else Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise InvalidRecommendationError(f"{field} must be numeric") from exc
        if not result.is_finite() or result <= 0:
            raise InvalidRecommendationError(f"{field} must be a finite positive number")
        return result

    @staticmethod
    def _enum_value(value: Any, enum_type: type[Enum], field: str) -> str:
        if not isinstance(value, enum_type):
            raise InvalidRecommendationError(f"{field} must be a {enum_type.__name__}")
        return str(value.value)

    def _record(self, result: RecommendationResult) -> dict[str, Any]:
        if result is None:
            raise InvalidRecommendationError("Recommendation result is required")
        try:
            identifiers = {
                field: str(self._uuid(getattr(result, field), field))
                for field in ("recommendation_id", "cargo_request_id", "forecast_run_id")
            }
            vessel_id = result.recommended_vessel_class_id
            if not isinstance(vessel_id, str) or not vessel_id.strip():
                raise InvalidRecommendationError("recommended_vessel_class_id is required")
            if not isinstance(result.created_at, datetime) or result.created_at.tzinfo is None:
                raise InvalidRecommendationError("created_at must be a timezone-aware timestamp")
            rationale = result.rationale
            assumptions = result.assumptions
            if not isinstance(rationale, str) or not rationale.strip():
                raise InvalidRecommendationError("rationale is required")
            if not isinstance(assumptions, str) or not assumptions.strip():
                raise InvalidRecommendationError("assumptions is required")
            return {
                **identifiers,
                "recommended_vessel_class_id": vessel_id.strip(),
                "market_entry_action": self._enum_value(
                    result.market_entry_action, MarketEntryAction, "market_entry_action"
                ),
                "contract_strategy": self._enum_value(
                    result.contract_strategy, ContractStrategy, "contract_strategy"
                ),
                "expected_freight_cost": str(self._decimal(
                    result.expected_freight_cost, "expected_freight_cost"
                )),
                "expected_total_cost": str(self._decimal(
                    result.expected_total_cost, "expected_total_cost"
                )),
                "estimated_turnaround_hours": str(self._decimal(
                    result.estimated_turnaround_hours, "estimated_turnaround_hours"
                )),
                "risk_level": self._enum_value(result.risk_level, RiskLevel, "risk_level"),
                "confidence": self._enum_value(
                    result.confidence, RecommendationConfidence, "confidence"
                ),
                "rationale": rationale,
                "assumptions": assumptions,
                "created_at": result.created_at.isoformat(),
            }
        except InvalidRecommendationError:
            raise
        except (AttributeError, TypeError, ValueError) as exc:
            raise InvalidRecommendationError("Recommendation result is incomplete or invalid") from exc

    def _validate_provenance(self, record: dict[str, Any]) -> None:
        cargo = self._get_one(
            "cargo_requests",
            {"cargo_request_id": f"eq.{record['cargo_request_id']}"},
            "Cargo request",
        )
        if str(cargo.get("cargo_request_id")) != record["cargo_request_id"]:
            raise RecommendationProvenanceError("Cargo lookup returned a different cargo request")

        forecast = self._get_one(
            "forecast_runs",
            {"forecast_run_id": f"eq.{record['forecast_run_id']}"},
            "Forecast run",
        )
        if str(forecast.get("forecast_run_id")) != record["forecast_run_id"]:
            raise RecommendationProvenanceError("Forecast lookup returned a different run")
        if str(forecast.get("cargo_request_id")) != record["cargo_request_id"]:
            raise RecommendationProvenanceError("Forecast run belongs to a different cargo request")
        if forecast.get("vessel_class_id") != record["recommended_vessel_class_id"]:
            raise RecommendationProvenanceError("Forecast run belongs to a different vessel class")

        route_id = forecast.get("route_id")
        if not isinstance(route_id, str) or not route_id:
            raise RecommendationProvenanceError("Forecast run has no route")
        route = self._get_one("routes", {"route_id": f"eq.{route_id}"}, "Forecast route")
        if route.get("route_id") != route_id:
            raise RecommendationProvenanceError("Forecast route lookup returned a different route")
        expected = (
            cargo.get("origin_port_id"),
            cargo.get("destination_port_id"),
            cargo.get("commodity"),
        )
        actual = (
            route.get("origin_port_id"),
            route.get("destination_port_id"),
            route.get("commodity"),
        )
        if actual != expected:
            raise RecommendationProvenanceError(
                "Forecast route does not match the cargo origin, destination, and commodity"
            )

    @staticmethod
    def _verify_inserted(rows: Any, record: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
            raise RecommendationPersistenceError("Database did not confirm one complete recommendation")
        saved = rows[0]
        if any(field not in saved for field in RecommendationRepository.FROZEN_FIELDS):
            raise RecommendationPersistenceError("Database returned an incomplete recommendation")
        for field in RecommendationRepository.FROZEN_FIELDS:
            if field in {"expected_freight_cost", "expected_total_cost", "estimated_turnaround_hours"}:
                if Decimal(str(saved[field])) != Decimal(record[field]):
                    raise RecommendationPersistenceError(
                        f"Persisted recommendation field {field} does not match the submitted value"
                    )
            elif field == "created_at":
                try:
                    saved_at = datetime.fromisoformat(str(saved[field]).replace("Z", "+00:00"))
                    submitted_at = datetime.fromisoformat(record[field])
                except ValueError as exc:
                    raise RecommendationPersistenceError("Persisted recommendation timestamp is invalid") from exc
                if saved_at != submitted_at:
                    raise RecommendationPersistenceError("Persisted recommendation timestamp does not match")
            elif str(saved[field]) != record[field]:
                raise RecommendationPersistenceError(
                    f"Persisted recommendation field {field} does not match the submitted value"
                )
        return saved

    def create(self, result: RecommendationResult) -> dict[str, Any]:
        """Validate, then atomically insert a complete frozen recommendation row."""
        record = self._record(result)
        self._validate_provenance(record)
        url, headers = self._configuration("recommendations")
        headers = {
            **headers,
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, headers=headers, json=record)
            self._check_response(response, "persistence")
            return self._verify_inserted(response.json(), record)
        except RecommendationPersistenceError:
            raise
        except Exception as exc:
            raise RecommendationPersistenceError("Recommendation persistence failed") from exc


recommendation_repository = RecommendationRepository()
