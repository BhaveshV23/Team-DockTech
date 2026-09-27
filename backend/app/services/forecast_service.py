from __future__ import annotations

from uuid import UUID, uuid4
from typing import Any, Dict

from backend.app.repositories.forecast_repository import forecast_repository
from ml.service import ForecastService as MLForecastService


class ForecastApplicationService:
    """Application service coordinating ML forecasting and persistence."""

    def __init__(
        self,
        repository=forecast_repository,
        ml_service=None,
    ):
        self.repository = repository
        self.ml_service = ml_service or MLForecastService()

    def create_forecast(
        self,
        cargo_request_id: UUID,
        route_id: str,
        vessel_class_id: str,
        freight_unit: str,
        horizon: int,
    ) -> Dict[str, Any]:
        """Generate a forecast and persist the run and forecast points."""

        # 1. Generate forecast using the existing ML engine.
        result = self.ml_service.forecast(
            route_id=route_id,
            vessel_class_id=vessel_class_id,
            freight_unit=freight_unit,
            horizon=horizon,
        )

        # 2. Create forecast run.
        forecast_run_id = uuid4()

        run_data = {
            "forecast_run_id": str(forecast_run_id),
            "cargo_request_id": str(cargo_request_id),
            "route_id": result.route_id,
            "vessel_class_id": result.vessel_class_id,
            "freight_unit": result.freight_unit,
            "model_name": "Per-series selected Ridge autoregression or seasonal-naive baseline",
            "model_version": result.model_version,
            "training_data_end_date": result.points[0].training_data_end_date,
        }

        saved_run = self.repository.create_forecast_run(run_data)

        # 3. Create forecast points.
        point_data = [
            {
                "forecast_date": point.forecast_date,
                "central_value": point.central,
                "lower_value": point.lower,
                "upper_value": point.upper,
                "unit": point.freight_unit,
            }
            for point in result.points
        ]

        saved_points = self.repository.create_forecast_points(
            forecast_run_id=forecast_run_id,
            points=point_data,
        )

        # 4. Return the persisted forecast in a simple structure.
        return {
            "forecast_run": saved_run,
            "forecast_points": saved_points,
        }


forecast_application_service = ForecastApplicationService()