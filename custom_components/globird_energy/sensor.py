"""Sensor platform for Globird Energy."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_IDENTIFIER, DOMAIN
from .coordinator import GlobirdEnergyCoordinator


@dataclass(frozen=True, kw_only=True)
class GlobirdSensorEntityDescription(SensorEntityDescription):
    """Describes Globird Energy sensor entity."""

    value_key: str


SENSORS: tuple[GlobirdSensorEntityDescription, ...] = (
    GlobirdSensorEntityDescription(
        key="daily_usage",
        translation_key="daily_usage",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_key="usage_kwh",
    ),
    GlobirdSensorEntityDescription(
        key="daily_usage_cost",
        translation_key="daily_usage_cost",
        native_unit_of_measurement="AUD",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_key="usage_cost",
    ),
    GlobirdSensorEntityDescription(
        key="daily_supply_charge",
        translation_key="daily_supply_charge",
        native_unit_of_measurement="AUD",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_key="supply_charge",
    ),
    GlobirdSensorEntityDescription(
        key="daily_total_cost",
        translation_key="daily_total_cost",
        native_unit_of_measurement="AUD",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_key="total_cost",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Globird Energy sensors from a config entry."""
    coordinator: GlobirdEnergyCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        GlobirdEnergySensor(coordinator, entry, description)
        for description in SENSORS
    )


class GlobirdEnergySensor(CoordinatorEntity[GlobirdEnergyCoordinator], SensorEntity):
    """Representation of a Globird Energy sensor."""

    entity_description: GlobirdSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: GlobirdEnergyCoordinator,
        entry: ConfigEntry,
        description: GlobirdSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        
        identifier = entry.data[CONF_IDENTIFIER]
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Globird Energy {identifier}",
            manufacturer="Globird Energy",
            model="Smart Meter",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://myaccount.globirdenergy.com.au",
        )

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.entity_description.value_key)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self.coordinator.data is None:
            return None
        
        return {
            "date": self.coordinator.data.get("date"),
            "identifier": self._entry.data[CONF_IDENTIFIER],
        }
