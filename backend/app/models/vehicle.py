from typing import Annotated
from uuid import UUID, uuid4

from pydantic import Field, StringConstraints, model_validator

from app.models.common import Schema, ShortText, Text

GOLF_ID = UUID("00000000-0000-4000-8000-000000000001")
MVP_IDENTITY = {
    "manufacturer": "Volkswagen",
    "model": "Golf Plus",
    "model_year": 2009,
    "engine": "2.0 TDI",
    "fuel_type": "Diesel",
    "transmission": "Manual",
    "engine_code": "CFFB",
}
VIN = Annotated[str, StringConstraints(to_upper=True, pattern=r"^[A-HJ-NPR-Z0-9]{17}$")]


class VehicleCreate(Schema):
    manufacturer: ShortText
    model: ShortText
    model_year: int = Field(ge=1886, le=2100)
    engine: ShortText
    fuel_type: ShortText
    transmission: ShortText
    engine_code: ShortText | None = None
    power_output: ShortText | None = None
    mileage_km: int | None = Field(default=None, ge=0, le=3000000)
    vin: VIN | None = Field(default=None, repr=False)
    additional_information: Text | None = None


class Vehicle(VehicleCreate):
    vehicle_id: UUID = Field(default_factory=uuid4)


class VehiclePatch(Schema):
    manufacturer: ShortText | None = None
    model: ShortText | None = None
    model_year: int | None = Field(default=None, ge=1886, le=2100)
    engine: ShortText | None = None
    fuel_type: ShortText | None = None
    transmission: ShortText | None = None
    engine_code: ShortText | None = None
    power_output: ShortText | None = None
    mileage_km: int | None = Field(default=None, ge=0, le=3000000)
    vin: VIN | None = Field(default=None, repr=False)
    additional_information: Text | None = None

    @model_validator(mode="after")
    def non_null_identity(self):
        required = {"manufacturer", "model", "model_year", "engine", "fuel_type", "transmission"}
        if any(getattr(self, key) is None for key in self.model_fields_set & required):
            raise ValueError("Vehicle identity fields cannot be null")
        return self


def seed_vehicle() -> Vehicle:
    return Vehicle(
        vehicle_id=GOLF_ID,
        **MVP_IDENTITY,
    )
