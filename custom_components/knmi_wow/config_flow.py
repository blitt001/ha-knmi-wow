"""Config flow for KNMI WOW integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_AUTH_KEY,
    CONF_DEBUG_MODE,
    CONF_SENSOR_DEW_POINT,
    CONF_SENSOR_HUMIDITY,
    CONF_SENSOR_PRESSURE,
    CONF_SENSOR_RAIN,
    CONF_SENSOR_RAIN_DAILY,
    CONF_SENSOR_TEMPERATURE,
    CONF_SENSOR_WIND_DIR,
    CONF_SENSOR_WIND_GUST,
    CONF_SENSOR_WIND_SPEED,
    CONF_SITE_ID,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MIN_UPDATE_INTERVAL,
)
from .coordinator import test_connection

_LOGGER = logging.getLogger(__name__)


class KNMIWOWConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for KNMI WOW."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate credentials
            site_id = user_input[CONF_SITE_ID]
            auth_key = user_input[CONF_AUTH_KEY]

            # Check if already configured
            await self.async_set_unique_id(site_id)
            self._abort_if_unique_id_configured()

            # Test connection (optional, might fail if no weather data)
            # For now, we trust the user's credentials
            self._data = user_input
            return await self.async_step_sensors()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SITE_ID): str,
                    vol.Required(CONF_AUTH_KEY): str,
                }
            ),
            errors=errors,
        )

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the sensor mapping step."""
        if user_input is not None:
            # Merge sensor mappings with credentials
            self._data.update(user_input)
            return await self.async_step_options()

        # Create entity selector for sensors
        entity_selector = selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="sensor",
                multiple=False,
            )
        )

        return self.async_show_form(
            step_id="sensors",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_SENSOR_TEMPERATURE): entity_selector,
                    vol.Optional(CONF_SENSOR_HUMIDITY): entity_selector,
                    vol.Optional(CONF_SENSOR_PRESSURE): entity_selector,
                    vol.Optional(CONF_SENSOR_RAIN): entity_selector,
                    vol.Optional(CONF_SENSOR_RAIN_DAILY): entity_selector,
                    vol.Optional(CONF_SENSOR_WIND_SPEED): entity_selector,
                    vol.Optional(CONF_SENSOR_WIND_DIR): entity_selector,
                    vol.Optional(CONF_SENSOR_WIND_GUST): entity_selector,
                    vol.Optional(CONF_SENSOR_DEW_POINT): entity_selector,
                }
            ),
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the options step."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(
                title=f"KNMI WOW ({self._data[CONF_SITE_ID][:8]}...)",
                data=self._data,
            )

        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_UPDATE_INTERVAL, max=60),
                    ),
                    vol.Optional(CONF_DEBUG_MODE, default=False): bool,
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> KNMIWOWOptionsFlow:
        """Get the options flow for this handler."""
        return KNMIWOWOptionsFlow()


class KNMIWOWOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for KNMI WOW."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Create entity selector for sensors
        entity_selector = selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="sensor",
                multiple=False,
            )
        )

        # Get current values
        current_data = {**self.config_entry.data, **self.config_entry.options}

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=current_data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_UPDATE_INTERVAL, max=60),
                    ),
                    vol.Optional(
                        CONF_DEBUG_MODE,
                        default=current_data.get(CONF_DEBUG_MODE, False),
                    ): bool,
                    vol.Optional(
                        CONF_SENSOR_TEMPERATURE,
                        description={"suggested_value": current_data.get(CONF_SENSOR_TEMPERATURE)},
                    ): entity_selector,
                    vol.Optional(
                        CONF_SENSOR_HUMIDITY,
                        description={"suggested_value": current_data.get(CONF_SENSOR_HUMIDITY)},
                    ): entity_selector,
                    vol.Optional(
                        CONF_SENSOR_PRESSURE,
                        description={"suggested_value": current_data.get(CONF_SENSOR_PRESSURE)},
                    ): entity_selector,
                    vol.Optional(
                        CONF_SENSOR_RAIN,
                        description={"suggested_value": current_data.get(CONF_SENSOR_RAIN)},
                    ): entity_selector,
                    vol.Optional(
                        CONF_SENSOR_RAIN_DAILY,
                        description={"suggested_value": current_data.get(CONF_SENSOR_RAIN_DAILY)},
                    ): entity_selector,
                    vol.Optional(
                        CONF_SENSOR_WIND_SPEED,
                        description={"suggested_value": current_data.get(CONF_SENSOR_WIND_SPEED)},
                    ): entity_selector,
                    vol.Optional(
                        CONF_SENSOR_WIND_DIR,
                        description={"suggested_value": current_data.get(CONF_SENSOR_WIND_DIR)},
                    ): entity_selector,
                    vol.Optional(
                        CONF_SENSOR_WIND_GUST,
                        description={"suggested_value": current_data.get(CONF_SENSOR_WIND_GUST)},
                    ): entity_selector,
                    vol.Optional(
                        CONF_SENSOR_DEW_POINT,
                        description={"suggested_value": current_data.get(CONF_SENSOR_DEW_POINT)},
                    ): entity_selector,
                }
            ),
        )
