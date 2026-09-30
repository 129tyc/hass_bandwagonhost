"""Tests for the dependency-free traffic normalization layer."""

import unittest
from datetime import UTC, datetime
from decimal import Decimal

from custom_components.kiwivm_traffic.traffic import parse_service_info


class TrafficParsingTests(unittest.TestCase):
    """Check unit conversion inputs and API edge cases."""

    def test_one_times_multiplier(self) -> None:
        snapshot = parse_service_info(
            {
                "plan_monthly_data": "100000000000",
                "data_counter": "25000000000",
                "monthly_data_multiplier": "1",
                "data_next_reset": "1800000000",
            },
            updated_at=datetime(2026, 9, 30, tzinfo=UTC),
        )

        self.assertEqual(snapshot.quota_bytes, Decimal("100000000000"))
        self.assertEqual(snapshot.used_bytes, Decimal("25000000000"))
        self.assertEqual(snapshot.remaining_bytes, Decimal("75000000000"))
        self.assertEqual(snapshot.usage_percent, Decimal("25.00"))
        self.assertEqual(snapshot.next_reset, datetime.fromtimestamp(1800000000, UTC))
        self.assertEqual(snapshot.updated_at.tzinfo, UTC)

    def test_non_one_multiplier(self) -> None:
        snapshot = parse_service_info(
            {
                "plan_monthly_data": 1000,
                "data_counter": 250,
                "monthly_data_multiplier": 2,
            }
        )

        self.assertEqual(snapshot.used_bytes, Decimal(500))
        self.assertEqual(snapshot.remaining_bytes, Decimal(500))
        self.assertEqual(snapshot.usage_percent, Decimal(50))

    def test_invalid_fields_stay_unavailable_independently(self) -> None:
        snapshot = parse_service_info(
            {
                "plan_monthly_data": "not a number",
                "data_counter": -10,
                "monthly_data_multiplier": 0,
                "data_next_reset": -1,
            }
        )

        self.assertIsNone(snapshot.quota_bytes)
        self.assertIsNone(snapshot.used_bytes)
        self.assertIsNone(snapshot.remaining_bytes)
        self.assertIsNone(snapshot.usage_percent)
        self.assertIsNone(snapshot.next_reset)

    def test_zero_quota_and_overuse(self) -> None:
        zero = parse_service_info(
            {"plan_monthly_data": 0, "data_counter": 5, "monthly_data_multiplier": 1}
        )
        over = parse_service_info(
            {
                "plan_monthly_data": 100,
                "data_counter": 120,
                "monthly_data_multiplier": 1,
            }
        )

        self.assertEqual(zero.remaining_bytes, Decimal(0))
        self.assertIsNone(zero.usage_percent)
        self.assertEqual(over.remaining_bytes, Decimal(0))
        self.assertEqual(over.usage_percent, Decimal(120))
