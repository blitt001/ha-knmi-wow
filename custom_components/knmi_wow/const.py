"""Constants for the KNMI WOW integration."""
from typing import Final

DOMAIN: Final = "knmi_wow"

# WOW API endpoint
WOW_API_URL: Final = "http://wow.metoffice.gov.uk/automaticreading"

# Default values
DEFAULT_UPDATE_INTERVAL: Final = 10  # minutes
MIN_UPDATE_INTERVAL: Final = 10  # minutes (WOW API rate limit)

# Software type identifier
SOFTWARE_TYPE: Final = "HomeAssistant-KNMI-WOW"

# Configuration keys
CONF_SITE_ID: Final = "site_id"
CONF_AUTH_KEY: Final = "auth_key"
CONF_UPDATE_INTERVAL: Final = "update_interval"
CONF_DEBUG_MODE: Final = "debug_mode"

# Sensor mapping configuration keys
CONF_SENSOR_TEMPERATURE: Final = "sensor_temperature"
CONF_SENSOR_HUMIDITY: Final = "sensor_humidity"
CONF_SENSOR_PRESSURE: Final = "sensor_pressure"
CONF_SENSOR_RAIN: Final = "sensor_rain"
CONF_SENSOR_RAIN_DAILY: Final = "sensor_rain_daily"
CONF_SENSOR_WIND_SPEED: Final = "sensor_wind_speed"
CONF_SENSOR_WIND_DIR: Final = "sensor_wind_dir"
CONF_SENSOR_WIND_GUST: Final = "sensor_wind_gust"
CONF_SENSOR_DEW_POINT: Final = "sensor_dew_point"

# All sensor configuration keys for iteration
SENSOR_CONFIGS: Final = [
    CONF_SENSOR_TEMPERATURE,
    CONF_SENSOR_HUMIDITY,
    CONF_SENSOR_PRESSURE,
    CONF_SENSOR_RAIN,
    CONF_SENSOR_RAIN_DAILY,
    CONF_SENSOR_WIND_SPEED,
    CONF_SENSOR_WIND_DIR,
    CONF_SENSOR_WIND_GUST,
    CONF_SENSOR_DEW_POINT,
]

# Mapping from config key to WOW parameter name
SENSOR_TO_WOW_PARAM: Final = {
    CONF_SENSOR_TEMPERATURE: "tempf",
    CONF_SENSOR_HUMIDITY: "humidity",
    CONF_SENSOR_PRESSURE: "baromin",
    CONF_SENSOR_RAIN: "rainin",
    CONF_SENSOR_RAIN_DAILY: "dailyrainin",
    CONF_SENSOR_WIND_SPEED: "windspeedmph",
    CONF_SENSOR_WIND_DIR: "winddir",
    CONF_SENSOR_WIND_GUST: "windgustmph",
    CONF_SENSOR_DEW_POINT: "dewptf",
}

# Sensor type categories for unit-aware conversion
SENSOR_TYPE_TEMPERATURE: Final = "temperature"
SENSOR_TYPE_HUMIDITY: Final = "humidity"
SENSOR_TYPE_PRESSURE: Final = "pressure"
SENSOR_TYPE_RAIN: Final = "rain"
SENSOR_TYPE_WIND_SPEED: Final = "wind_speed"
SENSOR_TYPE_WIND_DIR: Final = "wind_dir"

# Mapping from config key to sensor type
SENSOR_TYPES: Final = {
    CONF_SENSOR_TEMPERATURE: SENSOR_TYPE_TEMPERATURE,
    CONF_SENSOR_HUMIDITY: SENSOR_TYPE_HUMIDITY,
    CONF_SENSOR_PRESSURE: SENSOR_TYPE_PRESSURE,
    CONF_SENSOR_RAIN: SENSOR_TYPE_RAIN,
    CONF_SENSOR_RAIN_DAILY: SENSOR_TYPE_RAIN,
    CONF_SENSOR_WIND_SPEED: SENSOR_TYPE_WIND_SPEED,
    CONF_SENSOR_WIND_DIR: SENSOR_TYPE_WIND_DIR,
    CONF_SENSOR_WIND_GUST: SENSOR_TYPE_WIND_SPEED,
    CONF_SENSOR_DEW_POINT: SENSOR_TYPE_TEMPERATURE,
}


def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return (celsius * 9 / 5) + 32


def hpa_to_inhg(hpa: float) -> float:
    """Convert hectopascals to inches of mercury."""
    return hpa * 0.02953


def mbar_to_inhg(mbar: float) -> float:
    """Convert millibars to inches of mercury (same as hPa)."""
    return mbar * 0.02953


def mm_to_inches(mm: float) -> float:
    """Convert millimeters to inches."""
    return mm * 0.03937


def kmh_to_mph(kmh: float) -> float:
    """Convert kilometers per hour to miles per hour."""
    return kmh * 0.621371


def ms_to_mph(ms: float) -> float:
    """Convert meters per second to miles per hour."""
    return ms * 2.23694


def knots_to_mph(knots: float) -> float:
    """Convert knots to miles per hour."""
    return knots * 1.15078


def convert_value_with_unit(
    value: float, sensor_type: str, unit: str | None
) -> float:
    """Convert a value based on the sensor type and source unit.

    Args:
        value: The numeric value to convert
        sensor_type: The type of sensor (temperature, rain, etc.)
        unit: The unit of measurement from the HA sensor (e.g., "°C", "mm", "m/s")

    Returns:
        The value converted to the WOW expected unit (imperial)
    """
    if unit is None:
        unit = ""
    unit = unit.lower().strip()

    if sensor_type == SENSOR_TYPE_TEMPERATURE:
        # WOW expects Fahrenheit
        if unit in ("°c", "c", "celsius"):
            return celsius_to_fahrenheit(value)
        elif unit in ("°f", "f", "fahrenheit"):
            return value  # Already Fahrenheit
        else:
            # Assume Celsius if unknown
            return celsius_to_fahrenheit(value)

    elif sensor_type == SENSOR_TYPE_HUMIDITY:
        # Humidity is always % - no conversion needed
        return value

    elif sensor_type == SENSOR_TYPE_PRESSURE:
        # WOW expects inches of mercury
        if unit in ("hpa", "mbar", "mb"):
            return hpa_to_inhg(value)
        elif unit in ("inhg", "in"):
            return value  # Already inHg
        elif unit in ("mmhg",):
            return value * 0.03937  # mmHg to inHg
        elif unit in ("pa",):
            return (value / 100) * 0.02953  # Pa to hPa to inHg
        else:
            # Assume hPa if unknown
            return hpa_to_inhg(value)

    elif sensor_type == SENSOR_TYPE_RAIN:
        # WOW expects inches
        if unit in ("mm", "millimeter", "millimeters"):
            return mm_to_inches(value)
        elif unit in ("in", "inch", "inches"):
            return value  # Already inches
        elif unit in ("cm",):
            return mm_to_inches(value * 10)  # cm to mm to inches
        else:
            # Assume mm if unknown
            return mm_to_inches(value)

    elif sensor_type == SENSOR_TYPE_WIND_SPEED:
        # WOW expects mph
        if unit in ("m/s", "ms"):
            return ms_to_mph(value)
        elif unit in ("km/h", "kmh", "kph"):
            return kmh_to_mph(value)
        elif unit in ("mph",):
            return value  # Already mph
        elif unit in ("kn", "kt", "knots"):
            return knots_to_mph(value)
        else:
            # Assume m/s if unknown
            return ms_to_mph(value)

    elif sensor_type == SENSOR_TYPE_WIND_DIR:
        # Wind direction is always degrees - no conversion needed
        return value

    return value
