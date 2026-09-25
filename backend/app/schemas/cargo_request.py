from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class CommodityType(str, Enum):
    THERMAL_COAL = "THERMAL_COAL"
    COKING_COAL = "COKING_COAL"


class ContractHorizon(str, Enum):
    SPOT = "SPOT"
    SHORT_TERM = "SHORT_TERM"
    FLEXIBLE = "FLEXIBLE"


class CargoRequestCreate(BaseModel):
    commodity: CommodityType
    cargo_volume_mt: Optional[float] = Field(
        None, gt=0, description="Cargo volume in metric tonnes"
    )
    quantity_tonnes: Optional[float] = Field(
        None, gt=0, description="Alternative alias for cargo volume in MT"
    )
    origin_port_id: str = Field(..., min_length=1)
    destination_port_id: str = Field(..., min_length=1)
    earliest_delivery_date: Optional[date] = Field(None)
    delivery_start: Optional[date] = Field(None)
    latest_delivery_date: Optional[date] = Field(None)
    delivery_end: Optional[date] = Field(None)
    contract_horizon: ContractHorizon

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Volume alias check
            if data.get("cargo_volume_mt") is None:
                if "quantity_tonnes" in data and data["quantity_tonnes"] is not None:
                    data["cargo_volume_mt"] = data["quantity_tonnes"]

            # Delivery start date alias check
            if data.get("earliest_delivery_date") is None:
                if "delivery_start" in data and data["delivery_start"] is not None:
                    data["earliest_delivery_date"] = data["delivery_start"]

            # Delivery end date alias check
            if data.get("latest_delivery_date") is None:
                if "delivery_end" in data and data["delivery_end"] is not None:
                    data["latest_delivery_date"] = data["delivery_end"]

        return data

    @model_validator(mode="after")
    def validate_dates_and_ports(self) -> "CargoRequestCreate":
        if self.cargo_volume_mt is None:
            raise ValueError("Cargo volume (cargo_volume_mt or quantity_tonnes) is required and must be > 0")

        if self.earliest_delivery_date is None:
            raise ValueError("Earliest delivery date (earliest_delivery_date or delivery_start) is required")

        if self.latest_delivery_date is None:
            raise ValueError("Latest delivery date (latest_delivery_date or delivery_end) is required")

        if self.origin_port_id.strip().upper() == self.destination_port_id.strip().upper():
            raise ValueError("Origin port and destination port must be different")

        if self.latest_delivery_date < self.earliest_delivery_date:
            raise ValueError("latest_delivery_date must be on or after earliest_delivery_date")

        return self


class CargoRequestResponse(BaseModel):
    cargo_request_id: UUID
    user_id: UUID
    commodity: str
    cargo_volume_mt: float
    origin_port_id: str
    destination_port_id: str
    earliest_delivery_date: date
    latest_delivery_date: date
    contract_horizon: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
