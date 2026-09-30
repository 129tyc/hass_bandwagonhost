"""Privacy-conscious config-entry diagnostics."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import KiwiVMConfigEntry
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: KiwiVMConfigEntry
) -> dict[str, Any]:
    """Return operational status without credentials or VPS/account identifiers."""
    coordinator = entry.runtime_data.coordinator
    snapshot = coordinator.data
    return {
        "poll_interval_minutes": entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        ),
        "last_update_success": coordinator.last_update_success,
        "last_error": coordinator.last_error,
        "last_successful_update": snapshot.updated_at.isoformat() if snapshot else None,
        "available_traffic_fields": (
            {
                "quota": snapshot.quota_bytes is not None,
                "used": snapshot.used_bytes is not None,
                "remaining": snapshot.remaining_bytes is not None,
                "usage_percent": snapshot.usage_percent is not None,
                "next_reset": snapshot.next_reset is not None,
            }
            if snapshot
            else None
        ),
    }
