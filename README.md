# KiwiVM Traffic

Home Assistant custom integration for read-only BandwagonHost KiwiVM traffic monitoring. Each VPS has its own config entry, device, coordinator, and stable sensor IDs.

## Features

- Configure a VPS from **Settings → Devices & services → Add integration**.
- Add multiple VPS instances, including instances with the same hostname.
- View current-cycle quota, used traffic, remaining traffic, use percentage, next reset, and last successful update.
- Change the per-VPS polling interval in the integration options (5–60 minutes; default 15).
- Replace credentials through the integration reconfigure flow; invalid credentials start Home Assistant reauthentication.
- Uses only KiwiVM's read-only `getServiceInfo` API call. No power, snapshot, reinstall, or other management actions are provided.

The integration uses Home Assistant's built-in sensors and dashboards. It does not register static HTTP routes or require a separate service.

## Install

### HACS custom repository

[![Open HACS repository](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?category=integration&owner=129tyc&repository=hass_bandwagonhost)

The GitHub repository must be public for HACS. In HACS, add [129tyc/hass_bandwagonhost](https://github.com/129tyc/hass_bandwagonhost) as a custom repository with category **Integration**, download **KiwiVM Traffic**, then restart Home Assistant.

### Manual install

Copy `custom_components/kiwivm_traffic` into the Home Assistant `custom_components` directory, then restart Home Assistant.

## Configure

From **Settings → Devices & services → Add integration**, select **KiwiVM Traffic** and enter the VPS VEID and API key from its KiwiVM panel. The key field is a password field. A display name is optional; without one, the device is named with its VEID so instances remain distinguishable.

The integration validates the credentials with one `getServiceInfo` request before saving. The key is stored in the Home Assistant config entry and sent only to `https://api.64clouds.com/v1/getServiceInfo` over the Home Assistant HTTPS client. The request uses POST form data so the key is not part of the URL. TLS verification remains enabled.

The default polling interval is 15 minutes. Use the options page to choose 5–60 minutes. A shared coordinator makes one API request per VPS per update cycle for all its sensors. `homeassistant.update_entity` can be used to request an immediate update for that VPS.

## Sensors and units

Traffic amounts use decimal GB (1 GB = 1,000,000,000 bytes), matching the API byte fields. Current-cycle usage is a measurement because it resets with the provider's billing cycle; it is not a lifetime total. The use percentage can exceed 100%. A zero quota has no calculated percentage. Missing or invalid fields remain unavailable rather than becoming zero.

KiwiVM returns `data_counter` and `monthly_data_multiplier`. The implementation applies the API multiplier to the counter before calculating used traffic. Verify non-1 multiplier plans against the KiwiVM panel when validating this integration with a live VPS.

## Dashboard examples

Use the entity picker to replace these example IDs with the IDs created by your instance names.

```yaml
type: entities
title: VPS traffic
entities:
  - entity: sensor.node_a_current_cycle_traffic_used
  - entity: sensor.node_a_current_cycle_traffic_quota
  - entity: sensor.node_a_current_cycle_traffic_remaining
  - entity: sensor.node_a_traffic_usage
  - entity: sensor.node_a_next_traffic_reset
  - entity: sensor.node_b_current_cycle_traffic_used
  - entity: sensor.node_c_current_cycle_traffic_used
```

Example notification when one VPS passes 80% usage:

```yaml
alias: VPS traffic above 80 percent
triggers:
  - trigger: numeric_state
    entity_id: sensor.node_a_traffic_usage
    above: 80
actions:
  - action: persistent_notification.create
    data:
      title: VPS traffic is high
      message: "Node A traffic use is above 80%."
```

## Privacy and diagnostics

The integration does not log credentials or raw API responses. Its config-entry diagnostics include the poll interval, update status, last successful update time, and booleans showing which traffic fields are available. They omit the API key, VEID, hostname, IP addresses, email, and raw response data.

The KiwiVM API key can grant broader VPS control than this integration uses. The integration's own API client only implements the read-only service-info request; it cannot start, stop, restart, or otherwise manage a VPS.

## Validation status

A live `getServiceInfo` response confirmed authentication and the expected traffic fields for a 1× multiplier sample. The non-1× multiplier calculation still needs a panel comparison. Local checks cover Ruff, Python compilation, and traffic parsing; the full Home Assistant tests, hassfest, HACS validation, and install/upgrade flow have not run yet. GitHub Actions runs the repository checks after the code is pushed.

## Development and release

Run the local checks with `ruff check .` and `pytest`. GitHub Actions also runs those checks, Home Assistant hassfest, and HACS repository validation. A pushed `v*` tag creates a GitHub Release only when the tag matches the integration version in `manifest.json`.

The minimum Home Assistant version is 2026.3.0. The integration ships its own brand icon using the custom-integration brand support added in that release.

For HACS publication, use a public GitHub repository, enable Issues, and set repository metadata. Suggested description: `Read-only BandwagonHost KiwiVM traffic sensors for Home Assistant.` Suggested topics: `home-assistant`, `hacs`, `kiwivm`, `bandwagonhost`, `custom-integration`.

## License

MIT. BandwagonHost and KiwiVM are trademarks of their respective owners; this community integration is not affiliated with or endorsed by them.
