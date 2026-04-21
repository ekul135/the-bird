"""Sensor platform for The Bird."""
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
from .coordinator import TheBirdCoordinator


@dataclass(frozen=True, kw_only=True)
class TheBirdSensorEntityDescription(SensorEntityDescription):
    """Describes The Bird sensor entity."""

    value_key: str


# Daily data sensors - NO state_class because statistics are imported
# separately with correct historical dates via async_import_statistics.
# This avoids HA creating wrong-dated statistics when the sensor state changes.
DAILY_SENSORS: tuple[TheBirdSensorEntityDescription, ...] = (
    TheBirdSensorEntityDescription(
        key="usage",
        translation_key="usage",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_key="grid_usage_kwh",
    ),
    TheBirdSensorEntityDescription(
        key="usage_cost",
        translation_key="usage_cost",
        native_unit_of_measurement="AUD",
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        value_key="grid_usage_cost",
    ),
    TheBirdSensorEntityDescription(
        key="solar",
        translation_key="solar",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_key="solar_export_kwh",
    ),
    TheBirdSensorEntityDescription(
        key="solar_credit",
        translation_key="solar_credit",
        native_unit_of_measurement="AUD",
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        value_key="solar_export_credit",
    ),
    TheBirdSensorEntityDescription(
        key="super_export",
        translation_key="super_export",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_key="super_export_kwh",
    ),
    TheBirdSensorEntityDescription(
        key="super_export_credit",
        translation_key="super_export_credit",
        native_unit_of_measurement="AUD",
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        value_key="super_export_credit",
    ),
    TheBirdSensorEntityDescription(
        key="supply",
        translation_key="supply",
        native_unit_of_measurement="AUD",
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        value_key="supply_charge",
    ),
    TheBirdSensorEntityDescription(
        key="zerohero",
        translation_key="zerohero",
        native_unit_of_measurement="AUD",
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        value_key="zerohero_credit",
    ),
    TheBirdSensorEntityDescription(
        key="net_cost",
        translation_key="net_cost",
        native_unit_of_measurement="AUD",
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        value_key="total_cost",
    ),
)

# Snapshot sensors - MEASUREMENT state class, point-in-time values that don't roll up
SNAPSHOT_SENSORS: tuple[TheBirdSensorEntityDescription, ...] = (
    TheBirdSensorEntityDescription(
        key="account_balance",
        translation_key="account_balance",
        native_unit_of_measurement="AUD",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_key="account_balance",
    ),
    TheBirdSensorEntityDescription(
        key="unbilled_amount",
        translation_key="unbilled_amount",
        native_unit_of_measurement="AUD",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_key="unbilled_amount",
    ),
    TheBirdSensorEntityDescription(
        key="estimated_balance",
        translation_key="estimated_balance",
        native_unit_of_measurement="AUD",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_key="estimated_balance",
    ),
)

# Combined for entity setup
SENSORS = DAILY_SENSORS + SNAPSHOT_SENSORS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up The Bird sensors from a config entry."""
    coordinator: TheBirdCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        TheBirdSensor(coordinator, entry, description)
        for description in SENSORS
    )


class TheBirdSensor(CoordinatorEntity[TheBirdCoordinator], SensorEntity):
    """Representation of a The Bird sensor."""

    entity_description: TheBirdSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TheBirdCoordinator,
        entry: ConfigEntry,
        description: TheBirdSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        
        identifier = entry.data[CONF_IDENTIFIER]
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"The Bird {identifier}",
            manufacturer="The Bird",
            model="Smart Meter",
            entry_type=DeviceEntryType.SERVICE,
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
            "identifier": self._entry.data[CONF_IDENTIFIER],
            "data_date": self.coordinator.data.get("date"),
        }
