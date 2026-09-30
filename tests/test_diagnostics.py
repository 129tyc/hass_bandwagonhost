"""Tests that diagnostics contain no credentials or VPS identifiers."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kiwivm_traffic.const import (
    CONF_API_KEY,
    CONF_VEID,
    DOMAIN,
)
from custom_components.kiwivm_traffic.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.kiwivm_traffic.traffic import TrafficSnapshot


@pytest.mark.asyncio
async def test_diagnostics_omit_credentials_and_veid(hass) -> None:
    """Operational diagnostics expose field availability but no raw identity."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_VEID: "123456789", CONF_API_KEY: "sensitive-test-key"},
        unique_id="123456789",
        title="Private VPS name",
    )
    snapshot = TrafficSnapshot(
        quota_bytes=Decimal(100),
        used_bytes=Decimal(25),
        remaining_bytes=Decimal(75),
        usage_percent=Decimal(25),
        next_reset=None,
        updated_at=datetime(2026, 9, 30, tzinfo=UTC),
    )
    entry.runtime_data = SimpleNamespace(
        coordinator=SimpleNamespace(
            data=snapshot,
            last_update_success=True,
            last_error=None,
        )
    )

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    serialized = repr(diagnostics)

    assert diagnostics["available_traffic_fields"]["used"] is True
    assert "sensitive-test-key" not in serialized
    assert "123456789" not in serialized
    assert "Private VPS name" not in serialized
