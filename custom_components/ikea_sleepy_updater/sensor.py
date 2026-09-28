"""Diagnostic sensors for the IKEA Sleepy Device Firmware Updater."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SleepyConfigEntry
from .const import ICD_OPERATING_MODE_NAMES, OTA_UPDATE_STATE_NAMES
from .coordinator import SleepyDeviceManager
from .entity import SleepyEntity


@dataclass(frozen=True, kw_only=True)
class SleepySensorDescription(SensorEntityDescription):
    """Describes a sleepy-device diagnostic sensor."""

    value_fn: Callable[[SleepyDeviceManager, int], Any]


SENSORS: tuple[SleepySensorDescription, ...] = (
    SleepySensorDescription(
        key="ota_state",
        translation_key="ota_state",
        device_class=SensorDeviceClass.ENUM,
        options=list(OTA_UPDATE_STATE_NAMES.values()),
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda manager, node_id: manager.get_update_state_name(node_id),
    ),
    SleepySensorDescription(
        key="icd_mode",
        translation_key="icd_mode",
        device_class=SensorDeviceClass.ENUM,
        options=list(ICD_OPERATING_MODE_NAMES.values()),
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda manager, node_id: manager.get_operating_mode(node_id),
    ),
    SleepySensorDescription(
        key="promised_active",
        translation_key="promised_active",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda manager, node_id: manager.get_last_promised_duration(node_id),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SleepyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up diagnostic sensors for discovered IKEA sleepy devices."""
    manager = entry.runtime_data
    async_add_entities(
        SleepySensor(manager, node_id, description)
        for node_id in manager.get_device_node_ids()
        for description in SENSORS
    )


class SleepySensor(SleepyEntity, SensorEntity):
    """A diagnostic sensor reflecting OTA / ICD state."""

    entity_description: SleepySensorDescription

    def __init__(
        self,
        manager: SleepyDeviceManager,
        node_id: int,
        description: SleepySensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(manager, node_id)
        self.entity_description = description
        self._attr_unique_id = f"{node_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self._manager, self._node_id)
