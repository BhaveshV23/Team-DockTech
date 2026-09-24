"""Authoritative domain constants and controlled vocabularies for DockTech V1.

Defined strictly according to DATA_DICTIONARY.md and ARCHITECTURE.md.
"""

from enum import Enum


class ScenarioType(str, Enum):
    BASELINE = "BASELINE"
    ADVERSE = "ADVERSE"
    FAVORABLE = "FAVORABLE"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class CongestionLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class FreightUnit(str, Enum):
    USD_PER_MT = "USD_PER_MT"
    USD_PER_DAY = "USD_PER_DAY"


class MarineFuelType(str, Enum):
    VLSFO = "VLSFO"
    MGO = "MGO"


class MarketEntryAction(str, Enum):
    FIX_NOW = "FIX_NOW"
    WAIT = "WAIT"


class ContractStrategy(str, Enum):
    SPOT = "SPOT"
    SHORT_TERM_MULTIPLE_VOYAGE = "SHORT_TERM_MULTIPLE_VOYAGE"


class Commodity(str, Enum):
    THERMAL_COAL = "THERMAL_COAL"
    COKING_COAL = "COKING_COAL"


class ContractHorizon(str, Enum):
    SPOT = "SPOT"
    SHORT_TERM = "SHORT_TERM"
    FLEXIBLE = "FLEXIBLE"


class UserRole(str, Enum):
    VIEWER = "VIEWER"
    PLANNER = "PLANNER"
    MANAGER = "MANAGER"
    ADMINISTRATOR = "ADMINISTRATOR"


class DataType(str, Enum):
    SYNTHETIC = "SYNTHETIC"
    PROXY = "PROXY"
    ACTUAL = "ACTUAL"
    ESTIMATED = "ESTIMATED"
