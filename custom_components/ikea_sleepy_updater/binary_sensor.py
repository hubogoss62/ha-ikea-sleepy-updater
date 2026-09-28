"""Binary sensor exposing the keep-awake state for IKEA sleepy devices."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SleepyConfigEntry
from .coordinator import SleepyDeviceManager
from .entity import SleepyEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SleepyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the keep-awake binary sensor for discovered IKEA sleepy devices."""
    manager = entry.runtime_data
    async_add_entities(
        SleepyKeepAwakeSensor(manager, node_id)
        for node_id in manager.get_device_node_ids()
    )


class SleepyKeepAwakeSensor(SleepyEntity, BinarySensorEntity):
    """On while the integration is actively holding the device awake for an OTA."""

    _attr_translation_key = "keep_awake_active"
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, manager: SleepyDeviceManager, node_id: int) -> None:
        """Initialize the binary sensor."""
        super().__init__(manager, node_id)
        self._attr_unique_id = f"{node_id}_keep_awake_active"

    @property
    def is_on(self) -> bool:
        """Return True while the keep-awake loop is running for this node."""
        return self._manager.is_keeping_awake(self._node_id)
