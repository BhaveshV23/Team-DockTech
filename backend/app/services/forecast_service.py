from __future__ import annotations

from uuid import UUID, uuid4
from typing import Any, Dict

from app.repositories.forecast_repository import (
    ForecastPersistenceError,
    forecast_repository,
)
from app.repositories.route_repository import RouteRepository
from app.schemas.auth import UserProfileResponse
from app.services.cargo_service import cargo_service
from ml.service import ForecastService as MLForecastService


class ForecastApplicationService:
    """Application service coordinating ML forecasting and persistence."""

    def __init__(
        self,
        repository=forecast_repository,
        ml_service=None,
        cargo_access_service=cargo_service,
        route_repository=None,
    ):
        self.repository = repository
        self.ml_service = ml_service or MLForecastService()
        self.cargo_access_service = cargo_access_service
        self.route_repository = route_repository or RouteRepository()

    def create_forecast(
        self,
        cargo_request_id: UUID,
        route_id: str,
        vessel_class_id: str,
        freight_unit: str,
        horizon: int,
        user_profile: UserProfileResponse,
    ) -> Dict[str, Any]:
        """Generate a forecast and persist the run and forecast points."""

        # Reuse cargo authorization and resolve the route from canonical cargo fields.
        cargo = self.cargo_access_service.get_cargo_request(cargo_request_id, user_profile)
        route = self.route_repository.get_by_origin_dest_commodity(
            cargo.origin_port_id,
            cargo.destination_port_id,
            cargo.commodity,
        )
        if route is None or route.route_id != route_id:
            raise ValueError("route_id does not match the referenced cargo request")

        # 1. Generate forecast using the existing ML engine.
        result = self.ml_service.forecast(
            route_id=route_id,
            vessel_class_id=vessel_class_id,
            freight_unit=freight_unit,
            horizon=horizon,
        )
        if (
            result.route_id != route.route_id
            or result.vessel_class_id != vessel_class_id
            or result.freight_unit != freight_unit
            or not result.points
        ):
            raise ValueError("Forecast service returned inconsistent forecast data")

        # 2. Create forecast run.
        forecast_run_id = uuid4()

        run_data = {
            "forecast_run_id": str(forecast_run_id),
            "cargo_request_id": str(cargo_request_id),
            "route_id": result.route_id,
            "vessel_class_id": result.vessel_class_id,
            "freight_unit": result.freight_unit,
            "model_name": self._selected_model_name(route_id, vessel_class_id, freight_unit),
            "model_version": result.model_version,
            "training_data_end_date": result.points[0].training_data_end_date,
        }

        # 3. Build child points using the authoritative run-level freight unit.
        point_data = [
            {
                "forecast_date": point.forecast_date,
                "central_value": point.central,
                "lower_value": point.lower,
                "upper_value": point.upper,
                "unit": result.freight_unit,
            }
            for point in result.points
        ]

        try:
            saved_run = self.repository.create_forecast_run(run_data)
            saved_points = self.repository.create_forecast_points(
                forecast_run_id=UUID(str(saved_run["forecast_run_id"])),
                freight_unit=saved_run["freight_unit"],
                points=point_data,
            )
        except ForecastPersistenceError:
            raise
        except Exception as exc:
            # Repository owns compensation if a child write fails after the run insert.
            raise ForecastPersistenceError("Forecast persistence failed") from exc

        # 4. Return the persisted forecast in a simple structure.
        return {
            "forecast_run": saved_run,
            "forecast_points": saved_points,
        }

    def _selected_model_name(
        self, route_id: str, vessel_class_id: str, freight_unit: str
    ) -> str:
        """Return the model selected by the authoritative ML service for this series."""
        series_key = f"{route_id}||{vessel_class_id}||{freight_unit}"
        return getattr(self.ml_service, "selected_models", {}).get(
            series_key, "ridge_autoregression"
        )


forecast_application_service = ForecastApplicationService()
