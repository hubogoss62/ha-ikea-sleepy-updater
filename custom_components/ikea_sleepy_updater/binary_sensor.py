"""Binary sensors exposing the keep-awake state of sleepy Matter devices."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SleepyConfigEntry
from .coordinator import SleepyDeviceManager
from .entity import SleepyEntity


@dataclass(frozen=True, kw_only=True)
class SleepyBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a sleepy-device binary sensor."""

    is_on_fn: Callable[[SleepyDeviceManager, int], bool]


BINARY_SENSORS: tuple[SleepyBinarySensorDescription, ...] = (
    SleepyBinarySensorDescription(
        # On while the integration is actively holding the device awake for an OTA.
        key="keep_awake_active",
        translation_key="keep_awake_active",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda manager, node_id: manager.is_keeping_awake(node_id),
    ),
    SleepyBinarySensorDescription(
        # Whether the device accepts StayActiveRequest at all; if off, this
        # integration cannot keep it awake and the button must be pressed.
        key="keep_awake_supported",
        translation_key="keep_awake_supported",
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda manager, node_id: manager.supports_stay_active(node_id),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SleepyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensors for discovered sleepy devices."""
    manager = entry.runtime_data
    async_add_entities(
        SleepyBinarySensor(manager, node_id, description)
        for node_id in manager.get_device_node_ids()
        for description in BINARY_SENSORS
    )


class SleepyBinarySensor(SleepyEntity, BinarySensorEntity):
    """A diagnostic binary sensor for a sleepy device."""

    entity_description: SleepyBinarySensorDescription

    def __init__(
        self,
        manager: SleepyDeviceManager,
        node_id: int,
        description: SleepyBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(manager, node_id)
        self.entity_description = description
        self._attr_unique_id = f"{node_id}_{description.key}"

    @property
    def is_on(self) -> bool:
        """Return the sensor state."""
        return self.entity_description.is_on_fn(self._manager, self._node_id)
