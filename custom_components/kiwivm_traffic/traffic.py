"""Parse KiwiVM traffic values independently of Home Assistant and HTTP."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass(frozen=True)
class TrafficSnapshot:
    """Normalized traffic fields; missing source fields remain unavailable."""

    quota_bytes: Decimal | None
    used_bytes: Decimal | None
    remaining_bytes: Decimal | None
    usage_percent: Decimal | None
    next_reset: datetime | None
    updated_at: datetime


def _decimal(value: Any, *, positive: bool = False) -> Decimal | None:
    """Parse a finite, non-negative numeric API field."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite() or number < 0 or (positive and number == 0):
        return None
    return number


def _timestamp(value: Any) -> datetime | None:
    """Convert a numeric Unix timestamp into an aware UTC datetime."""
    timestamp = _decimal(value, positive=True)
    if timestamp is None:
        return None
    try:
        return datetime.fromtimestamp(float(timestamp), tz=UTC)
    except (OverflowError, OSError, ValueError):
        return None


def parse_service_info(
    payload: dict[str, Any], *, updated_at: datetime | None = None
) -> TrafficSnapshot:
    """Convert service-info fields into independently usable traffic values.

    The current multiplier rule applies ``monthly_data_multiplier`` to
    ``data_counter``. Validate this rule with KiwiVM panel samples before release.
    Byte values are kept exact until sensors convert them to decimal GB.
    """
    quota = _decimal(payload.get("plan_monthly_data"))
    counter = _decimal(payload.get("data_counter"))
    multiplier = _decimal(payload.get("monthly_data_multiplier"), positive=True)
    used = (
        counter * multiplier
        if counter is not None and multiplier is not None
        else None
    )
    remaining = (
        max(quota - used, Decimal(0))
        if quota is not None and used is not None
        else None
    )
    percent = (used * 100 / quota) if quota and used is not None else None

    return TrafficSnapshot(
        quota_bytes=quota,
        used_bytes=used,
        remaining_bytes=remaining,
        usage_percent=percent,
        next_reset=_timestamp(payload.get("data_next_reset")),
        updated_at=updated_at or datetime.now(UTC),
    )
