"""Small, independently implemented client for the Tohmo mobile API.

Only reads may be retried after token renewal. A command is sent at most once,
including when its HTTP response is lost or authentication expires in flight.
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable
import math
import time
from typing import Any
from urllib.parse import quote

import aiohttp

from .const import APP_ID, APP_VERSION, BASE_URL, CLIENT_ID, CLIENT_SECRET


class TohmoError(Exception):
    """An error containing no server response, URL, or account credentials."""


class AuthenticationError(TohmoError):
    """The account needs to sign in again."""


class ConnectionError(TohmoError):
    """The result could not be received; commands must not be replayed."""


class ApiError(TohmoError):
    """A request was rejected by the service."""

    def __init__(self, status: int) -> None:
        self.status = status
        super().__init__(f"Tohmo request rejected (HTTP {status})")


class TohmoClient:
    """Own OAuth lifecycle, without retaining account passwords."""

    def __init__(self, session: aiohttp.ClientSession, tokens: dict | None = None,
                 on_tokens: Callable[[dict], None] | None = None) -> None:
        self._session = session
        self._tokens = dict(tokens or {})
        self._on_tokens = on_tokens
        self._token_lock = asyncio.Lock()
        self._retry_at = 0.0

    @property
    def tokens(self) -> dict:
        return dict(self._tokens)

    async def login(self, username: str, password: str) -> None:
        async with self._token_lock:
            await self._grant({"grant_type": "password", "username": username,
                               "password": password, "scope": "*"})

    async def _grant(self, grant: dict) -> None:
        payload = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, **grant}
        result = await self._http("POST", "/app/oauth/token", payload, token=None)
        if not isinstance(result, dict) or not isinstance(result.get("access_token"), str) or not result["access_token"]:
            raise AuthenticationError("Tohmo did not return valid authentication")
        refresh = result.get("refresh_token", self._tokens.get("refresh_token"))
        if not isinstance(refresh, str) or not refresh:
            raise AuthenticationError("Tohmo did not return renewable authentication")
        try:
            lifetime = float(result["expires_in"])
        except (KeyError, ValueError, TypeError):
            raise AuthenticationError("Tohmo returned invalid token expiry") from None
        if not math.isfinite(lifetime) or lifetime <= 0:
            raise AuthenticationError("Tohmo authentication has expired")
        self._tokens = {"access_token": result["access_token"], "refresh_token": refresh,
                        "expires_at": time.time() + lifetime}
        if self._on_tokens:
            self._on_tokens(self.tokens)

    async def _ensure_token(self, rejected_token: str | None = None) -> None:
        async with self._token_lock:
            current = self._tokens.get("access_token")
            if current and self._tokens.get("expires_at", 0) > time.time() + 60:
                if rejected_token is None or current != rejected_token:
                    return
            refresh = self._tokens.get("refresh_token")
            if not refresh:
                raise AuthenticationError("Tohmo sign-in required")
            await self._grant({"grant_type": "refresh_token", "refresh_token": refresh})

    async def _http(self, method: str, path: str, payload: dict | None,
                    *, token: str | None) -> Any:
        if time.time() < self._retry_at:
            raise ApiError(429)
        headers = {"Accept": "application/json", "Accept-Language": "en",
                   "X-App-Id": APP_ID, "X-App-Version": APP_VERSION}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            async with self._session.request(
                method, BASE_URL + path, headers=headers, json=payload,
                timeout=aiohttp.ClientTimeout(total=25), allow_redirects=False,
            ) as response:
                if response.status == 429:
                    try:
                        delay = max(1.0, float(response.headers.get("Retry-After", "60")))
                    except ValueError:
                        delay = 60.0
                    self._retry_at = time.time() + delay
                if response.status == 401 or (path == "/app/oauth/token" and response.status in (400, 403)):
                    raise AuthenticationError("Tohmo sign-in required")
                if response.status < 200 or response.status >= 300:
                    raise ApiError(response.status)
                if response.status == 204:
                    return None
                try:
                    result = await response.json()
                except (ValueError, aiohttp.ContentTypeError):
                    raise ConnectionError("Tohmo returned an unreadable response; result unknown") from None
                if isinstance(result, dict) and (result.get("success") is False or result.get("error")):
                    raise ApiError(response.status)
                return result
        except (aiohttp.ClientError, TimeoutError):
            raise ConnectionError("Tohmo response unavailable; command result may be unknown") from None

    async def request(self, method: str, path: str, payload: dict | None = None) -> Any:
        await self._ensure_token()
        token = self._tokens["access_token"]
        try:
            return await self._http(method, path, payload, token=token)
        except AuthenticationError:
            if method not in ("GET", "OPTIONS"):
                raise
            await self._ensure_token(rejected_token=token)
            return await self._http(method, path, payload, token=self._tokens["access_token"])

    async def charge_points(self) -> list[dict]:
        result = await self.request("GET", "/app/personal/charge-points")
        if not isinstance(result, dict) or not isinstance(result.get("data"), list):
            raise ConnectionError("Tohmo returned an unexpected charger response")
        if any(not isinstance(point, dict) or "id" not in point for point in result["data"]):
            raise ConnectionError("Tohmo returned an invalid charger")
        return result["data"]

    async def global_settings(self) -> dict:
        result = await self.request("GET", "/app/settings/global")
        if not isinstance(result, dict):
            raise ConnectionError("Tohmo returned invalid settings")
        return result

    async def start(self, evse_id: int | str) -> Any:
        # The app uses evse.id here, not the alphanumeric evse.identifier.
        if isinstance(evse_id, bool) or not str(evse_id).isascii() or not str(evse_id).isdigit():
            raise TohmoError("The internal EVSE ID must be numeric")
        return await self.request("POST", "/app/session/start", {"evseId": int(evse_id)})

    async def stop(self, session_id: int | str) -> Any:
        return await self.request("POST", f"/app/session/{segment(session_id)}/end")

    async def reboot(self, point_id: int | str) -> Any:
        return await self.request("POST", f"/app/personal/charge-points/{segment(point_id)}/reboot")

    async def unlock(self, point_id: int | str, evse_id: int | str) -> Any:
        return await self.request("POST", f"/app/personal/charge-point/{segment(point_id)}/unlock-connector/{segment(evse_id)}")

    async def update_point(self, point_id: int | str, payload: dict) -> Any:
        return await self.request("PATCH", f"/app/personal/charge-points/{segment(point_id)}", payload)

    async def firmware_check(self, point_id: int | str) -> Any:
        return await self.request("GET", f"/app/personal/charge-points/{segment(point_id)}/firmware-updates/check")

    async def firmware_install(self, point_id: int | str) -> Any:
        return await self.request("POST", f"/app/personal/charge-points/{segment(point_id)}/firmware-updates")


def segment(identifier: int | str) -> str:
    """Preserve identifiers without numeric coercion or URL interpretation."""
    if isinstance(identifier, bool) or not isinstance(identifier, (str, int)) or not str(identifier):
        raise ValueError("Invalid identifier")
    return quote(str(identifier), safe="")

