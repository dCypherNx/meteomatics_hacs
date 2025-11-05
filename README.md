# Meteomatics Home Assistant Custom Component

This repository provides a Home Assistant custom component that connects to the [Meteomatics](https://www.meteomatics.com/) weather API using the credentials from the basic/free plan.

## Features

- Config flow that requests Meteomatics username, password, latitude, longitude, and update interval.
- Data is fetched through the official Meteomatics REST API using only endpoints available on the free plan.
- Provides a `weather` entity with:
  - Current conditions (temperature, humidity, pressure, wind speed/bearing and symbol-based condition).
  - Hourly forecast for the next 24 hours including precipitation, pressure, humidity and wind details.
  - Daily forecast for the next 7 days including high/low temperatures, precipitation and wind information.
- Supports Home Assistant options flow to adjust the refresh interval (15–180 minutes).

## Installation

1. Copy the `custom_components/meteomatics` directory into your Home Assistant `custom_components` folder.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration** and search for **Meteomatics**.
4. Enter your Meteomatics credentials, desired latitude/longitude and the preferred update interval.

> **Note:** The Meteomatics basic/free plan only allows access to a limited set of parameters and forecasting horizon. The integration uses endpoints compatible with this plan, but you must have an active Meteomatics account.

## Credits

Weather data is provided by [Meteomatics](https://www.meteomatics.com/).
