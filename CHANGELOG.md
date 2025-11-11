# Changelog

## [0.2.2] - 2025-11-19
### Changed
- Release version 0.2.2.

## [0.2.1] - 2025-11-12
### Changed
- Enforce the basic-plan cadence with fixed 20-minute hourly refreshes and scheduled daily retrievals.
- Update the hourly and daily parameter sets to match the free-tier requirements, limit the daily horizon to nine days, and infer the daily symbol from hourly data.
- Remove optional parameter selection and variable interval configuration from the setup and options flows.

## [0.1.9] - 2025-11-07
### Added
- Allow Meteomatics basic-plan users to pick additional optional parameters during setup while always requesting the required
  baseline datasets.

### Changed
- Persist the optional parameter selection and make coordinator requests honor the chosen datasets for each account tier.

## [0.1.8] - 2025-11-06
### Added
- Allow reconfiguring Meteomatics credentials directly from the options flow so usernames and passwords can be updated without removing the integration.

### Fixed
- Pause updates for one hour after receiving HTTP 429 responses from the Meteomatics API to honor rate limits.

## [0.1.7] - 2025-11-05
### Changed
- Internal build not released publicly.

## [0.1.6] - 2025-11-05
### Fixed
- Ignore option updates that arrive before the Meteomatics entry finishes setting up so Home Assistant no longer raises `ConfigEntryNotReady` when the update interval is adjusted.
- Update the coordinator interval only when it actually changes and remain compatible with older Home Assistant cores.

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

