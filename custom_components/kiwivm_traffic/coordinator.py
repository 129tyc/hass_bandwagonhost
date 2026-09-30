"""Traffic data coordinator."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    KiwiVMAuthenticationError,
    KiwiVMConnectionError,
    KiwiVMRateLimitError,
    KiwiVMResponseError,
    async_get_service_info,
)
from .const import (
    CONF_API_KEY,
    CONF_SCAN_INTERVAL,
    CONF_VEID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .traffic import TrafficSnapshot, parse_service_info

_LOGGER = logging.getLogger(__name__)


@dataclass
class KiwiVMRuntimeData:
    """Runtime objects for one configured VPS."""

    coordinator: KiwiVMTrafficCoordinator


class KiwiVMTrafficCoordinator(DataUpdateCoordinator[TrafficSnapshot]):
    """Fetch one service-info response for all entities of one VPS."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        session: aiohttp.ClientSession,
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                minutes=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
            config_entry=entry,
        )
        self._entry = entry
        self._session = session
        self.last_error: str | None = None

    async def _async_update_data(self) -> TrafficSnapshot:
        """Fetch and normalize the API response."""
        try:
            payload = await async_get_service_info(
                self._session,
                self._entry.data[CONF_VEID],
                self._entry.data[CONF_API_KEY],
            )
        except KiwiVMAuthenticationError as err:
            self.last_error = "authentication"
            raise ConfigEntryAuthFailed("KiwiVM credentials were rejected") from err
        except KiwiVMRateLimitError as err:
            self.last_error = "rate_limited"
            raise UpdateFailed(
                "KiwiVM API rate limited the request", retry_after=err.retry_after
            ) from err
        except KiwiVMConnectionError as err:
            self.last_error = "connection"
            raise UpdateFailed("Unable to connect to the KiwiVM API") from err
        except KiwiVMResponseError as err:
            self.last_error = "response"
            raise UpdateFailed("KiwiVM returned an API error response") from err

        self.last_error = None
        return parse_service_info(payload)
