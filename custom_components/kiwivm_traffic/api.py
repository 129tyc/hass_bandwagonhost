"""Small, read-only client for the KiwiVM service information endpoint."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import aiohttp

from .const import API_URL

_REQUEST_SEMAPHORE = asyncio.Semaphore(2)
_AUTH_ERROR = "700005"


class KiwiVMError(Exception):
    """Base error for a failed KiwiVM request."""


class KiwiVMConnectionError(KiwiVMError):
    """The service information endpoint could not be reached."""


class KiwiVMAuthenticationError(KiwiVMError):
    """KiwiVM rejected the VEID/API key pair."""


class KiwiVMResponseError(KiwiVMError):
    """KiwiVM returned an invalid or unsuccessful response."""


class KiwiVMRateLimitError(KiwiVMError):
    """KiwiVM rejected the request because of rate limiting."""

    def __init__(self, retry_after: float | None = None) -> None:
        super().__init__("KiwiVM API rate limited the request")
        self.retry_after = retry_after


def _retry_after(value: str | None) -> float | None:
    """Read standard seconds or HTTP-date Retry-After values."""
    if value is None:
        return None
    try:
        seconds = float(value)
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)
        seconds = (retry_at - datetime.now(UTC)).total_seconds()
    return max(seconds, 0) if seconds >= 0 else None


async def async_get_service_info(
    session: aiohttp.ClientSession, veid: str, api_key: str
) -> dict[str, Any]:
    """Fetch read-only service information using POST form data."""
    try:
        async with _REQUEST_SEMAPHORE:
            async with session.post(
                API_URL,
                data={"veid": veid, "api_key": api_key},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status == 429:
                    raise KiwiVMRateLimitError(
                        _retry_after(response.headers.get("Retry-After"))
                    )
                response.raise_for_status()
                try:
                    payload = await response.json(content_type=None)
                except (aiohttp.ContentTypeError, json.JSONDecodeError) as err:
                    raise KiwiVMResponseError("KiwiVM returned invalid JSON") from err
    except KiwiVMError:
        raise
    except (aiohttp.ClientError, TimeoutError) as err:
        raise KiwiVMConnectionError("KiwiVM request failed") from err

    if not isinstance(payload, dict):
        raise KiwiVMResponseError("KiwiVM returned an unexpected response")

    error = payload.get("error", 0)
    error_code = str(error)
    if error not in (None, 0, "0"):
        if error_code == _AUTH_ERROR:
            raise KiwiVMAuthenticationError("KiwiVM authentication failed")
        message = payload.get("message", "")
        if isinstance(message, str) and any(
            phrase in message.casefold()
            for phrase in ("rate limit", "too many requests", "request limit")
        ):
            raise KiwiVMRateLimitError()
        raise KiwiVMResponseError("KiwiVM returned an API error")

    return payload
