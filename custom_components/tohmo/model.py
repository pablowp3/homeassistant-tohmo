"""Capability and validation rules grounded in the mobile app and account data."""
from __future__ import annotations

import math
from typing import Any

from .api import TohmoError


BOOL_SETTINGS = {"requires_authorization", "enable_keep_awake", "connector_lock"}
NUMBER_SETTINGS = {"max_current_a", "min_charging_current"}
LED_LEVELS = {"low": 5, "medium": 20, "high": 50}
START_STATUSES = {"ready", "available", "occupied", "preparing", "finishing"}


def session_active(session: Any) -> bool:
    """A suspended vehicle can still have a live, billable session."""
    return (isinstance(session, dict) and session.get("id") is not None
            and session.get("stoppedAt") is None
            and session.get("status") not in {"finished", "failed", "cancelled", "canceled"})


def current_limits(point: dict) -> tuple[float, float] | None:
    try:
        lower = float(point["allowed_min_current_a"])
        upper = float(point["allowed_max_current_a"])
    except (KeyError, TypeError, ValueError):
        return None
    if not math.isfinite(lower) or not math.isfinite(upper) or lower <= 0 or upper < lower:
        return None
    return lower, upper


def supported_settings(point: dict, features: dict) -> set[str]:
    if point.get("isOwner") is not True:
        return set()
    supported = {"name"}
    if isinstance(point.get("requires_authorization"), bool) and not features.get("personalCharging", {}).get("enforceAuthentication", False):
        supported.add("requires_authorization")
    if isinstance(point.get("enable_keep_awake"), bool):
        supported.add("enable_keep_awake")
    if point.get("is_max_current_supported") is True and current_limits(point):
        supported.add("max_current_a")
    if "min_charging_current" in point and current_limits(point):
        supported.add("min_charging_current")
    if point.get("is_connector_lock_supported") is True:
        supported.add("connector_lock")
    if point.get("is_light_intensity_supported") is True:
        supported.add("light_intensity")
    return supported


def setting_payload(point: dict, features: dict, key: str, value: Any) -> dict:
    """Whitelist only settings with verified payloads; enforce server limits."""
    if key not in supported_settings(point, features):
        raise TohmoError("This setting is not available for this charger/account")
    if key in BOOL_SETTINGS:
        if not isinstance(value, bool):
            raise TohmoError("This setting requires a boolean")
    elif key in NUMBER_SETTINGS:
        limits = current_limits(point)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise TohmoError("Current must be a finite number")
        if not limits or not limits[0] <= value <= limits[1] or value != int(value):
            raise TohmoError("Current is outside the charger's allowed whole-amp range")
        value = int(value)
    elif key == "light_intensity":
        if value not in LED_LEVELS.values():
            raise TohmoError("Select a light level offered by the app")
    elif key == "name":
        if not isinstance(value, str) or not value.strip():
            raise TohmoError("Charger name cannot be empty")
        value = value.strip()
    if key in NUMBER_SETTINGS or key == "enable_keep_awake":
        # The app saves this group together (Hermes function 44740).
        payload = {field: point.get(field) for field in NUMBER_SETTINGS | {"enable_keep_awake"}}
        payload[key] = value
        if not isinstance(payload["enable_keep_awake"], bool):
            raise TohmoError("Keep-awake state is unavailable")
        limits = current_limits(point)
        for field in NUMBER_SETTINGS:
            number = payload[field]
            if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number) or not limits or not limits[0] <= number <= limits[1]:
                raise TohmoError("Current settings cannot be safely preserved")
        if payload["min_charging_current"] > payload["max_current_a"]:
            raise TohmoError("Keep-awake current cannot exceed maximum charging current")
        return payload
    return {key: value}
