# KNMI WOW Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/blitt001/ha-knmi-wow)](https://github.com/blitt001/ha-knmi-wow/releases)
[![GitHub License](https://img.shields.io/github/license/blitt001/ha-knmi-wow)](LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.1.0+-blue.svg)](https://www.home-assistant.io/)

Upload your weather station data from [Home Assistant](https://www.home-assistant.io/) to [KNMI WOW](https://wow.knmi.nl) (Weather Observations Website).

## Features

- Seamless integration with Home Assistant's UI
- Automatically uploads weather data every 10 minutes (configurable)
- UI-based configuration - no YAML editing required
- Map any Home Assistant sensor to WOW weather parameters
- Automatic unit conversion (metric to imperial)
- Status sensor with ENUM states (`pending`, `ok`, `error`)
- Sensor availability check before upload
- Debug mode for troubleshooting

## Prerequisites

1. A working [Home Assistant](https://www.home-assistant.io/) installation (version 2025.1.0 or newer)
2. [HACS](https://hacs.xyz/) installed (recommended for easy installation)
3. Register at [wow.knmi.nl](https://wow.knmi.nl) and create a weather station site
4. Note your **Site ID** (UUID format) and **Authentication Key** (6-digit PIN)

## Installation

### HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=blitt001&repository=ha-knmi-wow&category=integration)

Or manually:

1. Open [HACS](https://hacs.xyz/) in Home Assistant
2. Click the three dots menu → **Custom repositories**
3. Add `https://github.com/blitt001/ha-knmi-wow` and select **Integration** as the category
4. Search for "KNMI WOW" and click **Download**
5. Restart Home Assistant

### Manual Installation

1. Download the latest release from [GitHub](https://github.com/blitt001/ha-knmi-wow/releases)
2. Copy the `custom_components/knmi_wow` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=knmi_wow)

Or manually:

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration** and search for "KNMI WOW"
3. Enter your WOW credentials:
   - **Site ID**: Your WOW site identifier (UUID format)
   - **Authentication Key**: Your 6-digit PIN
4. Map your Home Assistant sensors to weather parameters:
   - Outdoor Temperature
   - Humidity
   - Barometric Pressure
   - Rain (since last reading)
   - Daily Rain Total
   - Wind Speed
   - Wind Direction
   - Wind Gust
   - Dew Point
5. Set your preferred upload interval (minimum 10 minutes)
6. Optionally enable debug mode

### Changing Settings

To modify sensor mappings or settings after initial setup:

1. Go to **Settings** → **Devices & Services**
2. Find **KNMI WOW** and click **Configure** (gear icon)
3. Update your settings and submit

## Supported Sensors

The integration automatically converts metric units to the imperial units required by the WOW API:

| Parameter | WOW Field | Supported Input Units |
|-----------|-----------|----------------------|
| Temperature | tempf | °C, °F |
| Humidity | humidity | % |
| Pressure | baromin | hPa, mbar, mmHg, inHg |
| Rain | rainin | mm, in, cm |
| Daily Rain | dailyrainin | mm, in, cm |
| Wind Speed | windspeedmph | m/s, km/h, mph, knots |
| Wind Direction | winddir | Degrees (0-360) |
| Wind Gust | windgustmph | m/s, km/h, mph, knots |
| Dew Point | dewptf | °C, °F |

## Status Sensor

The integration creates a status sensor (`sensor.knmi_wow_status`) with:

- **State**: `pending`, `ok`, or `error` (ENUM device class)
- **Attributes**:
  - `last_upload`: Timestamp of last successful upload
  - `last_error`: Error message (if any)
  - `next_upload`: Scheduled time for next upload
  - `upload_count`: Total successful uploads
  - `site_id`: Your WOW site ID
  - `debug_mode`: Whether debug mode is enabled
  - `last_sent_data`: The data sent in the last upload (only when debug mode is enabled)

### Sensor Availability

The integration checks if all configured sensors are available before uploading. If any sensor is unavailable, the upload is skipped and the status shows `error` with details about which sensors are unavailable.

## Debug Mode

Enable debug mode in the integration options to:
- Log all data being sent to WOW
- Include `last_sent_data` in the status sensor attributes

### Enabling Debug Logging

For detailed logs, add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.knmi_wow: debug
```

After adding this configuration, restart Home Assistant. Debug logs will appear in:
- **Settings** → **System** → **Logs**
- The `home-assistant.log` file in your config directory

### Log Levels

The integration logs at different levels:

| Level | Information |
|-------|-------------|
| DEBUG | Sensor values, unit conversions, API requests |
| INFO | Successful uploads, debug mode data |
| WARNING | Rate limiting (429), unavailable sensors |
| ERROR | Upload failures, connection errors |

## Troubleshooting

### No data appearing on WOW

1. Check the status sensor (`sensor.knmi_wow_status`) for errors
2. Verify your Site ID and Authentication Key are correct
3. Ensure at least one sensor is mapped and has valid data
4. Enable debug mode and check the `last_sent_data` attribute
5. Check Home Assistant logs for detailed error messages

### Rate Limiting (429 errors)

The WOW API has rate limits. If you see "Rate limit exceeded (429)" errors:
- Ensure the upload interval is at least 10 minutes
- Avoid manually reloading the integration repeatedly
- Wait a few minutes before the next automatic upload

### Invalid credentials

The Site ID should be a UUID like `6a571450-df53-e611-9401-0003ff5987fd`. You can find it on your WOW site page in brackets next to the station name.

### Sensors not updating after changing options

After changing sensor mappings in the options:
1. The integration should reload automatically
2. If not, manually reload: **Settings** → **Devices & Services** → **KNMI WOW** → **⋮** → **Reload**

### Rain values seem incorrect

Make sure you're using the correct rain sensor:
- **Rain (since last reading)**: For sensors that show incremental rain between measurements
- **Daily Rain Total**: For sensors that show cumulative rain today (resets at midnight)

If your sensor shows total accumulated rain since installation, create a [Utility Meter](https://www.home-assistant.io/integrations/utility_meter/) helper with daily reset cycle.

## API Reference

This integration uses the WOW automatic upload API:
- Endpoint: `http://wow.metoffice.gov.uk/automaticreading`
- Method: HTTP GET with query parameters
- Required parameters: `siteid`, `siteAuthenticationKey`, `dateutc`, `softwaretype`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

- [Report a bug](https://github.com/blitt001/ha-knmi-wow/issues/new?template=bug_report.md)
- [Request a feature](https://github.com/blitt001/ha-knmi-wow/issues/new?template=feature_request.md)
- [Home Assistant Community Forum](https://community.home-assistant.io/)

## License

MIT License - see [LICENSE](LICENSE) for details.
