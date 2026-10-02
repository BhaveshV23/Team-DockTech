"""Application reference repositories use the Supabase runtime adapter."""

import sys
from pathlib import Path

backend_path = str(Path(__file__).resolve().parents[1] / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from backend.app.domain.cost.models import FreightUnit
from backend.app.repositories.berth_repository import BerthRepository
from backend.app.repositories.port_repository import PortRepository
from backend.app.repositories.reference_repository import SupabaseCostReferenceRepository
from backend.app.repositories.route_repository import RouteRepository
from backend.app.repositories.scenario_repository import ScenarioRepository
from backend.app.repositories.vessel_repository import VesselRepository
from backend.app.services.feasibility_service import FeasibilityService
from backend.app.services.recommendation_service import RecommendationService
from backend.app.services.forecast_service import ForecastApplicationService
from backend.app.services.reference_service import ReferenceService


def test_default_catalog_repositories_read_supabase_reference_tables(monkeypatch):
    queried_tables = []
    seeded_table_query = SupabaseCostReferenceRepository._get

    def recording_query(repository, table, params):
        queried_tables.append(table)
        return seeded_table_query(repository, table, params)

    monkeypatch.setattr(SupabaseCostReferenceRepository, "_get", recording_query)

    assert PortRepository().get_all()
    assert BerthRepository().get_all()
    assert VesselRepository().get_all()
    assert RouteRepository().get_all()
    assert {"ports", "berths", "vessel_classes", "routes"}.issubset(queried_tables)


def test_reference_api_service_and_forecast_route_resolution_use_supabase(monkeypatch):
    queried_tables = []
    seeded_table_query = SupabaseCostReferenceRepository._get

    def recording_query(repository, table, params):
        queried_tables.append(table)
        return seeded_table_query(repository, table, params)

    monkeypatch.setattr(SupabaseCostReferenceRepository, "_get", recording_query)
    assert ReferenceService().get_ports()
    assert ReferenceService().get_vessels()
    assert ReferenceService().get_routes()
    assert ForecastApplicationService().route_repository.get_by_origin_dest_commodity(
        "NEWCASTLE", "PARADIP", "THERMAL_COAL"
    )
    assert {"ports", "vessel_classes", "routes"}.issubset(queried_tables)


def test_default_feasibility_service_uses_supabase_reference_tables(monkeypatch):
    queried_tables = []
    seeded_table_query = SupabaseCostReferenceRepository._get

    def recording_query(repository, table, params):
        queried_tables.append(table)
        return seeded_table_query(repository, table, params)

    monkeypatch.setattr(SupabaseCostReferenceRepository, "_get", recording_query)
    result = FeasibilityService().check_feasibility(
        origin_port_id="NEWCASTLE",
        destination_port_id="PARADIP",
        commodity="THERMAL_COAL",
        vessel_class_id="SUPRAMAX",
        cargo_volume_mt=50000,
    )

    assert result.vessel_class_id == "SUPRAMAX"
    assert {"ports", "berths", "vessel_classes", "routes"}.issubset(queried_tables)


def test_scenario_defaults_are_read_from_supabase_at_runtime():
    defaults = ScenarioRepository().get_scenario_defaults()
    assert {default.scenario_id.value for default in defaults} == {
        "BASELINE", "ADVERSE", "FAVORABLE"
    }


def test_recommendation_defaults_use_supabase_reference_repositories():
    service = RecommendationService()
    assert service.route_repository._use_supabase
    assert service.vessel_repository._use_supabase
    assert service.feasibility_service._port_repo._use_supabase
    assert service.feasibility_service._berth_repo._use_supabase
    assert service.cost_engine._resolver.repository.__class__ is SupabaseCostReferenceRepository
    assert service.scenario_service.repository.use_supabase_reference_data


def test_historical_freight_lookup_uses_supabase_but_ml_csv_remains():
    observations = SupabaseCostReferenceRepository().get_freight_observations(
        "NEWCASTLE_PARADIP_THERMAL", "PANAMAX", FreightUnit.USD_PER_MT
    )
    assert observations
    assert observations[0].observation_date <= observations[-1].observation_date
    assert all(row.freight_unit is FreightUnit.USD_PER_MT for row in observations)

    from ml.features import prepare_freight_data
    ml_history = prepare_freight_data("data/reference/freight_rates.csv")
    assert not ml_history.empty
