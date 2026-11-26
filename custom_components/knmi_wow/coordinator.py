"""Data coordinator for KNMI WOW integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT

from .const import (
    CONF_AUTH_KEY,
    CONF_DEBUG_MODE,
    CONF_SITE_ID,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_UNAVAILABLE_ATTEMPTS,
    SENSOR_CONFIGS,
    SENSOR_TO_WOW_PARAM,
    SENSOR_TYPES,
    SOFTWARE_TYPE,
    STATUS_ERROR,
    STATUS_OK,
    STATUS_PENDING,
    WOW_API_URL,
    convert_value_with_unit,
)

_LOGGER = logging.getLogger(__name__)


class KNMIWOWCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage WOW data uploads."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.site_id = entry.data[CONF_SITE_ID]
        self.auth_key = entry.data[CONF_AUTH_KEY]

        update_interval = entry.options.get(
            CONF_UPDATE_INTERVAL,
            entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        )

        self.debug_mode = entry.options.get(
            CONF_DEBUG_MODE,
            entry.data.get(CONF_DEBUG_MODE, False)
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_interval),
        )

        self.last_upload: datetime | None = None
        self.last_error: str | None = None
        self.upload_count: int = 0
        self.last_request_params: dict[str, str] | None = None
        self.status: str = STATUS_PENDING
        self.unavailable_attempts: int = 0

    def _all_sensors_available(self) -> tuple[bool, list[str]]:
        """Check if all configured sensors are available.

        Returns a tuple of (all_available, list_of_unavailable_entities).
        """
        config_data = {**self.entry.data, **self.entry.options}
        unavailable: list[str] = []

        for sensor_key in SENSOR_CONFIGS:
            entity_id = config_data.get(sensor_key)
            if not entity_id:
                continue

            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unknown", "unavailable", None):
                unavailable.append(entity_id)

        return len(unavailable) == 0, unavailable

    async def _async_update_data(self) -> dict[str, Any]:
        """Upload weather data to WOW."""
        try:
            # Don't upload while Home Assistant is still starting: source
            # sensors (e.g. a weather station via MQTT) may not have reported yet.
            if self.hass.state is not CoreState.running:
                _LOGGER.debug("Home Assistant is still starting, postponing KNMI WOW upload")
                return self._get_status_data()

            # Check if all configured sensors are available
            all_available, unavailable = self._all_sensors_available()
            if not all_available:
                self.unavailable_attempts += 1
                message = f"Sensors unavailable: {', '.join(unavailable)}"
                if self.unavailable_attempts >= MAX_UNAVAILABLE_ATTEMPTS:
                    self._set_error(message)
                    _LOGGER.warning(
                        "Skipping KNMI WOW upload - sensors unavailable for %s attempts: %s",
                        self.unavailable_attempts,
                        unavailable,
                    )
                else:
                    # Keep the current status (pending after start-up, ok after
                    # a successful upload) during a short dropout.
                    _LOGGER.info(
                        "Skipping KNMI WOW upload - sensors not available yet "
                        "(attempt %s of %s): %s",
                        self.unavailable_attempts,
                        MAX_UNAVAILABLE_ATTEMPTS,
                        unavailable,
                    )
                return self._get_status_data()

            self.unavailable_attempts = 0

            # Collect sensor values
            weather_data = self._collect_sensor_data()

            if not weather_data:
                _LOGGER.warning("No sensor data available to upload")
                self._set_error("No sensor data available")
                return self._get_status_data()

            # Build the API request
            params = self._build_request_params(weather_data)
            self.last_request_params = params

            # Log debug info if enabled
            if self.debug_mode:
                # Create a safe copy without auth key for logging
                safe_params = {**params, "PASSWORD": "******"}
                _LOGGER.info("KNMI WOW Debug - Sending data: %s", safe_params)

            # Send to WOW
            success, error = await self._send_to_wow(params)

            if success:
                self.last_upload = dt_util.utcnow()
                self.last_error = None
                self.status = STATUS_OK
                self.upload_count += 1
                if self.debug_mode:
                    _LOGGER.info("KNMI WOW Debug - Upload successful")
                else:
                    _LOGGER.info("Successfully uploaded weather data to KNMI WOW")
            else:
                self._set_error(error)
                _LOGGER.error("Failed to upload weather data: %s", error)

            return self._get_status_data()

        except Exception as ex:
            self._set_error(str(ex))
            _LOGGER.exception("Error uploading weather data to KNMI WOW")
            return self._get_status_data()

    def _set_error(self, message: str | None) -> None:
        """Mark the integration as failing with the given message."""
        self.status = STATUS_ERROR
        self.last_error = message

    def _collect_sensor_data(self) -> dict[str, float]:
        """Collect current sensor values from configured entities."""
        weather_data: dict[str, float] = {}

        # Merge data and options, with options taking precedence
        config_data = {**self.entry.data, **self.entry.options}

        for sensor_key in SENSOR_CONFIGS:
            entity_id = config_data.get(sensor_key)
            if not entity_id:
                continue

            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unknown", "unavailable", None):
                _LOGGER.debug("Sensor %s is unavailable", entity_id)
                continue

            try:
                value = float(state.state)
            except (ValueError, TypeError):
                _LOGGER.warning("Could not parse value from %s: %s", entity_id, state.state)
                continue

            # Get the unit of measurement from the sensor
            unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)

            # Get the sensor type for conversion
            sensor_type = SENSOR_TYPES.get(sensor_key)

            # Convert to imperial units based on source unit
            if sensor_type:
                value = convert_value_with_unit(value, sensor_type, unit)
                _LOGGER.debug(
                    "Sensor %s: value=%s, unit=%s, converted=%s",
                    entity_id, state.state, unit, value
                )

            # Get the WOW parameter name
            wow_param = SENSOR_TO_WOW_PARAM.get(sensor_key)
            if wow_param:
                weather_data[wow_param] = round(value, 2)

        return weather_data

    def _build_request_params(self, weather_data: dict[str, float]) -> dict[str, str]:
        """Build the request parameters for the WOW API."""
        # Format date as required: YYYY-mm-DD HH:mm:ss in UTC
        now_utc = dt_util.utcnow()
        date_str = now_utc.strftime("%Y-%m-%d %H:%M:%S")

        params = {
            "ID": self.site_id,
            "PASSWORD": self.auth_key,
            "dateutc": date_str,
            "action": "updateraw",
            "softwaretype": SOFTWARE_TYPE,
        }

        # Add weather data
        for key, value in weather_data.items():
            params[key] = str(value)

        return params

    async def _send_to_wow(self, params: dict[str, str]) -> tuple[bool, str | None]:
        """Send data to WOW API."""
        url = f"{WOW_API_URL}?{urlencode(params)}"

        _LOGGER.debug(
            "Sending request to WOW: %s",
            {k: v for k, v in params.items() if k != "PASSWORD"},
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    response_text = await response.text()

                    if response.status == 200:
                        return True, None
                    elif response.status == 403:
                        return False, "Invalid Station ID or authentication key (403)"
                    elif response.status == 429:
                        _LOGGER.warning(
                            "WOW API rate limit exceeded (429). Consider increasing upload interval."
                        )
                        return False, "Rate limit exceeded (429)"
                    else:
                        error = f"HTTP {response.status}: {response_text}"
                        return False, error

        except aiohttp.ClientError as ex:
            return False, f"Connection error: {ex}"
        except TimeoutError:
            return False, "Request timed out"

    def _get_status_data(self) -> dict[str, Any]:
        """Get status data for the coordinator."""
        next_update = dt_util.utcnow() + (self.update_interval or timedelta(minutes=DEFAULT_UPDATE_INTERVAL))

        data = {
            "status": self.status,
            "last_upload": self.last_upload.isoformat() if self.last_upload else None,
            "last_error": self.last_error,
            "next_upload": next_update.isoformat(),
            "upload_count": self.upload_count,
            "debug_mode": self.debug_mode,
        }

        # Include last sent data when debug mode is enabled
        if self.debug_mode and self.last_request_params:
            # Create safe copy without auth key
            safe_params = {
                k: v for k, v in self.last_request_params.items()
                if k not in ("PASSWORD", "ID")
            }
            data["last_sent_data"] = safe_params

        return data


async def test_connection(hass: HomeAssistant, site_id: str, auth_key: str) -> tuple[bool, str | None]:
    """Test the connection to WOW API with a minimal request."""
    # Build minimal test params (we need at least one weather value)
    now_utc = dt_util.utcnow()
    date_str = now_utc.strftime("%Y-%m-%d %H:%M:%S")

    params = {
        "ID": site_id,
        "PASSWORD": auth_key,
        "dateutc": date_str,
        "action": "updateraw",
        "softwaretype": f"{SOFTWARE_TYPE}-test",
    }

    url = f"{WOW_API_URL}?{urlencode(params)}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    return True, None
                else:
                    response_text = await response.text()
                    return False, f"HTTP {response.status}: {response_text}"

    except aiohttp.ClientError as ex:
        return False, f"Connection error: {ex}"
    except TimeoutError:
        return False, "Request timed out"
