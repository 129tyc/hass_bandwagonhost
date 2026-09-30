"""Tests for the user-facing config flow."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kiwivm_traffic.const import (
    CONF_API_KEY,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_VEID,
    DOMAIN,
)

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


@pytest.mark.asyncio
async def test_invalid_veid_does_not_call_api(hass) -> None:
    """A malformed VEID is rejected locally before a network request."""
    with patch(
        "custom_components.kiwivm_traffic.config_flow.async_get_service_info",
        new=AsyncMock(),
    ) as get_service_info:
        flow = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"],
            user_input={CONF_VEID: "not-a-veid", CONF_API_KEY: "test-key"},
        )

    assert result["type"] == "form"
    assert result["errors"] == {"base": "invalid_veid"}
    get_service_info.assert_not_called()


@pytest.mark.asyncio
async def test_duplicate_veid_aborts_without_api_request(hass) -> None:
    """Each VEID can only be configured once."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_VEID: "12345", CONF_API_KEY: "test-key"},
        unique_id="12345",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.kiwivm_traffic.config_flow.async_get_service_info",
        new=AsyncMock(),
    ) as get_service_info:
        flow = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"],
            user_input={CONF_VEID: "12345", CONF_API_KEY: "test-key"},
        )

    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"
    get_service_info.assert_not_called()


@pytest.mark.asyncio
async def test_different_veids_create_distinct_entries_with_same_hostname(hass) -> None:
    """Hostname does not participate in config identity."""
    with patch(
        "custom_components.kiwivm_traffic.config_flow.async_get_service_info",
        new=AsyncMock(return_value={"error": 0, "hostname": "same-host"}),
    ) as get_service_info:
        for veid, name in (("12345", "Node A"), ("67890", "Node B")):
            flow = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_USER}
            )
            result = await hass.config_entries.flow.async_configure(
                flow["flow_id"],
                user_input={CONF_VEID: veid, CONF_API_KEY: "test-key", CONF_NAME: name},
            )
            assert result["type"] == "create_entry"
            assert result["title"] == name

    entries = hass.config_entries.async_entries(DOMAIN)
    assert {entry.unique_id for entry in entries} == {"12345", "67890"}
    assert get_service_info.await_count == 2


@pytest.mark.asyncio
async def test_reconfigure_updates_key_without_changing_entry_identity(hass) -> None:
    """Credential updates preserve the VEID and update the existing entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_VEID: "12345", CONF_API_KEY: "old-key"},
        unique_id="12345",
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.kiwivm_traffic.config_flow.async_get_service_info",
            new=AsyncMock(return_value={"error": 0}),
        ),
        patch.object(
            hass.config_entries,
            "async_reload",
            new=AsyncMock(return_value=True),
        ),
    ):
        flow = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
        )
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"], user_input={CONF_API_KEY: "new-key"}
        )

    assert result["type"] == "abort"
    assert entry.data == {CONF_VEID: "12345", CONF_API_KEY: "new-key"}
    assert entry.unique_id == "12345"


@pytest.mark.asyncio
async def test_options_flow_accepts_interval_boundaries(hass) -> None:
    """The UI accepts configured minimum and maximum polling intervals."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_VEID: "12345", CONF_API_KEY: "test-key"},
        unique_id="12345",
    )
    entry.add_to_hass(hass)

    for interval in (5, 60):
        flow = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            flow["flow_id"], user_input={CONF_SCAN_INTERVAL: interval}
        )
        assert result["type"] == "create_entry"
        assert entry.options[CONF_SCAN_INTERVAL] == interval
