from uuid import UUID

from app.core.exceptions import AppError, not_found
from app.models.vehicle import Vehicle, VehicleCreate, VehiclePatch, seed_vehicle
from app.repositories.interfaces import Store


def require_supported(vehicle: Vehicle) -> None:
    seed = seed_vehicle()
    fields = ("manufacturer", "model", "model_year", "engine", "fuel_type", "transmission")
    if any(
        str(getattr(vehicle, key)).casefold() != str(getattr(seed, key)).casefold()
        for key in fields
    ):
        raise AppError(
            422,
            "unsupported_vehicle",
            f"The MVP supports only {seed.manufacturer} {seed.model} "
            f"{seed.model_year} {seed.engine} diesel/manual.",
        )


class VehicleService:
    def __init__(self, store: Store):
        self.store = store

    async def list(self):
        async with self.store.transaction() as repository:
            return await repository.list_vehicles()

    async def get(self, vehicle_id: UUID):
        async with self.store.transaction() as repository:
            vehicle = await repository.get_vehicle(vehicle_id)
            if not vehicle:
                raise not_found("Vehicle")
            return vehicle

    async def create(self, data: VehicleCreate):
        vehicle = Vehicle(**data.model_dump())
        require_supported(vehicle)
        async with self.store.transaction() as repository:
            await repository.save_vehicle(vehicle)
        return vehicle

    async def update(self, vehicle_id: UUID, data: VehiclePatch):
        async with self.store.transaction() as repository:
            current = await repository.get_vehicle(vehicle_id, lock=True)
            if not current:
                raise not_found("Vehicle")
            vehicle = Vehicle.model_validate(
                {**current.model_dump(), **data.model_dump(exclude_unset=True)}
            )
            require_supported(vehicle)
            await repository.save_vehicle(vehicle)
            return vehicle
