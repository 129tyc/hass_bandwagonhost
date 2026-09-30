"""Tests for KiwiVM responses and traffic normalization."""

from __future__ import annotations

import aiohttp
import pytest

from custom_components.kiwivm_traffic.api import (
    KiwiVMAuthenticationError,
    KiwiVMRateLimitError,
    async_get_service_info,
)
from custom_components.kiwivm_traffic.const import API_URL


class _FakeResponse:
    """Minimal async response used to check request classification."""

    def __init__(
        self, payload: dict, *, status: int = 200, headers: dict | None = None
    ) -> None:
        self.payload = payload
        self.status = status
        self.headers = headers or {}

    async def __aenter__(self) -> _FakeResponse:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def json(self, *, content_type: str | None = None) -> dict:
        return self.payload

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise aiohttp.ClientResponseError(
                request_info=None,
                history=(),
                status=self.status,
                message="test response",
            )


class _FakeSession:
    """Capture method and parameters without making a request."""

    def __init__(self, response: _FakeResponse) -> None:
        self.response = response
        self.url: str | None = None
        self.data: dict | None = None

    def post(self, url: str, *, data: dict, timeout: aiohttp.ClientTimeout):
        self.url = url
        self.data = data
        return self.response


@pytest.mark.asyncio
async def test_request_posts_credentials_outside_url() -> None:
    """Credentials are sent in form data to the fixed read-only endpoint."""
    session = _FakeSession(_FakeResponse({"error": 0, "hostname": "ignored"}))

    await async_get_service_info(session, "12345", "secret-test-key")  # type: ignore[arg-type]

    assert session.url == API_URL
    assert session.data == {"veid": "12345", "api_key": "secret-test-key"}
    assert "secret-test-key" not in session.url


@pytest.mark.asyncio
async def test_auth_and_rate_limit_errors_are_classified() -> None:
    """Authentication and HTTP rate-limit errors have distinct exceptions."""
    with pytest.raises(KiwiVMAuthenticationError):
        await async_get_service_info(
            _FakeSession(_FakeResponse({"error": 700005})),  # type: ignore[arg-type]
            "12345",
            "test-key",
        )

    with pytest.raises(KiwiVMRateLimitError) as raised:
        await async_get_service_info(
            _FakeSession(
                _FakeResponse({}, status=429, headers={"Retry-After": "120"})
            ),  # type: ignore[arg-type]
            "12345",
            "test-key",
        )
    assert raised.value.retry_after == 120
