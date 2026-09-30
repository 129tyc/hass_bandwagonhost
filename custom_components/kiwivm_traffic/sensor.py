"""Traffic sensors for a KiwiVM VPS."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import KiwiVMConfigEntry
from .const import DOMAIN
from .coordinator import KiwiVMTrafficCoordinator
from .traffic import TrafficSnapshot

_GIGABYTE = Decimal(1_000_000_000)

_SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="quota_bytes",
        translation_key="quota",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="used_bytes",
        translation_key="used",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="remaining_bytes",
        translation_key="remaining",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="usage_percent",
        translation_key="usage_percent",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="next_reset",
        translation_key="next_reset",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="updated_at",
        translation_key="updated_at",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KiwiVMConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the traffic sensors for one VPS."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        KiwiVMTrafficSensor(coordinator, entry, description)
        for description in _SENSORS
    )


class KiwiVMTrafficSensor(CoordinatorEntity[KiwiVMTrafficCoordinator], SensorEntity):
    """Expose one value from a shared per-VPS coordinator response."""

    entity_description: SensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: KiwiVMTrafficCoordinator,
        entry: KiwiVMConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._key = description.key
        self._attr_unique_id = f"{entry.unique_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            manufacturer="BandwagonHost",
            model="KiwiVM VPS",
            name=entry.title,
        )

    @property
    def available(self) -> bool:
        """Keep the last-success timestamp readable while current data is stale."""
        if self._key == "updated_at":
            return self.coordinator.data is not None
        return super().available and self._snapshot_value() is not None

    @property
    def native_value(self) -> Any:
        """Return the value for this metric, preserving missing values as unknown."""
        value = self._snapshot_value()
        if value is None:
            return None
        if self._key in {"quota_bytes", "used_bytes", "remaining_bytes"}:
            return float(value / _GIGABYTE)
        if self._key == "usage_percent":
            return float(value)
        return value

    def _snapshot_value(self) -> Any:
        """Read this entity's value from the latest successful API response."""
        snapshot: TrafficSnapshot | None = self.coordinator.data
        return getattr(snapshot, self._key) if snapshot is not None else None
