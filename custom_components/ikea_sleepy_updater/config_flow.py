"""Config flow for the IKEA Sleepy Device Firmware Updater integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_FALLBACK_INTERVAL,
    CONF_PRODUCT_FILTER,
    CONF_URL,
    CONF_VENDOR_SCOPE,
    DEFAULT_KEEP_AWAKE_FALLBACK_INTERVAL,
    DEFAULT_MATTER_URL,
    DEFAULT_PRODUCT_FILTER,
    DEFAULT_VENDOR_SCOPE,
    DOMAIN,
    MAX_FALLBACK_INTERVAL,
    MIN_FALLBACK_INTERVAL,
    VENDOR_SCOPE_ANY,
    VENDOR_SCOPE_IKEA,
)
from .coordinator import (
    SleepyConnectionError,
    async_validate_connection,
    discover_matter_url,
)

_LOGGER = logging.getLogger(__name__)


class SleepyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IKEA Sleepy Device Firmware Updater."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SleepyOptionsFlow:
        """Return the options flow handler."""
        return SleepyOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}

        if user_input is not None:
            url = user_input[CONF_URL]
            try:
                await async_validate_connection(self.hass, url)
            except SleepyConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - surface unexpected errors to the UI
                _LOGGER.exception("Unexpected error validating Matter Server")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title="IKEA Sleepy Device Firmware Updater",
                    data={CONF_URL: url},
                )

        default_url = (
            (user_input or {}).get(CONF_URL)
            or discover_matter_url(self.hass)
            or DEFAULT_MATTER_URL
        )
        schema = vol.Schema({vol.Required(CONF_URL, default=default_url): str})
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )


class SleepyOptionsFlow(OptionsFlow):
    """Handle the options flow (device selection and keep-awake tuning)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            user_input[CONF_PRODUCT_FILTER] = user_input.get(
                CONF_PRODUCT_FILTER, ""
            ).strip()
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_VENDOR_SCOPE,
                    default=options.get(CONF_VENDOR_SCOPE, DEFAULT_VENDOR_SCOPE),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[VENDOR_SCOPE_IKEA, VENDOR_SCOPE_ANY],
                        translation_key=CONF_VENDOR_SCOPE,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_PRODUCT_FILTER,
                    description={
                        "suggested_value": options.get(
                            CONF_PRODUCT_FILTER, DEFAULT_PRODUCT_FILTER
                        )
                    },
                ): str,
                vol.Required(
                    CONF_FALLBACK_INTERVAL,
                    default=options.get(
                        CONF_FALLBACK_INTERVAL, DEFAULT_KEEP_AWAKE_FALLBACK_INTERVAL
                    ),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_FALLBACK_INTERVAL, max=MAX_FALLBACK_INTERVAL),
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
