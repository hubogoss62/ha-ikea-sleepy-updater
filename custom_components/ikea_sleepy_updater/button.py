"""Buttons for manual recovery actions on IKEA sleepy devices."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SleepyConfigEntry
from .coordinator import SleepyDeviceManager
from .entity import SleepyEntity


@dataclass(frozen=True, kw_only=True)
class SleepyButtonDescription(ButtonEntityDescription):
    """Describes a sleepy-device action button."""

    press_fn: Callable[[SleepyDeviceManager, int], Awaitable[None]]


async def _keep_awake(manager: SleepyDeviceManager, node_id: int) -> None:
    await manager.keep_awake_once(node_id)


BUTTONS: tuple[SleepyButtonDescription, ...] = (
    SleepyButtonDescription(
        key="keep_awake",
        translation_key="keep_awake",
        entity_category=EntityCategory.CONFIG,
        press_fn=_keep_awake,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SleepyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up action buttons for discovered IKEA sleepy devices."""
    manager = entry.runtime_data
    async_add_entities(
        SleepyButton(manager, node_id, description)
        for node_id in manager.get_device_node_ids()
        for description in BUTTONS
    )


class SleepyButton(SleepyEntity, ButtonEntity):
    """A manual recovery button."""

    entity_description: SleepyButtonDescription

    def __init__(
        self,
        manager: SleepyDeviceManager,
        node_id: int,
        description: SleepyButtonDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(manager, node_id)
        self.entity_description = description
        self._attr_unique_id = f"{node_id}_{description.key}"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.entity_description.press_fn(self._manager, self._node_id)
