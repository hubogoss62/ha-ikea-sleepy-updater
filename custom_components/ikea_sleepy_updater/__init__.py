"""The IKEA Sleepy Device Firmware Updater integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import (
    CONF_FALLBACK_INTERVAL,
    CONF_PRODUCT_FILTER,
    CONF_URL,
    CONF_VENDOR_SCOPE,
    DEFAULT_KEEP_AWAKE_FALLBACK_INTERVAL,
    DEFAULT_MATTER_URL,
    DEFAULT_PRODUCT_FILTER,
    DEFAULT_VENDOR_SCOPE,
)
from .coordinator import SleepyConnectionError, SleepyDeviceManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SENSOR,
]

type SleepyConfigEntry = ConfigEntry[SleepyDeviceManager]


async def async_setup_entry(hass: HomeAssistant, entry: SleepyConfigEntry) -> bool:
    """Set up IKEA Sleepy Device Firmware Updater from a config entry."""
    url = entry.data.get(CONF_URL, DEFAULT_MATTER_URL)
    fallback_interval = entry.options.get(
        CONF_FALLBACK_INTERVAL, DEFAULT_KEEP_AWAKE_FALLBACK_INTERVAL
    )
    manager = SleepyDeviceManager(
        hass,
        url,
        fallback_interval=fallback_interval,
        vendor_scope=entry.options.get(CONF_VENDOR_SCOPE, DEFAULT_VENDOR_SCOPE),
        product_filter=entry.options.get(CONF_PRODUCT_FILTER, DEFAULT_PRODUCT_FILTER),
    )

    try:
        await manager.async_connect()
    except SleepyConnectionError as err:
        raise ConfigEntryNotReady(str(err)) from err

    node_ids = manager.get_device_node_ids()
    if node_ids:
        _LOGGER.info(
            "Watching %d sleepy Matter device(s) for firmware updates: %s",
            len(node_ids),
            ", ".join(
                f"{manager.get_node_name(n)} (node {n}, ICD mode "
                f"{manager.get_operating_mode(n)}, OTA state "
                f"{manager.get_update_state_name(n)}, StayActiveRequest "
                f"{'supported' if manager.supports_stay_active(n) else 'NOT supported'})"
                for n in node_ids
            ),
        )
    else:
        _LOGGER.warning(
            "No matching sleepy Matter device found; check the vendor scope and "
            "product filter in the integration options"
        )

    entry.runtime_data = manager
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_remove_stale_devices(
        hass, entry, {manager.get_device_identifier(n) for n in node_ids}
    )
    return True


@callback
def _async_remove_stale_devices(
    hass: HomeAssistant,
    entry: SleepyConfigEntry,
    current_identifiers: set[tuple[str, str]],
) -> None:
    """Detach this entry from devices it no longer provides entities for.

    Covers devices excluded by a new filter and the nameless duplicate devices
    earlier versions could create when linking to the Matter device failed.
    Detaching removes our entities from that device; a device left without any
    config entry is deleted by Home Assistant, the Matter device itself is kept.
    """
    registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
        if device.identifiers & current_identifiers:
            continue
        _LOGGER.debug("Removing stale device %s (%s)", device.name, device.identifiers)
        registry.async_update_device(device.id, remove_config_entry_id=entry.entry_id)


async def _async_options_updated(hass: HomeAssistant, entry: SleepyConfigEntry) -> None:
    """Reload the entry when options change so the new settings take effect."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: SleepyConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_disconnect()
    return unloaded
