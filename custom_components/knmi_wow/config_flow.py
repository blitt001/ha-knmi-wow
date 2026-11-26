"""Config flow for KNMI WOW integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .const import (
    CONF_AUTH_KEY,
    CONF_DEBUG_MODE,
    CONF_SENSOR_DEW_POINT,
    CONF_SENSOR_HUMIDITY,
    CONF_SENSOR_PRESSURE,
    CONF_SENSOR_PRESSURE_ABS,
    CONF_SENSOR_RAIN,
    CONF_SENSOR_RAIN_DAILY,
    CONF_SENSOR_SOLAR_RADIATION,
    CONF_SENSOR_TEMPERATURE,
    CONF_SENSOR_UV,
    CONF_SENSOR_WIND_DIR,
    CONF_SENSOR_WIND_GUST,
    CONF_SENSOR_WIND_SPEED,
    CONF_SITE_ID,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MIN_UPDATE_INTERVAL,
    SENSOR_CONFIGS,
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
                    vol.Optional(CONF_SENSOR_PRESSURE_ABS): entity_selector,
                    vol.Optional(CONF_SENSOR_RAIN): entity_selector,
                    vol.Optional(CONF_SENSOR_RAIN_DAILY): entity_selector,
                    vol.Optional(CONF_SENSOR_WIND_SPEED): entity_selector,
                    vol.Optional(CONF_SENSOR_WIND_DIR): entity_selector,
                    vol.Optional(CONF_SENSOR_WIND_GUST): entity_selector,
                    vol.Optional(CONF_SENSOR_DEW_POINT): entity_selector,
                    vol.Optional(CONF_SENSOR_SOLAR_RADIATION): entity_selector,
                    vol.Optional(CONF_SENSOR_UV): entity_selector,
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

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user change the Station ID and authentication key."""
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            old_site_id = entry.data[CONF_SITE_ID]
            new_site_id = user_input[CONF_SITE_ID].strip()
            new_auth_key = user_input[CONF_AUTH_KEY].strip()

            if new_site_id != old_site_id:
                # Make sure no other entry already uses this station ID
                await self.async_set_unique_id(new_site_id)
                self._abort_if_unique_id_configured()
                self._migrate_registry_ids(entry, old_site_id, new_site_id)

            # The entry's update listener (see __init__.py) reloads the
            # integration once; async_update_reload_and_abort would reload twice.
            self.hass.config_entries.async_update_entry(
                entry,
                unique_id=new_site_id,
                title=f"KNMI WOW ({new_site_id[:8]}...)",
                data={
                    **entry.data,
                    CONF_SITE_ID: new_site_id,
                    CONF_AUTH_KEY: new_auth_key,
                },
            )
            return self.async_abort(reason="reconfigure_successful")

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SITE_ID, default=entry.data.get(CONF_SITE_ID, "")
                    ): str,
                    vol.Required(
                        CONF_AUTH_KEY, default=entry.data.get(CONF_AUTH_KEY, "")
                    ): str,
                }
            ),
        )

    def _migrate_registry_ids(
        self,
        entry: config_entries.ConfigEntry,
        old_site_id: str,
        new_site_id: str,
    ) -> None:
        """Move the status sensor and device to the new site ID.

        The sensor unique_id and device identifier are derived from the site ID,
        so without this a changed ID would create a new entity and device and
        leave the old ones orphaned.
        """
        ent_reg = er.async_get(self.hass)
        for entity in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
            if entity.unique_id.startswith(f"{old_site_id}_"):
                ent_reg.async_update_entity(
                    entity.entity_id,
                    new_unique_id=new_site_id + entity.unique_id[len(old_site_id):],
                )

        dev_reg = dr.async_get(self.hass)
        device = dev_reg.async_get_device(identifiers={(DOMAIN, old_site_id)})
        if device is not None:
            dev_reg.async_update_device(
                device.id, new_identifiers={(DOMAIN, new_site_id)}
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
            # A cleared selector is left out of user_input. Store it explicitly
            # as None, otherwise the value from the initial setup (entry.data)
            # would still be used when data and options are merged.
            for sensor_key in SENSOR_CONFIGS:
                user_input.setdefault(sensor_key, None)
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
                        CONF_SENSOR_PRESSURE_ABS,
                        description={"suggested_value": current_data.get(CONF_SENSOR_PRESSURE_ABS)},
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
                    vol.Optional(
                        CONF_SENSOR_SOLAR_RADIATION,
                        description={"suggested_value": current_data.get(CONF_SENSOR_SOLAR_RADIATION)},
                    ): entity_selector,
                    vol.Optional(
                        CONF_SENSOR_UV,
                        description={"suggested_value": current_data.get(CONF_SENSOR_UV)},
                    ): entity_selector,
                }
            ),
        )
