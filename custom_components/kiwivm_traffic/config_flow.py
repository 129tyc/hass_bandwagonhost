"""Config and options flows for KiwiVM Traffic."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import aiohttp_client, selector

from .api import (
    KiwiVMAuthenticationError,
    KiwiVMConnectionError,
    KiwiVMRateLimitError,
    KiwiVMResponseError,
    async_get_service_info,
)
from .const import (
    CONF_API_KEY,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_VEID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_VEID_PATTERN = re.compile(r"^[0-9]{1,20}$")


async def _credential_error(
    hass: HomeAssistant, veid: str, api_key: str
) -> str | None:
    """Return the user-facing error for a failed credential check."""
    try:
        await async_get_service_info(
            aiohttp_client.async_get_clientsession(hass), veid, api_key
        )
    except KiwiVMAuthenticationError:
        return "invalid_auth"
    except KiwiVMRateLimitError:
        return "rate_limited"
    except KiwiVMResponseError:
        return "invalid_response"
    except KiwiVMConnectionError:
        return "cannot_connect"
    return None


def _credential_schema() -> vol.Schema:
    """Return the add-entry credential form."""
    return vol.Schema(
        {
            vol.Required(CONF_VEID): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Required(CONF_API_KEY): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Optional(CONF_NAME): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
        }
    )


class KiwiVMConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle adding a single VPS, reconfiguration, and reauthentication."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Add a VPS using its VEID and KiwiVM API key."""
        errors: dict[str, str] = {}
        if user_input is not None:
            veid = user_input[CONF_VEID].strip()
            api_key = user_input[CONF_API_KEY].strip()
            if not _VEID_PATTERN.fullmatch(veid):
                errors["base"] = "invalid_veid"
            else:
                await self.async_set_unique_id(veid)
                self._abort_if_unique_id_configured()
                error = await _credential_error(self.hass, veid, api_key)
                if error:
                    errors["base"] = error
                else:
                    title = user_input.get(CONF_NAME, "").strip() or f"VPS {veid}"
                    return self.async_create_entry(
                        title=title,
                        data={CONF_VEID: veid, CONF_API_KEY: api_key},
                    )

        return self.async_show_form(
            step_id="user", data_schema=_credential_schema(), errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Replace credentials without changing the VEID or entity identities."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            error = await _credential_error(self.hass, entry.data[CONF_VEID], api_key)
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_API_KEY: api_key}
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Start reauthentication after the API rejects stored credentials."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Validate and save a replacement API key."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            error = await _credential_error(self.hass, entry.data[CONF_VEID], api_key)
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_API_KEY: api_key}
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    )
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> KiwiVMOptionsFlow:
        """Return polling options flow."""
        return KiwiVMOptionsFlow()


class KiwiVMOptionsFlow(config_entries.OptionsFlow):
    """Manage one VPS polling interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Set the interval between read-only service-info requests."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            step=1,
                            mode=selector.NumberSelectorMode.SLIDER,
                            unit_of_measurement="min",
                        )
                    )
                }
            ),
        )
