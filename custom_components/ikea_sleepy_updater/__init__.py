"""The IKEA Sleepy Device Firmware Updater integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

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
                f"{manager.get_node_name(n)} (node {n})" for n in node_ids
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
    return True


async def _async_options_updated(hass: HomeAssistant, entry: SleepyConfigEntry) -> None:
    """Reload the entry when options change so the new settings take effect."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: SleepyConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_disconnect()
    return unloaded
