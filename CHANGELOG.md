# Changelog

## [0.1.5] - 2025-11-05
### Fixed
- Ensure reloaded entries wait for an initial data refresh and surface configuration errors instead of silently keeping stale data.
- Advertise daily and hourly forecast support so Home Assistant exposes the Meteomatics forecast in the UI.
- Provide native weather properties to restore the current conditions, including temperature, in the weather entity.

## [0.1.4] - 2025-11-05
### Fixed
- Prevent Home Assistant from warning about `async_config_entry_first_refresh` when reloading the integration.

## [0.1.3] - 2025-11-05
### Fixed
- Attach the config entry directly to the data update coordinator so the first-refresh helper remains supported in future Home Assistant releases.
- Bundle the fixes that modernize the options flow and expose richer weather data for the Meteomatics entity.

