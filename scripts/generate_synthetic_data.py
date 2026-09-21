#!/usr/bin/env python3
"""
DockTech V1 — Synthetic Reference Data Generator
=================================================
Generates the 9 canonical reference datasets and manifest.json for DockTech V1
in accordance with:
  - DATA_DICTIONARY.md (Frozen Canonical Data Contract & Schemas)
  - SYNTHETIC_DATA_DESIGN.md (Data Generation Architecture & Math Models)
  - ARCHITECTURE.md (System Architecture & Pipeline Boundaries)
  - PRD.md (Product Scope & Feasibility Requirements)

Outputs:
  data/reference/
  ├── ports.csv             (15 rows)
  ├── berths.csv            (32 rows)
  ├── vessel_classes.csv    (6 rows)
  ├── routes.csv            (28 rows)
  ├── freight_rates.csv     (245,616 rows)
  ├── commodity_prices.csv  (1,462 rows)
  ├── fuel_prices.csv       (1,462 rows)
  ├── port_activity.csv     (10,965 rows)
  ├── scenario_defaults.csv (3 rows)
  └── manifest.json         (Execution metadata & SHA-256 checksums)

Total Reference Records: 259,589 rows.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import json
import math
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np


# ==============================================================================
# 1. CONFIGURATION DATASTRUCTURES
# ==============================================================================

@dataclass(frozen=True)
class PortConfig:
    port_id: str
    port_name: str
    country: str
    region: str
    max_loa_m: float
    max_beam_m: float
    max_draft_m: float
    handling_rate_tpd: float
    typical_turnaround_hours: float
    baseline_arrivals_lambda: float
    baseline_waiting_hours: float


@dataclass(frozen=True)
class BerthConfig:
    berth_id: str
    port_id: str
    berth_name: str
    commodity: str
    max_loa_m: float
    max_beam_m: float
    max_draft_m: float
    handling_rate_tpd: float


@dataclass(frozen=True)
class VesselClassConfig:
    vessel_class_id: str
    vessel_class_name: str
    dwt_min_mt: float
    dwt_max_mt: float
    loa_m: float
    beam_m: float
    draft_m: float
    speed_knots: float
    cargo_capacity_mt: float
    fuel_consumption_mt_day: float
    rate_per_mt_multiplier: float
    rate_per_day_base: float
    daily_volatility: float


@dataclass(frozen=True)
class RouteConfig:
    route_id: str
    origin_port_id: str
    destination_port_id: str
    commodity: str
    distance_nm: float
    typical_sailing_days: float


@dataclass(frozen=True)
class CommodityConfig:
    commodity_id: str
    market: str
    base_price: float
    mean_price: float
    reversion_speed: float
    volatility: float


@dataclass(frozen=True)
class FuelConfig:
    fuel_type: str
    base_price: float
    mean_price: float
    reversion_speed: float
    volatility: float
    is_active_cost_input: bool


@dataclass(frozen=True)
class ScenarioConfig:
    scenario_id: str
    scenario_name: str
    freight_change_pct: float
    fuel_change_pct: float
    delay_hours: float
    port_congestion_level: str
    description: str


@dataclass(frozen=True)
class SyntheticDataConfig:
    global_seed: int = 26006
    start_date: str = "2024-01-01"
    end_date: str = "2025-12-31"
    expected_days: int = 731
    provenance_source: str = "SYNTHETIC_GENERATOR_V1"
    provenance_data_type: str = "SYNTHETIC"
    ports: List[PortConfig] = field(default_factory=list)
    berths: List[BerthConfig] = field(default_factory=list)
    vessel_classes: List[VesselClassConfig] = field(default_factory=list)
    routes: List[RouteConfig] = field(default_factory=list)
    commodities: List[CommodityConfig] = field(default_factory=list)
    fuels: List[FuelConfig] = field(default_factory=list)
    scenarios: List[ScenarioConfig] = field(default_factory=list)


# ==============================================================================
# 2. DEFAULT V1 CONFIGURATION FACTORY
# ==============================================================================

def get_default_v1_config() -> SyntheticDataConfig:
    """Builds the frozen V1 default synthetic data configuration."""
    
    # --- 15 Ports (8 Origin overseas + 7 Destination India East Coast) ---
    ports = [
        # Overseas Origins
        PortConfig(
            port_id="NEWCASTLE",
            port_name="Newcastle",
            country="Australia",
            region="Oceania / Pacific",
            max_loa_m=300.0,
            max_beam_m=50.0,
            max_draft_m=16.5,
            handling_rate_tpd=40000.0,
            typical_turnaround_hours=60.0,
            baseline_arrivals_lambda=14.0,
            baseline_waiting_hours=18.0,
        ),
        PortConfig(
            port_id="GLADSTONE",
            port_name="Gladstone",
            country="Australia",
            region="Oceania / Pacific",
            max_loa_m=310.0,
            max_beam_m=52.0,
            max_draft_m=19.0,
            handling_rate_tpd=45000.0,
            typical_turnaround_hours=54.0,
            baseline_arrivals_lambda=12.0,
            baseline_waiting_hours=16.0,
        ),
        PortConfig(
            port_id="HAMPTON_ROADS",
            port_name="Hampton Roads",
            country="USA",
            region="North America / Atlantic",
            max_loa_m=300.0,
            max_beam_m=48.0,
            max_draft_m=16.5,
            handling_rate_tpd=35000.0,
            typical_turnaround_hours=66.0,
            baseline_arrivals_lambda=10.0,
            baseline_waiting_hours=20.0,
        ),
        PortConfig(
            port_id="BALTIMORE",
            port_name="Baltimore",
            country="USA",
            region="North America / Atlantic",
            max_loa_m=290.0,
            max_beam_m=45.0,
            max_draft_m=15.5,
            handling_rate_tpd=30000.0,
            typical_turnaround_hours=72.0,
            baseline_arrivals_lambda=8.0,
            baseline_waiting_hours=22.0,
        ),
        PortConfig(
            port_id="MAPUTO",
            port_name="Maputo",
            country="Mozambique",
            region="East Africa / Indian Ocean",
            max_loa_m=250.0,
            max_beam_m=38.0,
            max_draft_m=14.5,
            handling_rate_tpd=22000.0,
            typical_turnaround_hours=84.0,
            baseline_arrivals_lambda=6.0,
            baseline_waiting_hours=28.0,
        ),
        PortConfig(
            port_id="NACALA",
            port_name="Nacala",
            country="Mozambique",
            region="East Africa / Indian Ocean",
            max_loa_m=300.0,
            max_beam_m=50.0,
            max_draft_m=19.5,
            handling_rate_tpd=35000.0,
            typical_turnaround_hours=66.0,
            baseline_arrivals_lambda=6.0,
            baseline_waiting_hours=18.0,
        ),
        PortConfig(
            port_id="TABONEO",
            port_name="Taboneo",
            country="Indonesia",
            region="Southeast Asia / Pacific",
            max_loa_m=260.0,
            max_beam_m=42.0,
            max_draft_m=15.0,
            handling_rate_tpd=20000.0,
            typical_turnaround_hours=80.0,
            baseline_arrivals_lambda=10.0,
            baseline_waiting_hours=24.0,
        ),
        PortConfig(
            port_id="SAMARINDA",
            port_name="Samarinda",
            country="Indonesia",
            region="Southeast Asia / Pacific",
            max_loa_m=225.0,
            max_beam_m=33.0,
            max_draft_m=12.5,
            handling_rate_tpd=18000.0,
            typical_turnaround_hours=90.0,
            baseline_arrivals_lambda=8.0,
            baseline_waiting_hours=26.0,
        ),
        # Destination Ports (India East Coast)
        PortConfig(
            port_id="PARADIP",
            port_name="Paradip",
            country="India",
            region="East Coast India (Odisha)",
            max_loa_m=260.0,
            max_beam_m=40.0,
            max_draft_m=16.0,
            handling_rate_tpd=30000.0,
            typical_turnaround_hours=84.0,
            baseline_arrivals_lambda=12.0,
            baseline_waiting_hours=32.0,
        ),
        PortConfig(
            port_id="VISAKHAPATNAM",
            port_name="Visakhapatnam",
            country="India",
            region="East Coast India (Andhra Pradesh)",
            max_loa_m=280.0,
            max_beam_m=45.0,
            max_draft_m=17.5,
            handling_rate_tpd=30000.0,
            typical_turnaround_hours=78.0,
            baseline_arrivals_lambda=11.0,
            baseline_waiting_hours=30.0,
        ),
        PortConfig(
            port_id="GANGAVARAM",
            port_name="Gangavaram",
            country="India",
            region="East Coast India (Andhra Pradesh)",
            max_loa_m=300.0,
            max_beam_m=48.0,
            max_draft_m=19.5,
            handling_rate_tpd=35000.0,
            typical_turnaround_hours=72.0,
            baseline_arrivals_lambda=9.0,
            baseline_waiting_hours=24.0,
        ),
        PortConfig(
            port_id="GOPALPUR",
            port_name="Gopalpur",
            country="India",
            region="East Coast India (Odisha)",
            max_loa_m=230.0,
            max_beam_m=33.0,
            max_draft_m=14.5,
            handling_rate_tpd=20000.0,
            typical_turnaround_hours=90.0,
            baseline_arrivals_lambda=5.0,
            baseline_waiting_hours=26.0,
        ),
        PortConfig(
            port_id="DHAMRA",
            port_name="Dhamra",
            country="India",
            region="East Coast India (Odisha)",
            max_loa_m=300.0,
            max_beam_m=48.0,
            max_draft_m=19.0,
            handling_rate_tpd=35000.0,
            typical_turnaround_hours=72.0,
            baseline_arrivals_lambda=8.0,
            baseline_waiting_hours=22.0,
        ),
        PortConfig(
            port_id="SAGAR_SANDHEADS",
            port_name="Sagar-Sandheads",
            country="India",
            region="East Coast India (West Bengal anchorage)",
            max_loa_m=225.0,
            max_beam_m=32.5,
            max_draft_m=11.5,
            handling_rate_tpd=15000.0,
            typical_turnaround_hours=108.0,
            baseline_arrivals_lambda=5.0,
            baseline_waiting_hours=38.0,
        ),
        PortConfig(
            port_id="HALDIA",
            port_name="Haldia",
            country="India",
            region="East Coast India (West Bengal dock)",
            max_loa_m=220.0,
            max_beam_m=32.0,
            max_draft_m=10.5,
            handling_rate_tpd=16000.0,
            typical_turnaround_hours=112.0,
            baseline_arrivals_lambda=7.0,
            baseline_waiting_hours=42.0,
        ),
    ]

    # --- 32 Berths (Authoritative Operational Layer) ---
    berths = [
        # NEWCASTLE (3 berths)
        BerthConfig("NEWCASTLE_BERTH_1", "NEWCASTLE", "Kooragang Coal Terminal 1", "THERMAL_COAL", 290.0, 47.0, 16.2, 38000.0),
        BerthConfig("NEWCASTLE_BERTH_2", "NEWCASTLE", "Port Waratah Coal Berth 2", "COKING_COAL", 290.0, 47.0, 16.2, 38000.0),
        BerthConfig("NEWCASTLE_BERTH_3", "NEWCASTLE", "Carrington Coal Berth 3", "THERMAL_COAL", 300.0, 50.0, 16.5, 40000.0),
        # GLADSTONE (2 berths — Capesize capable)
        BerthConfig("GLADSTONE_BERTH_1", "GLADSTONE", "R.G. Tanna Coal Terminal 1", "THERMAL_COAL", 310.0, 52.0, 18.8, 42000.0),
        BerthConfig("GLADSTONE_BERTH_2", "GLADSTONE", "Barney Point Coal Berth 2", "COKING_COAL", 310.0, 52.0, 18.8, 42000.0),
        # HAMPTON_ROADS (2 berths)
        BerthConfig("HAMPTON_ROADS_BERTH_1", "HAMPTON_ROADS", "Pier 6 Coal Terminal", "COKING_COAL", 295.0, 46.0, 16.0, 32000.0),
        BerthConfig("HAMPTON_ROADS_BERTH_2", "HAMPTON_ROADS", "DTA Coal Terminal", "THERMAL_COAL", 290.0, 45.0, 15.5, 30000.0),
        # BALTIMORE (1 berth — Coking only, tests INSUFFICIENT_FEASIBILITY_DATA for thermal)
        BerthConfig("BALTIMORE_BERTH_1", "BALTIMORE", "Curtis Bay Coal Pier", "COKING_COAL", 285.0, 44.0, 15.2, 28000.0),
        # MAPUTO (2 berths)
        BerthConfig("MAPUTO_BERTH_1", "MAPUTO", "Matola Coal Terminal 1", "THERMAL_COAL", 245.0, 36.0, 14.0, 20000.0),
        BerthConfig("MAPUTO_BERTH_2", "MAPUTO", "Matola Coal Terminal 2", "COKING_COAL", 245.0, 36.0, 14.0, 20000.0),
        # NACALA (2 berths — Capesize capable deepwater)
        BerthConfig("NACALA_BERTH_1", "NACALA", "Nacala-a-Velha Coal Terminal 1", "THERMAL_COAL", 295.0, 48.0, 19.0, 32000.0),
        BerthConfig("NACALA_BERTH_2", "NACALA", "Nacala-a-Velha Coal Terminal 2", "COKING_COAL", 295.0, 48.0, 19.0, 32000.0),
        # TABONEO (1 berth — Thermal only, tests INSUFFICIENT_FEASIBILITY_DATA for coking)
        BerthConfig("TABONEO_BERTH_1", "TABONEO", "Taboneo Offshore Transshipment 1", "THERMAL_COAL", 255.0, 40.0, 14.5, 18000.0),
        # SAMARINDA (1 berth — Thermal only, riverine draft limit 12.0m)
        BerthConfig("SAMARINDA_BERTH_1", "SAMARINDA", "Muara Berau Coal Anchorage 1", "THERMAL_COAL", 220.0, 32.0, 12.0, 16000.0),
        # PARADIP (3 berths)
        BerthConfig("PARADIP_BERTH_1", "PARADIP", "Mechanised Coal Berth 1", "THERMAL_COAL", 255.0, 38.0, 15.0, 28000.0),
        BerthConfig("PARADIP_BERTH_2", "PARADIP", "South Quay Coal Berth 2", "COKING_COAL", 255.0, 38.0, 15.0, 28000.0),
        BerthConfig("PARADIP_BERTH_3", "PARADIP", "Central Quay Coal Berth 3", "COKING_COAL", 260.0, 40.0, 15.5, 30000.0),
        # VISAKHAPATNAM (3 berths)
        BerthConfig("VISAKHAPATNAM_BERTH_1", "VISAKHAPATNAM", "General Cargo Berth Coal 1", "THERMAL_COAL", 260.0, 40.0, 16.0, 28000.0),
        BerthConfig("VISAKHAPATNAM_BERTH_2", "VISAKHAPATNAM", "Outer Harbour Coal Berth 2", "COKING_COAL", 275.0, 42.0, 16.5, 30000.0),
        BerthConfig("VISAKHAPATNAM_BERTH_3", "VISAKHAPATNAM", "East Quay Bulk Berth 3", "COKING_COAL", 280.0, 45.0, 17.0, 32000.0),
        # GANGAVARAM (3 berths — Capesize capable deepwater >= 18.5m draft)
        BerthConfig("GANGAVARAM_BERTH_1", "GANGAVARAM", "Deepwater Coal Berth 1", "COKING_COAL", 300.0, 48.0, 19.0, 35000.0),
        BerthConfig("GANGAVARAM_BERTH_2", "GANGAVARAM", "Deepwater Coal Berth 2", "THERMAL_COAL", 300.0, 48.0, 19.0, 35000.0),
        BerthConfig("GANGAVARAM_BERTH_3", "GANGAVARAM", "Multipurpose Bulk Berth 3", "COKING_COAL", 290.0, 46.0, 18.5, 32000.0),
        # DHAMRA (3 berths — Capesize capable deepwater >= 18.5m draft)
        BerthConfig("DHAMRA_BERTH_1", "DHAMRA", "East Bulk Terminal 1", "THERMAL_COAL", 300.0, 48.0, 18.8, 35000.0),
        BerthConfig("DHAMRA_BERTH_2", "DHAMRA", "East Bulk Terminal 2", "COKING_COAL", 300.0, 48.0, 18.8, 35000.0),
        BerthConfig("DHAMRA_BERTH_3", "DHAMRA", "Bulk Cargo Jetty 3", "THERMAL_COAL", 290.0, 46.0, 18.5, 32000.0),
        # GOPALPUR (2 berths — Intermediate draft 13.5m)
        BerthConfig("GOPALPUR_BERTH_1", "GOPALPUR", "Gopalpur Coal Berth 1", "THERMAL_COAL", 225.0, 32.5, 13.5, 18000.0),
        BerthConfig("GOPALPUR_BERTH_2", "GOPALPUR", "Gopalpur Bulk Berth 2", "COKING_COAL", 225.0, 32.5, 13.5, 18000.0),
        # SAGAR_SANDHEADS (2 berths — Shallow riverine anchorage draft 11.2m, rejects Capesize/Kamsarmax/Panamax)
        BerthConfig("SAGAR_SANDHEADS_BERTH_1", "SAGAR_SANDHEADS", "Sagar Anchorage Point A", "THERMAL_COAL", 220.0, 32.0, 11.2, 14000.0),
        BerthConfig("SAGAR_SANDHEADS_BERTH_2", "SAGAR_SANDHEADS", "Sagar Anchorage Point B", "COKING_COAL", 220.0, 32.0, 11.2, 14000.0),
        # HALDIA (2 berths — Shallow dock basin draft 10.2m, rejects Capesize/Kamsarmax/Panamax)
        BerthConfig("HALDIA_BERTH_1", "HALDIA", "Haldia Dock Berth 4A", "THERMAL_COAL", 210.0, 31.0, 10.2, 15000.0),
        BerthConfig("HALDIA_BERTH_2", "HALDIA", "Haldia Dock Berth 4B", "COKING_COAL", 210.0, 31.0, 10.2, 15000.0),
    ]

    # --- 6 Canonical Dry-Bulk Carrier Classes ---
    vessel_classes = [
        VesselClassConfig(
            vessel_class_id="HANDYSIZE",
            vessel_class_name="Handysize",
            dwt_min_mt=28000.0,
            dwt_max_mt=38000.0,
            loa_m=180.0,
            beam_m=28.4,
            draft_m=10.2,
            speed_knots=13.0,
            cargo_capacity_mt=32000.0,
            fuel_consumption_mt_day=22.0,
            rate_per_mt_multiplier=1.30,
            rate_per_day_base=11500.0,
            daily_volatility=0.010,
        ),
        VesselClassConfig(
            vessel_class_id="SUPRAMAX",
            vessel_class_name="Supramax",
            dwt_min_mt=50000.0,
            dwt_max_mt=58000.0,
            loa_m=190.0,
            beam_m=32.2,
            draft_m=12.2,
            speed_knots=14.0,
            cargo_capacity_mt=53000.0,
            fuel_consumption_mt_day=28.0,
            rate_per_mt_multiplier=1.10,
            rate_per_day_base=14500.0,
            daily_volatility=0.012,
        ),
        VesselClassConfig(
            vessel_class_id="ULTRAMAX",
            vessel_class_name="Ultramax",
            dwt_min_mt=60000.0,
            dwt_max_mt=65000.0,
            loa_m=199.9,
            beam_m=32.2,
            draft_m=13.0,
            speed_knots=14.0,
            cargo_capacity_mt=61000.0,
            fuel_consumption_mt_day=30.0,
            rate_per_mt_multiplier=1.02,
            rate_per_day_base=16000.0,
            daily_volatility=0.015,
        ),
        VesselClassConfig(
            vessel_class_id="PANAMAX",
            vessel_class_name="Panamax",
            dwt_min_mt=68000.0,
            dwt_max_mt=78000.0,
            loa_m=225.0,
            beam_m=32.3,
            draft_m=14.2,
            speed_knots=14.0,
            cargo_capacity_mt=72000.0,
            fuel_consumption_mt_day=34.0,
            rate_per_mt_multiplier=0.92,
            rate_per_day_base=18000.0,
            daily_volatility=0.018,
        ),
        VesselClassConfig(
            vessel_class_id="KAMSARMAX",
            vessel_class_name="Kamsarmax",
            dwt_min_mt=80000.0,
            dwt_max_mt=85000.0,
            loa_m=229.0,
            beam_m=32.3,
            draft_m=14.5,
            speed_knots=14.0,
            cargo_capacity_mt=79000.0,
            fuel_consumption_mt_day=36.0,
            rate_per_mt_multiplier=0.86,
            rate_per_day_base=20000.0,
            daily_volatility=0.020,
        ),
        VesselClassConfig(
            vessel_class_id="CAPESIZE",
            vessel_class_name="Capesize",
            dwt_min_mt=160000.0,
            dwt_max_mt=185000.0,
            loa_m=292.0,
            beam_m=45.0,
            draft_m=18.2,
            speed_knots=14.5,
            cargo_capacity_mt=170000.0,
            fuel_consumption_mt_day=52.0,
            rate_per_mt_multiplier=0.72,
            rate_per_day_base=28000.0,
            daily_volatility=0.025,
        ),
    ]

    # --- 28 Trade Routes across Key Coal Corridors ---
    routes = [
        # Australia East Coast Corridor (8 routes)
        RouteConfig("NEWCASTLE_PARADIP_THERMAL", "NEWCASTLE", "PARADIP", "THERMAL_COAL", 5350.0, 15.9),
        RouteConfig("NEWCASTLE_PARADIP_COKING", "NEWCASTLE", "PARADIP", "COKING_COAL", 5350.0, 15.9),
        RouteConfig("NEWCASTLE_VISAKHAPATNAM_COKING", "NEWCASTLE", "VISAKHAPATNAM", "COKING_COAL", 5420.0, 16.1),
        RouteConfig("NEWCASTLE_HALDIA_THERMAL", "NEWCASTLE", "HALDIA", "THERMAL_COAL", 5480.0, 16.3),
        RouteConfig("GLADSTONE_PARADIP_COKING", "GLADSTONE", "PARADIP", "COKING_COAL", 5180.0, 15.4),
        RouteConfig("GLADSTONE_VISAKHAPATNAM_COKING", "GLADSTONE", "VISAKHAPATNAM", "COKING_COAL", 5250.0, 15.6),
        RouteConfig("GLADSTONE_GANGAVARAM_COKING", "GLADSTONE", "GANGAVARAM", "COKING_COAL", 5260.0, 15.7),
        RouteConfig("GLADSTONE_DHAMRA_THERMAL", "GLADSTONE", "DHAMRA", "THERMAL_COAL", 5150.0, 15.3),

        # Indonesia Corridor (6 routes — Thermal Coal only)
        RouteConfig("TABONEO_PARADIP_THERMAL", "TABONEO", "PARADIP", "THERMAL_COAL", 2350.0, 7.0),
        RouteConfig("TABONEO_VISAKHAPATNAM_THERMAL", "TABONEO", "VISAKHAPATNAM", "THERMAL_COAL", 2280.0, 6.8),
        RouteConfig("TABONEO_DHAMRA_THERMAL", "TABONEO", "DHAMRA", "THERMAL_COAL", 2380.0, 7.1),
        RouteConfig("SAMARINDA_PARADIP_THERMAL", "SAMARINDA", "PARADIP", "THERMAL_COAL", 2520.0, 7.5),
        RouteConfig("SAMARINDA_VISAKHAPATNAM_THERMAL", "SAMARINDA", "VISAKHAPATNAM", "THERMAL_COAL", 2450.0, 7.3),
        RouteConfig("SAMARINDA_HALDIA_THERMAL", "SAMARINDA", "HALDIA", "THERMAL_COAL", 2580.0, 7.7),

        # Southern Africa Corridor (8 routes)
        RouteConfig("MAPUTO_PARADIP_THERMAL", "MAPUTO", "PARADIP", "THERMAL_COAL", 4200.0, 12.5),
        RouteConfig("MAPUTO_PARADIP_COKING", "MAPUTO", "PARADIP", "COKING_COAL", 4200.0, 12.5),
        RouteConfig("MAPUTO_VISAKHAPATNAM_COKING", "MAPUTO", "VISAKHAPATNAM", "COKING_COAL", 4120.0, 12.3),
        RouteConfig("MAPUTO_GOPALPUR_THERMAL", "MAPUTO", "GOPALPUR", "THERMAL_COAL", 4160.0, 12.4),
        RouteConfig("NACALA_PARADIP_COKING", "NACALA", "PARADIP", "COKING_COAL", 3850.0, 11.5),
        RouteConfig("NACALA_VISAKHAPATNAM_COKING", "NACALA", "VISAKHAPATNAM", "COKING_COAL", 3780.0, 11.3),
        RouteConfig("NACALA_GANGAVARAM_COKING", "NACALA", "GANGAVARAM", "COKING_COAL", 3790.0, 11.3),
        RouteConfig("NACALA_DHAMRA_THERMAL", "NACALA", "DHAMRA", "THERMAL_COAL", 3880.0, 11.5),

        # US East Coast Corridor via Cape (6 routes — Metallurgical/Coking Coal focused)
        RouteConfig("HAMPTON_ROADS_PARADIP_COKING", "HAMPTON_ROADS", "PARADIP", "COKING_COAL", 11850.0, 35.3),
        RouteConfig("HAMPTON_ROADS_VISAKHAPATNAM_COKING", "HAMPTON_ROADS", "VISAKHAPATNAM", "COKING_COAL", 11780.0, 35.1),
        RouteConfig("HAMPTON_ROADS_GANGAVARAM_COKING", "HAMPTON_ROADS", "GANGAVARAM", "COKING_COAL", 11790.0, 35.1),
        RouteConfig("HAMPTON_ROADS_DHAMRA_COKING", "HAMPTON_ROADS", "DHAMRA", "COKING_COAL", 11880.0, 35.4),
        RouteConfig("BALTIMORE_PARADIP_COKING", "BALTIMORE", "PARADIP", "COKING_COAL", 11920.0, 35.5),
        RouteConfig("BALTIMORE_VISAKHAPATNAM_COKING", "BALTIMORE", "VISAKHAPATNAM", "COKING_COAL", 11850.0, 35.3),
    ]

    # --- 2 Commodities ---
    commodities = [
        CommodityConfig("THERMAL_COAL", "NEWCASTLE_BENCHMARK", base_price=135.0, mean_price=138.0, reversion_speed=0.02, volatility=0.006),
        CommodityConfig("COKING_COAL", "PREMIUM_COKING", base_price=260.0, mean_price=265.0, reversion_speed=0.02, volatility=0.006),
    ]

    # --- 2 Fuels (VLSFO active sea-going, MGO reference-only) ---
    fuels = [
        FuelConfig("VLSFO", base_price=590.0, mean_price=610.0, reversion_speed=0.025, volatility=0.008, is_active_cost_input=True),
        FuelConfig("MGO", base_price=780.0, mean_price=805.0, reversion_speed=0.025, volatility=0.008, is_active_cost_input=False),
    ]

    # --- 3 Scenario Defaults ---
    scenarios = [
        ScenarioConfig(
            scenario_id="BASELINE",
            scenario_name="Baseline",
            freight_change_pct=0.0,
            fuel_change_pct=0.0,
            delay_hours=0.0,
            port_congestion_level="MEDIUM",
            description="Standard baseline market conditions with normal forward expectations.",
        ),
        ScenarioConfig(
            scenario_id="ADVERSE",
            scenario_name="Adverse Market Shock",
            freight_change_pct=25.0,
            fuel_change_pct=15.0,
            delay_hours=48.0,
            port_congestion_level="HIGH",
            description="Simulated fleet tightness, high bunker inflation, and acute discharge port waiting times.",
        ),
        ScenarioConfig(
            scenario_id="FAVORABLE",
            scenario_name="Favorable Easing",
            freight_change_pct=-15.0,
            fuel_change_pct=-10.0,
            delay_hours=0.0,
            port_congestion_level="LOW",
            description="Softening freight indices, declining bunker prices, and expedited berthing queues.",
        ),
    ]

    return SyntheticDataConfig(
        global_seed=26006,
        start_date="2024-01-01",
        end_date="2025-12-31",
        expected_days=731,
        provenance_source="SYNTHETIC_GENERATOR_V1",
        provenance_data_type="SYNTHETIC",
        ports=ports,
        berths=berths,
        vessel_classes=vessel_classes,
        routes=routes,
        commodities=commodities,
        fuels=fuels,
        scenarios=scenarios,
    )


# ==============================================================================
# 3. STATIC DATASET GENERATORS
# ==============================================================================

def generate_ports(config: SyntheticDataConfig) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Generates rows for ports.csv matching DATA_DICTIONARY.md schema."""
    headers = [
        "port_id",
        "port_name",
        "country",
        "max_loa_m",
        "max_beam_m",
        "max_draft_m",
        "handling_rate_tpd",
        "typical_turnaround_hours",
        "source",
        "data_type",
    ]
    rows = []
    for p in config.ports:
        rows.append({
            "port_id": p.port_id,
            "port_name": p.port_name,
            "country": p.country,
            "max_loa_m": f"{p.max_loa_m:.1f}",
            "max_beam_m": f"{p.max_beam_m:.1f}",
            "max_draft_m": f"{p.max_draft_m:.1f}",
            "handling_rate_tpd": f"{p.handling_rate_tpd:.1f}",
            "typical_turnaround_hours": f"{p.typical_turnaround_hours:.1f}",
            "source": config.provenance_source,
            "data_type": config.provenance_data_type,
        })
    return headers, rows


def generate_berths(config: SyntheticDataConfig) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Generates rows for berths.csv matching DATA_DICTIONARY.md schema."""
    headers = [
        "berth_id",
        "port_id",
        "berth_name",
        "commodity",
        "max_loa_m",
        "max_beam_m",
        "max_draft_m",
        "handling_rate_tpd",
        "source",
        "data_type",
    ]
    rows = []
    for b in config.berths:
        rows.append({
            "berth_id": b.berth_id,
            "port_id": b.port_id,
            "berth_name": b.berth_name,
            "commodity": b.commodity,
            "max_loa_m": f"{b.max_loa_m:.1f}",
            "max_beam_m": f"{b.max_beam_m:.1f}",
            "max_draft_m": f"{b.max_draft_m:.1f}",
            "handling_rate_tpd": f"{b.handling_rate_tpd:.1f}",
            "source": config.provenance_source,
            "data_type": config.provenance_data_type,
        })
    return headers, rows


def generate_vessel_classes(config: SyntheticDataConfig) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Generates rows for vessel_classes.csv matching DATA_DICTIONARY.md schema."""
    headers = [
        "vessel_class_id",
        "vessel_class_name",
        "dwt_min_mt",
        "dwt_max_mt",
        "loa_m",
        "beam_m",
        "draft_m",
        "speed_knots",
        "cargo_capacity_mt",
        "fuel_consumption_mt_day",
        "source",
        "data_type",
    ]
    rows = []
    for v in config.vessel_classes:
        rows.append({
            "vessel_class_id": v.vessel_class_id,
            "vessel_class_name": v.vessel_class_name,
            "dwt_min_mt": f"{v.dwt_min_mt:.1f}",
            "dwt_max_mt": f"{v.dwt_max_mt:.1f}",
            "loa_m": f"{v.loa_m:.1f}",
            "beam_m": f"{v.beam_m:.1f}",
            "draft_m": f"{v.draft_m:.1f}",
            "speed_knots": f"{v.speed_knots:.1f}",
            "cargo_capacity_mt": f"{v.cargo_capacity_mt:.1f}",
            "fuel_consumption_mt_day": f"{v.fuel_consumption_mt_day:.1f}",
            "source": config.provenance_source,
            "data_type": config.provenance_data_type,
        })
    return headers, rows


def generate_routes(config: SyntheticDataConfig) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Generates rows for routes.csv matching DATA_DICTIONARY.md schema."""
    headers = [
        "route_id",
        "origin_port_id",
        "destination_port_id",
        "commodity",
        "distance_nm",
        "typical_sailing_days",
        "source",
        "data_type",
    ]
    rows = []
    for r in config.routes:
        rows.append({
            "route_id": r.route_id,
            "origin_port_id": r.origin_port_id,
            "destination_port_id": r.destination_port_id,
            "commodity": r.commodity,
            "distance_nm": f"{r.distance_nm:.1f}",
            "typical_sailing_days": f"{r.typical_sailing_days:.1f}",
            "source": config.provenance_source,
            "data_type": config.provenance_data_type,
        })
    return headers, rows


# ==============================================================================
# 4. TIME-SERIES GENERATORS
# ==============================================================================

def generate_date_list(start_date_str: str, expected_days: int) -> List[str]:
    """Generates a continuous sequence of ISO date strings."""
    start = datetime.date.fromisoformat(start_date_str)
    dates = [(start + datetime.timedelta(days=i)).isoformat() for i in range(expected_days)]
    return dates


def compute_market_regime_shock(t: int, b0: float) -> float:
    """
    Computes controlled synthetic market regime shock E(t):
      Regime 1 (t in [0, 212]): Baseline drift (2024-01-01 to 2024-07-31)
      Regime 2 (t in [213, 334]): Freight spike +30% to +45% (2024-08-01 to 2024-11-30)
      Regime 3 (t in [335, 515]): Market easing -25% (2024-12-01 to 2025-05-31)
      Regime 4 (t in [516, 730]): Volatile sideways oscillation +-12% (2025-06-01 to 2025-12-31)
    """
    if t < 213:
        return 0.0
    elif t < 335:
        # Surge up to +38% decaying over a 45-day half-life
        surge_day = t - 213
        return b0 * 0.38 * math.exp(-surge_day / 70.0)
    elif t < 516:
        # Correction downward by up to -25%
        easing_day = t - 335
        return -b0 * 0.25 * (1.0 - math.exp(-easing_day / 50.0))
    else:
        # Range-bound sideways oscillation +-10%
        wave_day = t - 516
        return b0 * 0.10 * math.sin(2.0 * math.pi * wave_day / 45.0)


def generate_freight_rates(
    config: SyntheticDataConfig, rng: np.random.Generator, dates: List[str]
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Generates 245,616 rows for freight_rates.csv matching DATA_DICTIONARY.md:
      28 routes x 6 vessel classes x 2 units x 731 dates = 245,616 rows.
    Implements structural model:
      R(t) = [B0 + T(t) + S(t) + E(t)] x Mv x Mr + epsilon(t)
    Enforces:
      - For USD_PER_MT: CAPESIZE < PANAMAX < SUPRAMAX
      - For USD_PER_DAY: CAPESIZE > PANAMAX > SUPRAMAX
      - Volatility hierarchy: CAPESIZE (2.5%) > PANAMAX (1.8%) > SUPRAMAX (1.2%)
      - Non-negativity and temporal continuity via AR(1) residuals
    """
    headers = [
        "freight_rate_id",
        "observation_date",
        "route_id",
        "vessel_class_id",
        "freight_value",
        "freight_unit",
        "currency",
        "data_type",
        "source",
    ]
    rows = []
    record_counter = 0

    num_days = len(dates)
    rho = 0.88
    rho_scale = math.sqrt(1.0 - rho ** 2)

    for route in config.routes:
        # Distance-driven base voyage rate per metric tonne
        route_base_mt = 3.5 + (route.distance_nm / 1000.0) * 2.25

        for vc in config.vessel_classes:
            for freight_unit in ["USD_PER_MT", "USD_PER_DAY"]:
                # Determine baseline and scale
                if freight_unit == "USD_PER_MT":
                    b0 = route_base_mt * vc.rate_per_mt_multiplier
                    daily_vol = vc.daily_volatility
                    min_floor = max(2.5, b0 * 0.35)
                else:  # USD_PER_DAY
                    route_distance_factor = 0.90 + (route.distance_nm / 10000.0) * 0.15
                    b0 = vc.rate_per_day_base * route_distance_factor
                    daily_vol = vc.daily_volatility
                    min_floor = max(4000.0, b0 * 0.35)

                # Pre-generate standard normal noise for this slice
                innovations = rng.standard_normal(num_days)
                eps = 0.0

                for t, obs_date in enumerate(dates):
                    record_counter += 1
                    rate_id = f"FR_{record_counter:06d}"

                    # 1. Macro Trend T(t)
                    trend = b0 * 0.06 * math.sin(2.0 * math.pi * t / 500.0) + (b0 * 0.00004 * t)

                    # 2. Seasonality S(t) (Monsoon dip in Q3, winter peaks in Q4/Q1)
                    d_year = t % 365
                    seasonality = b0 * 0.08 * math.cos(2.0 * math.pi * d_year / 365.25 + 0.6)

                    # 3. Market Regime Shock E(t)
                    shock = compute_market_regime_shock(t, b0)

                    # 4. AR(1) Residual Noise epsilon(t)
                    shock_sigma = b0 * daily_vol
                    eps = rho * eps + shock_sigma * rho_scale * innovations[t]

                    # Composite Rate R(t)
                    val = b0 + trend + seasonality + shock + eps
                    if val < min_floor:
                        val = min_floor

                    rows.append({
                        "freight_rate_id": rate_id,
                        "observation_date": obs_date,
                        "route_id": route.route_id,
                        "vessel_class_id": vc.vessel_class_id,
                        "freight_value": f"{val:.2f}",
                        "freight_unit": freight_unit,
                        "currency": "USD",
                        "data_type": config.provenance_data_type,
                        "source": config.provenance_source,
                    })

    return headers, rows


def generate_commodity_prices(
    config: SyntheticDataConfig, rng: np.random.Generator, dates: List[str]
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Generates 1,462 rows for commodity_prices.csv matching DATA_DICTIONARY.md:
      2 commodities x 1 market x 731 dates = 1,462 rows.
    Implements mean-reverting jump diffusion with macro correlation.
    """
    headers = [
        "commodity_price_id",
        "observation_date",
        "commodity",
        "market",
        "price_value",
        "currency",
        "unit",
        "data_type",
        "source",
    ]
    rows = []
    record_counter = 0
    num_days = len(dates)

    for comm in config.commodities:
        innovations = rng.standard_normal(num_days)
        price = comm.base_price

        for t, obs_date in enumerate(dates):
            record_counter += 1
            price_id = f"CP_{record_counter:06d}"

            # Mean-reverting drift: theta * (mu - P_{t-1})
            drift = comm.reversion_speed * (comm.mean_price - price)
            # Volatility shock
            shock = comm.base_price * comm.volatility * innovations[t]
            # Macro shock component aligned with global freight regimes
            macro_factor = 0.0
            if 213 <= t < 335:
                macro_factor = 0.15  # Commodity uptick during freight surge
            elif 335 <= t < 516:
                macro_factor = -0.10  # Commodity softening during market easing

            price = price + drift + shock + (comm.base_price * 0.0003 * macro_factor)
            price = max(comm.base_price * 0.70, price)

            rows.append({
                "commodity_price_id": price_id,
                "observation_date": obs_date,
                "commodity": comm.commodity_id,
                "market": comm.market,
                "price_value": f"{price:.2f}",
                "currency": "USD",
                "unit": "USD_PER_MT",
                "data_type": config.provenance_data_type,
                "source": config.provenance_source,
            })

    return headers, rows


def generate_fuel_prices(
    config: SyntheticDataConfig, rng: np.random.Generator, dates: List[str]
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Generates 1,462 rows for fuel_prices.csv matching DATA_DICTIONARY.md:
      2 fuel types x 731 dates = 1,462 rows.
      VLSFO is active sea-going transit fuel; MGO is reference-only.
    """
    headers = [
        "fuel_price_id",
        "observation_date",
        "fuel_type",
        "price_value",
        "currency",
        "unit",
        "data_type",
        "source",
    ]
    rows = []
    record_counter = 0
    num_days = len(dates)

    for fuel in config.fuels:
        innovations = rng.standard_normal(num_days)
        price = fuel.base_price

        for t, obs_date in enumerate(dates):
            record_counter += 1
            price_id = f"FP_{record_counter:06d}"

            # Mean-reverting drift
            drift = fuel.reversion_speed * (fuel.mean_price - price)
            # Volatility shock
            shock = fuel.base_price * fuel.volatility * innovations[t]
            # Macro fuel pressure in Regime 2 (freight spike)
            if 213 <= t < 335:
                drift += fuel.base_price * 0.0005

            price = price + drift + shock
            price = max(fuel.base_price * 0.65, price)

            rows.append({
                "fuel_price_id": price_id,
                "observation_date": obs_date,
                "fuel_type": fuel.fuel_type,
                "price_value": f"{price:.2f}",
                "currency": "USD",
                "unit": "USD_PER_MT",
                "data_type": config.provenance_data_type,
                "source": config.provenance_source,
            })

    return headers, rows


def generate_port_activity(
    config: SyntheticDataConfig, rng: np.random.Generator, dates: List[str]
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Generates 10,965 rows for port_activity.csv matching DATA_DICTIONARY.md:
      15 ports x 731 dates = 10,965 rows.
    Implements:
      Arrivals ~ Poisson(lambda)
      Waiting = W_base * (Arrivals / lambda)^1.5 + noise
      Turnaround = Waiting + HandlingBase + noise
      Congestion: LOW (<24h), MEDIUM (24-60h), HIGH (>=60h)
    """
    headers = [
        "activity_id",
        "observation_date",
        "port_id",
        "vessel_arrivals",
        "average_waiting_hours",
        "average_turnaround_hours",
        "congestion_level",
        "source",
        "data_type",
    ]
    rows = []
    record_counter = 0
    num_days = len(dates)

    for port in config.ports:
        lam = port.baseline_arrivals_lambda
        w_base = port.baseline_waiting_hours
        handling_base = max(24.0, port.typical_turnaround_hours - w_base)

        # Generate arrivals and noise vectors
        arrivals_array = rng.poisson(lam, num_days)
        waiting_noise = rng.normal(0.0, 3.5, num_days)
        turnaround_noise = rng.normal(0.0, 4.0, num_days)

        for t, obs_date in enumerate(dates):
            record_counter += 1
            activity_id = f"PA_{record_counter:06d}"

            arr = int(arrivals_array[t])
            # Non-linear queuing response
            queue_ratio = max(0.2, arr / lam)
            waiting_val = w_base * (queue_ratio ** 1.5) + waiting_noise[t]
            waiting_val = max(0.0, round(waiting_val, 1))

            turnaround_val = waiting_val + handling_base + turnaround_noise[t]
            turnaround_val = max(waiting_val + 12.0, round(turnaround_val, 1))

            # Categorical Congestion Standard
            if waiting_val < 24.0:
                congestion = "LOW"
            elif waiting_val < 60.0:
                congestion = "MEDIUM"
            else:
                congestion = "HIGH"

            rows.append({
                "activity_id": activity_id,
                "observation_date": obs_date,
                "port_id": port.port_id,
                "vessel_arrivals": str(arr),
                "average_waiting_hours": f"{waiting_val:.1f}",
                "average_turnaround_hours": f"{turnaround_val:.1f}",
                "congestion_level": congestion,
                "source": config.provenance_source,
                "data_type": config.provenance_data_type,
            })

    return headers, rows


def generate_scenario_defaults(config: SyntheticDataConfig) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Generates 3 rows for scenario_defaults.csv matching DATA_DICTIONARY.md schema."""
    headers = [
        "scenario_id",
        "scenario_name",
        "freight_change_pct",
        "fuel_change_pct",
        "delay_hours",
        "port_congestion_level",
        "description",
        "source",
        "data_type",
    ]
    rows = []
    for s in config.scenarios:
        rows.append({
            "scenario_id": s.scenario_id,
            "scenario_name": s.scenario_name,
            "freight_change_pct": f"{s.freight_change_pct:.1f}",
            "fuel_change_pct": f"{s.fuel_change_pct:.1f}",
            "delay_hours": f"{s.delay_hours:.1f}",
            "port_congestion_level": s.port_congestion_level,
            "description": s.description,
            "source": config.provenance_source,
            "data_type": config.provenance_data_type,
        })
    return headers, rows


# ==============================================================================
# 5. GENERATOR-SIDE INVARIANT & INTEGRITY CHECKS
# ==============================================================================

def validate_generator_invariants(
    config: SyntheticDataConfig,
    datasets: Dict[str, Tuple[List[str], List[Dict[str, Any]]]],
    dates: List[str],
) -> None:
    """
    Performs comprehensive in-memory relational integrity and domain invariant checks
    prior to writing CSV files. Fails loudly with an AssertionError if any check fails.
    """
    print("[Invariant Check] Validating dataset schemas, foreign keys, and domain rules...")

    # 1. Check Expected Record Counts
    expected_counts = {
        "ports": 15,
        "berths": 32,
        "vessel_classes": 6,
        "routes": 28,
        "freight_rates": 245616,
        "commodity_prices": 1462,
        "fuel_prices": 1462,
        "port_activity": 10965,
        "scenario_defaults": 3,
    }

    for key, expected_len in expected_counts.items():
        actual_len = len(datasets[key][1])
        assert actual_len == expected_len, (
            f"Row count mismatch for '{key}': expected {expected_len}, got {actual_len}"
        )

    # 2. Date Range Continuity
    assert len(dates) == config.expected_days == 731, (
        f"Expected exactly 731 calendar days, got {len(dates)}"
    )
    assert dates[0] == config.start_date == "2024-01-01"
    assert dates[-1] == config.end_date == "2025-12-31"

    # 3. Foreign Key Integrity
    port_ids = {p["port_id"] for p in datasets["ports"][1]}
    assert len(port_ids) == 15, "Non-unique port_id in ports"

    # Berths -> Ports
    for b in datasets["berths"][1]:
        assert b["port_id"] in port_ids, f"Orphan berth port_id: {b['port_id']}"

    # Routes -> Ports
    route_ids = set()
    for r in datasets["routes"][1]:
        assert r["origin_port_id"] in port_ids, f"Orphan route origin: {r['origin_port_id']}"
        assert r["destination_port_id"] in port_ids, f"Orphan route destination: {r['destination_port_id']}"
        assert r["origin_port_id"] != r["destination_port_id"], "Self-loop route detected"
        route_ids.add(r["route_id"])
    assert len(route_ids) == 28, "Duplicate route_id found"

    # Vessel Classes
    vc_ids = {v["vessel_class_id"] for v in datasets["vessel_classes"][1]}
    assert len(vc_ids) == 6, "Duplicate vessel_class_id found"

    # Port Activity -> Ports
    for pa in datasets["port_activity"][1]:
        assert pa["port_id"] in port_ids, f"Orphan port_activity port_id: {pa['port_id']}"

    # 4. Physical Dimension Rules
    # Cargo capacity < DWT max
    for v in datasets["vessel_classes"][1]:
        cap = float(v["cargo_capacity_mt"])
        dwt = float(v["dwt_max_mt"])
        assert cap < dwt, f"Vessel class {v['vessel_class_id']} cargo capacity >= dwt_max"

    # Berth draft <= Port draft
    port_draft_map = {p["port_id"]: float(p["max_draft_m"]) for p in datasets["ports"][1]}
    for b in datasets["berths"][1]:
        berth_draft = float(b["max_draft_m"])
        port_draft = port_draft_map[b["port_id"]]
        assert berth_draft <= port_draft, (
            f"Berth {b['berth_id']} draft ({berth_draft}m) exceeds port draft ({port_draft}m)"
        )

    # 5. Provenance Consistency
    for name, (_, rows) in datasets.items():
        for r in rows:
            assert r["source"] == config.provenance_source, f"Invalid source in {name}: {r['source']}"
            assert r["data_type"] == config.provenance_data_type, f"Invalid data_type in {name}: {r['data_type']}"

    # 6. Freight Cross-Sectional Economics Check (Sanity Sampling)
    # Check that for any given route/date, Capesize $/MT < Supramax $/MT
    fr_rows = datasets["freight_rates"][1]
    # Sample first observation date and first route
    sample_date = dates[0]
    sample_route = datasets["routes"][1][0]["route_id"]
    rates_sample_mt = {
        r["vessel_class_id"]: float(r["freight_value"])
        for r in fr_rows[:500]
        if r["observation_date"] == sample_date and r["route_id"] == sample_route and r["freight_unit"] == "USD_PER_MT"
    }
    rates_sample_day = {
        r["vessel_class_id"]: float(r["freight_value"])
        for r in fr_rows[:500]
        if r["observation_date"] == sample_date and r["route_id"] == sample_route and r["freight_unit"] == "USD_PER_DAY"
    }

    if "CAPESIZE" in rates_sample_mt and "SUPRAMAX" in rates_sample_mt:
        assert rates_sample_mt["CAPESIZE"] < rates_sample_mt["SUPRAMAX"], (
            f"Economies of scale violation in $/MT: Capesize {rates_sample_mt['CAPESIZE']} >= Supramax {rates_sample_mt['SUPRAMAX']}"
        )
    if "CAPESIZE" in rates_sample_day and "SUPRAMAX" in rates_sample_day:
        assert rates_sample_day["CAPESIZE"] > rates_sample_day["SUPRAMAX"], (
            f"TCE hire hierarchy violation in $/day: Capesize {rates_sample_day['CAPESIZE']} <= Supramax {rates_sample_day['SUPRAMAX']}"
        )

    print("[Invariant Check] All generator invariants passed successfully.")


# ==============================================================================
# 6. CSV & MANIFEST WRITERS
# ==============================================================================

def write_csv_file(filepath: Path, headers: List[str], rows: List[Dict[str, Any]]) -> str:
    """Writes dataset to CSV deterministically and returns its SHA-256 hex digest."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    # Compute SHA-256
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def write_manifest_file(
    filepath: Path,
    config: SyntheticDataConfig,
    checksums: Dict[str, str],
    record_counts: Dict[str, int],
) -> None:
    """Writes data/reference/manifest.json containing execution metadata and checksums."""
    manifest_data = {
        "generator_name": "DockTech Synthetic Generator",
        "generator_version": "1.0.0",
        "master_seed": config.global_seed,
        "generation_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "history_start_date": config.start_date,
        "history_end_date": config.end_date,
        "record_counts": record_counts,
        "checksums_sha256": checksums,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    print(f"[Manifest] Written: {filepath}")


# ==============================================================================
# 7. MAIN PIPELINE EXECUTION
# ==============================================================================

def run_pipeline(output_dir: Path, master_seed: int = 26006) -> None:
    """Orchestrates generation of all 9 canonical CSVs and manifest.json."""
    print("=" * 70)
    print("  DockTech V1 — Synthetic Data Generation Pipeline")
    print(f"  Master Seed : {master_seed}")
    print(f"  Output Dir  : {output_dir.resolve()}")
    print("=" * 70)

    # 1. Initialize Configuration and RNG
    config = get_default_v1_config()
    if master_seed != config.global_seed:
        config = dataclass.replace(config, global_seed=master_seed)

    rng = np.random.default_rng(config.global_seed)
    dates = generate_date_list(config.start_date, config.expected_days)
    print(f"[Pipeline] Initialized calendar: {dates[0]} to {dates[-1]} ({len(dates)} dates)")

    # 2. Generate Static Datasets
    print("[Pipeline] Generating static reference data...")
    ports_headers, ports_rows = generate_ports(config)
    berths_headers, berths_rows = generate_berths(config)
    vc_headers, vc_rows = generate_vessel_classes(config)
    routes_headers, routes_rows = generate_routes(config)

    # 3. Generate Time-Series Datasets
    print("[Pipeline] Generating time-series datasets...")
    fr_headers, fr_rows = generate_freight_rates(config, rng, dates)
    cp_headers, cp_rows = generate_commodity_prices(config, rng, dates)
    fp_headers, fp_rows = generate_fuel_prices(config, rng, dates)
    pa_headers, pa_rows = generate_port_activity(config, rng, dates)

    # 4. Generate Scenario Presets
    print("[Pipeline] Generating scenario defaults...")
    sc_headers, sc_rows = generate_scenario_defaults(config)

    datasets: Dict[str, Tuple[List[str], List[Dict[str, Any]]]] = {
        "ports": (ports_headers, ports_rows),
        "berths": (berths_headers, berths_rows),
        "vessel_classes": (vc_headers, vc_rows),
        "routes": (routes_headers, routes_rows),
        "freight_rates": (fr_headers, fr_rows),
        "commodity_prices": (cp_headers, cp_rows),
        "fuel_prices": (fp_headers, fp_rows),
        "port_activity": (pa_headers, pa_rows),
        "scenario_defaults": (sc_headers, sc_rows),
    }

    # 5. Validate Invariants in Memory
    validate_generator_invariants(config, datasets, dates)

    # 6. Write CSV Files and Compute Checksums
    checksums: Dict[str, str] = {}
    record_counts: Dict[str, int] = {}
    total_records = 0

    print("[Pipeline] Writing canonical CSV files to target directory...")
    for key, (headers, rows) in datasets.items():
        filename = f"{key}.csv"
        filepath = output_dir / filename
        sha256 = write_csv_file(filepath, headers, rows)
        checksums[filename] = sha256
        record_counts[key] = len(rows)
        total_records += len(rows)
        print(f"  -> {filename:<22} : {len(rows):>8,d} rows | SHA-256: {sha256[:12]}...")

    print(f"[Pipeline] Total reference records written: {total_records:,d}")
    assert total_records == 259589, f"Expected total 259,589 rows, got {total_records}"

    # 7. Write Manifest
    manifest_path = output_dir / "manifest.json"
    write_manifest_file(manifest_path, config, checksums, record_counts)

    print("=" * 70)
    print("  [SUCCESS] All 9 canonical reference CSVs & manifest.json generated.")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic reference datasets for DockTech V1."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/reference",
        help="Target output directory for reference CSVs (default: data/reference)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=26006,
        help="Master random number seed (default: 26006)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    target_dir = repo_root / args.output_dir

    run_pipeline(output_dir=target_dir, master_seed=args.seed)


if __name__ == "__main__":
    main()
