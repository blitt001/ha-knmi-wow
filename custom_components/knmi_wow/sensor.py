"""Sensor platform for KNMI WOW integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_SITE_ID, DOMAIN
from .coordinator import KNMIWOWCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KNMI WOW sensor from a config entry."""
    coordinator: KNMIWOWCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([KNMIWOWStatusSensor(coordinator, entry)])


class KNMIWOWStatusSensor(CoordinatorEntity[KNMIWOWCoordinator], SensorEntity):
    """Sensor showing the status of KNMI WOW uploads."""

    _attr_has_entity_name = True
    _attr_name = "Status"
    _attr_icon = "mdi:cloud-upload"

    def __init__(
        self,
        coordinator: KNMIWOWCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        site_id = entry.data[CONF_SITE_ID]

        self._attr_unique_id = f"{site_id}_status"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, site_id)},
            "name": "KNMI WOW",
            "manufacturer": "KNMI",
            "model": "Weather Observations Website",
            "configuration_url": "https://wow.knmi.nl",
        }

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get("status", "unknown")
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}

        attrs = {
            "last_upload": self.coordinator.data.get("last_upload"),
            "last_error": self.coordinator.data.get("last_error"),
            "next_upload": self.coordinator.data.get("next_upload"),
            "upload_count": self.coordinator.data.get("upload_count", 0),
            "site_id": self._entry.data[CONF_SITE_ID],
            "debug_mode": self.coordinator.data.get("debug_mode", False),
        }

        # Include last sent data when debug mode is enabled
        last_sent = self.coordinator.data.get("last_sent_data")
        if last_sent:
            attrs["last_sent_data"] = last_sent

        return attrs
