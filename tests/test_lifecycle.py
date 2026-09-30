"""Tests for coordinator refresh and config-entry unload behavior."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState, SOURCE_REAUTH
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kiwivm_traffic.api import (
    KiwiVMAuthenticationError,
    KiwiVMConnectionError,
)
from custom_components.kiwivm_traffic.const import (
    CONF_API_KEY,
    CONF_VEID,
    DOMAIN,
)

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


@pytest.mark.asyncio
async def test_one_coordinator_updates_all_sensors_and_unloads(hass) -> None:
    """One VPS shares data, marks it stale after errors, and unloads cleanly."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_VEID: "12345", CONF_API_KEY: "test-key"},
        unique_id="12345",
        title="Node A",
    )
    entry.add_to_hass(hass)
    payload = {
        "error": 0,
        "plan_monthly_data": 1_000_000_000,
        "data_counter": 250_000_000,
        "monthly_data_multiplier": 1,
        "data_next_reset": 1_800_000_000,
    }

    with patch(
        "custom_components.kiwivm_traffic.coordinator.async_get_service_info",
        new=AsyncMock(return_value=payload),
    ) as get_service_info:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert get_service_info.await_count == 1

        from homeassistant.helpers import entity_registry as er

        registry = er.async_get(hass)
        entities = er.async_entries_for_config_entry(registry, entry.entry_id)
        assert len(entities) == 6
        assert all(hass.states.get(entity.entity_id) is not None for entity in entities)
        last_success_id = next(
            entity.entity_id
            for entity in entities
            if entity.unique_id.endswith("_updated_at")
        )
        last_success_value = hass.states.get(last_success_id).state

        get_service_info.side_effect = KiwiVMConnectionError("test failure")
        await entry.runtime_data.coordinator.async_refresh()
        await hass.async_block_till_done()
        traffic_states = [
            hass.states.get(entity.entity_id)
            for entity in entities
            if entity.entity_id != last_success_id
        ]
        assert all(state.state == "unavailable" for state in traffic_states)
        last_success_state = hass.states.get(last_success_id)
        assert last_success_state.state == last_success_value

        get_service_info.side_effect = KiwiVMAuthenticationError("test auth failure")
        await entry.runtime_data.coordinator.async_refresh()
        await hass.async_block_till_done()
        reauth_flows = [
            flow
            for flow in hass.config_entries.flow.async_progress()
            if flow["handler"] == DOMAIN
            and flow["context"].get("source") == SOURCE_REAUTH
        ]
        assert len(reauth_flows) == 1

        get_service_info.side_effect = None
        get_service_info.return_value = payload
        with (
            patch.object(
                hass.config_entries,
                "async_reload",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "custom_components.kiwivm_traffic.config_flow.async_get_service_info",
                new=AsyncMock(return_value=payload),
            ) as reauth_check,
        ):
            result = await hass.config_entries.flow.async_configure(
                reauth_flows[0]["flow_id"],
                user_input={CONF_API_KEY: "replacement-key"},
            )
            await hass.async_block_till_done()
        assert result["type"] == "abort"
        assert entry.data[CONF_API_KEY] == "replacement-key"
        reauth_check.assert_awaited_once()

        coordinator = entry.runtime_data.coordinator
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.NOT_LOADED
        assert coordinator._listeners == {}
        assert coordinator._unsub_refresh is None
