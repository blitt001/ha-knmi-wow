"""Constants for the KNMI WOW integration."""
from typing import Final

DOMAIN: Final = "knmi_wow"

# WOW API endpoint (Wunderground protocol, hosted by KMI/IRM at wow.meteo.be)
WOW_API_URL: Final = "https://wow.meteo.be/api/v2/send"

# Default values
DEFAULT_UPDATE_INTERVAL: Final = 1  # minutes (recommended by KNMI)
MIN_UPDATE_INTERVAL: Final = 1  # minutes

# Consecutive attempts with unavailable sensors before the status turns to error.
# Gives source sensors time to report after a restart or a short dropout.
MAX_UNAVAILABLE_ATTEMPTS: Final = 5

# Upload status values (also the options of the status ENUM sensor)
STATUS_PENDING: Final = "pending"
STATUS_OK: Final = "ok"
STATUS_ERROR: Final = "error"

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
CONF_SENSOR_PRESSURE_ABS: Final = "sensor_pressure_abs"
CONF_SENSOR_RAIN: Final = "sensor_rain"
CONF_SENSOR_RAIN_DAILY: Final = "sensor_rain_daily"
CONF_SENSOR_WIND_SPEED: Final = "sensor_wind_speed"
CONF_SENSOR_WIND_DIR: Final = "sensor_wind_dir"
CONF_SENSOR_WIND_GUST: Final = "sensor_wind_gust"
CONF_SENSOR_DEW_POINT: Final = "sensor_dew_point"
CONF_SENSOR_SOLAR_RADIATION: Final = "sensor_solar_radiation"
CONF_SENSOR_UV: Final = "sensor_uv"

# All sensor configuration keys for iteration
SENSOR_CONFIGS: Final = [
    CONF_SENSOR_TEMPERATURE,
    CONF_SENSOR_HUMIDITY,
    CONF_SENSOR_PRESSURE,
    CONF_SENSOR_PRESSURE_ABS,
    CONF_SENSOR_RAIN,
    CONF_SENSOR_RAIN_DAILY,
    CONF_SENSOR_WIND_SPEED,
    CONF_SENSOR_WIND_DIR,
    CONF_SENSOR_WIND_GUST,
    CONF_SENSOR_DEW_POINT,
    CONF_SENSOR_SOLAR_RADIATION,
    CONF_SENSOR_UV,
]

# Mapping from config key to WOW parameter name (wow.meteo.be protocol):
# - baromin is relative (sea-level) pressure and is authoritative; absbaromin is
#   absolute (station) pressure, from which the server derives relative pressure
#   when baromin is not sent.
# - rainin is rain intensity in inches per hour.
SENSOR_TO_WOW_PARAM: Final = {
    CONF_SENSOR_TEMPERATURE: "tempf",
    CONF_SENSOR_HUMIDITY: "humidity",
    CONF_SENSOR_PRESSURE: "baromin",
    CONF_SENSOR_PRESSURE_ABS: "absbaromin",
    CONF_SENSOR_RAIN: "rainin",
    CONF_SENSOR_RAIN_DAILY: "dailyrainin",
    CONF_SENSOR_WIND_SPEED: "windspeedmph",
    CONF_SENSOR_WIND_DIR: "winddir",
    CONF_SENSOR_WIND_GUST: "windgustmph",
    CONF_SENSOR_DEW_POINT: "dewptf",
    CONF_SENSOR_SOLAR_RADIATION: "solarradiation",
    CONF_SENSOR_UV: "UV",
}

# Sensor type categories for unit-aware conversion
SENSOR_TYPE_TEMPERATURE: Final = "temperature"
SENSOR_TYPE_HUMIDITY: Final = "humidity"
SENSOR_TYPE_PRESSURE: Final = "pressure"
SENSOR_TYPE_RAIN: Final = "rain"
SENSOR_TYPE_RAIN_RATE: Final = "rain_rate"
SENSOR_TYPE_SOLAR_RADIATION: Final = "solar_radiation"
SENSOR_TYPE_UV: Final = "uv"

# Approximate conversion from illuminance to solar irradiance for sunlight,
# used when a station only reports lux (e.g. Bresser 7-in-1): W/m² ≈ lx / 126.7
LUX_PER_WATT_PER_M2: Final = 126.7
SENSOR_TYPE_WIND_SPEED: Final = "wind_speed"
SENSOR_TYPE_WIND_DIR: Final = "wind_dir"

# Mapping from config key to sensor type
SENSOR_TYPES: Final = {
    CONF_SENSOR_TEMPERATURE: SENSOR_TYPE_TEMPERATURE,
    CONF_SENSOR_HUMIDITY: SENSOR_TYPE_HUMIDITY,
    CONF_SENSOR_PRESSURE: SENSOR_TYPE_PRESSURE,
    CONF_SENSOR_PRESSURE_ABS: SENSOR_TYPE_PRESSURE,
    CONF_SENSOR_RAIN: SENSOR_TYPE_RAIN_RATE,
    CONF_SENSOR_RAIN_DAILY: SENSOR_TYPE_RAIN,
    CONF_SENSOR_WIND_SPEED: SENSOR_TYPE_WIND_SPEED,
    CONF_SENSOR_WIND_DIR: SENSOR_TYPE_WIND_DIR,
    CONF_SENSOR_WIND_GUST: SENSOR_TYPE_WIND_SPEED,
    CONF_SENSOR_DEW_POINT: SENSOR_TYPE_TEMPERATURE,
    CONF_SENSOR_SOLAR_RADIATION: SENSOR_TYPE_SOLAR_RADIATION,
    CONF_SENSOR_UV: SENSOR_TYPE_UV,
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

    elif sensor_type == SENSOR_TYPE_RAIN_RATE:
        # WOW expects inches per hour
        if unit in ("mm/h", "mm/hr", "mm/u"):
            return mm_to_inches(value)
        elif unit in ("in/h", "in/hr"):
            return value  # Already inches per hour
        else:
            # Assume mm/h if unknown
            return mm_to_inches(value)

    elif sensor_type == SENSOR_TYPE_SOLAR_RADIATION:
        # WOW expects W/m²
        if unit in ("lx", "lux"):
            return value / LUX_PER_WATT_PER_M2  # approximation for sunlight
        return value  # Assume W/m²

    elif sensor_type == SENSOR_TYPE_UV:
        # UV index - no conversion needed
        return value

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
