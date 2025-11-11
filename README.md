# Meteomatics Home Assistant Custom Component

This repository provides a Home Assistant custom component that connects to the [Meteomatics](https://www.meteomatics.com/) weather API using the credentials from the basic/free plan.

## Features

- Simple configuration that only requires your Meteomatics username and password. The integration automatically uses the Home Assistant latitude and longitude.
- Data is fetched through the official Meteomatics REST API using only endpoints available on the basic/free plan.
- The hourly request includes the most verbose data set allowed by the plan, while the complementary daily request focuses on extremes and solar information, inferring other attributes when possible.
- Provides a `weather` entity with:
  - Current conditions (temperature, humidity, pressure, wind speed/bearing and symbol-based condition).
  - Hourly forecast for the next 24 hours including precipitation, pressure, humidity and wind details.
  - Daily forecast for the next 7 days including high/low temperatures, precipitation, inferred precipitation totals and wind information.
- Supports the Home Assistant options flow to update stored credentials at any time.

## Installation

### Via HACS (recommended)

1. Ensure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance.
2. In HACS, go to **Integrations → … (three dots) → Custom repositories** and add `https://github.com/dCypherNx/meteomatics_hacs` as a **Integration** repository.
3. After adding the repository, search for **Meteomatics Weather** within HACS and install it.
4. Restart Home Assistant after the installation completes.

### Manual installation

1. Copy the `custom_components/meteomatics` directory into your Home Assistant `custom_components` folder.
2. Restart Home Assistant.

### Configuration

1. Go to **Settings → Devices & Services → Add Integration** and search for **Meteomatics**.
2. Enter your Meteomatics username and password. The integration automatically uses the location configured in Home Assistant.

> **Note:** The Meteomatics basic/free plan restricts each request to 10 parameters. The integration distributes 15 available parameters across hourly and daily queries to stay within this limit while delivering rich forecasts.

## Credits

Weather data is provided by [Meteomatics](https://www.meteomatics.com/).
