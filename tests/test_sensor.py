"""Tests for traffic sensor identity and availability."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kiwivm_traffic.const import DOMAIN
from custom_components.kiwivm_traffic.sensor import _SENSORS, KiwiVMTrafficSensor
from custom_components.kiwivm_traffic.traffic import TrafficSnapshot


def _snapshot(
    *, quota: Decimal | None = Decimal(100), used: Decimal | None = Decimal(25)
):
    return TrafficSnapshot(
        quota_bytes=quota,
        used_bytes=used,
        remaining_bytes=Decimal(75) if quota is not None and used is not None else None,
        usage_percent=Decimal(25) if quota else None,
        next_reset=datetime(2027, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 9, 30, tzinfo=UTC),
    )


def test_sensor_names_and_ids_are_stable_per_veid() -> None:
    """Translated entity names are combined with the device name."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id="12345", title="Node A")
    coordinator = SimpleNamespace(data=_snapshot(), last_update_success=True)
    sensor = KiwiVMTrafficSensor(coordinator, entry, _SENSORS[1])

    assert sensor._attr_has_entity_name is True
    assert sensor.entity_description.translation_key == "used"
    assert sensor.unique_id == "12345_used_bytes"
    assert sensor.native_value == 2.5e-08
    assert sensor.available


def test_last_success_timestamp_survives_failed_update() -> None:
    """Traffic goes unavailable on request failure while the last success remains."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id="12345", title="Node A")
    coordinator = SimpleNamespace(data=_snapshot(), last_update_success=False)
    used = KiwiVMTrafficSensor(coordinator, entry, _SENSORS[1])
    last_success = KiwiVMTrafficSensor(coordinator, entry, _SENSORS[5])

    assert not used.available
    assert last_success.available
    assert last_success.native_value == datetime(2026, 9, 30, tzinfo=UTC)


def test_missing_source_field_is_unavailable() -> None:
    """A missing quota does not appear as a zero-value sensor."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id="12345", title="Node A")
    coordinator = SimpleNamespace(
        data=_snapshot(quota=None), last_update_success=True
    )
    quota = KiwiVMTrafficSensor(coordinator, entry, _SENSORS[0])

    assert not quota.available
    assert quota.native_value is None


@pytest.mark.asyncio
async def test_manual_update_requests_shared_coordinator_refresh() -> None:
    """The native update-entity action delegates to the coordinator's debounce."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id="12345", title="Node A")
    coordinator = SimpleNamespace(
        data=_snapshot(),
        last_update_success=True,
        async_request_refresh=AsyncMock(),
    )
    sensor = KiwiVMTrafficSensor(coordinator, entry, _SENSORS[1])

    await sensor.async_update()

    coordinator.async_request_refresh.assert_awaited_once()
