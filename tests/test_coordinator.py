"""Command-boundary tests using minimal HA lifecycle interfaces, not a live HA."""
from copy import deepcopy
import importlib
import sys
import types
import unittest
from unittest.mock import patch

import test_api
from test_model import point
from tohmo_client_test.api import ConnectionError


class HomeAssistantError(Exception):
    pass


class ConfigEntryAuthFailed(HomeAssistantError):
    pass


class UpdateFailed(Exception):
    pass


class CoordinatorInterface:
    @classmethod
    def __class_getitem__(cls, _):
        return cls

    def __init__(self, hass, logger, *, name, config_entry, update_interval):
        self.hass = hass
        self.config_entry = config_entry
        self.data = {}
        self.last_update_success = True

    async def async_refresh(self):
        try:
            self.data = await self._async_update_data()
            self.last_update_success = True
        except (UpdateFailed, ConfigEntryAuthFailed):
            self.last_update_success = False

    async def async_request_refresh(self):
        await self.async_refresh()

    def async_update_listeners(self):
        pass


def module(name, **attrs):
    value = types.ModuleType(name)
    value.__dict__.update(attrs)
    return value


with patch.dict(sys.modules, {
    "homeassistant": module("homeassistant"),
    "homeassistant.config_entries": module("config_entries", ConfigEntry=object),
    "homeassistant.core": module("core", HomeAssistant=object),
    "homeassistant.exceptions": module("exceptions", ConfigEntryAuthFailed=ConfigEntryAuthFailed, HomeAssistantError=HomeAssistantError),
    "homeassistant.helpers": module("helpers"),
    "homeassistant.helpers.update_coordinator": module("update_coordinator", DataUpdateCoordinator=CoordinatorInterface, UpdateFailed=UpdateFailed),
}):
    TohmoCoordinator = importlib.import_module("tohmo_client_test.coordinator").TohmoCoordinator


def charger(active=False, **updates):
    session = ({"id": "test-session", "status": "active", "stoppedAt": None,
                "power": 0, "isRemoteStopEnabled": True,
                "isRemoteStopSupported": True} if active else None)
    return point(evses=[{"id": "42", "identifier": "ES*TEST*E42",
                         "status": "suspended" if active else "ready", "session": session}],
                 isFirmwareUpdatesSupported=True, isFirmwareUpdating=False, **updates)


class Client:
    def __init__(self, current, error=None):
        self.current = current
        self.error = error
        self.calls = []

    async def charge_points(self):
        self.calls.append(("read",))
        return [deepcopy(self.current)]

    async def _write(self, name, *args):
        self.calls.append((name, *args))
        if self.error:
            raise self.error

    async def start(self, *args):
        await self._write("start", *args)

    async def stop(self, *args):
        await self._write("stop", *args)

    async def update_point(self, *args):
        await self._write("patch", *args)

    async def firmware_check(self, *args):
        self.calls.append(("firmware_read", *args))

    async def firmware_install(self, *args):
        await self._write("firmware_write", *args)


def coordinator(client):
    instance = TohmoCoordinator(None, None, client)
    instance._features_loaded = True
    instance.data = {"test-point": charger()}
    return instance


class CommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_fresh_ownership_revocation_blocks_write(self):
        client = Client(charger(isOwner=False))
        with self.assertRaises(HomeAssistantError):
            await coordinator(client).command("test-point", "start", evse_id="42")
        self.assertEqual(client.calls, [("read",)])

    async def test_fresh_active_session_blocks_duplicate_start(self):
        client = Client(charger(active=True))
        with self.assertRaises(HomeAssistantError):
            await coordinator(client).command("test-point", "start", evse_id="42")
        self.assertEqual(client.calls, [("read",)])

    async def test_stop_suspended_session_uses_live_session_id_once(self):
        client = Client(charger(active=True))
        await coordinator(client).command("test-point", "stop", evse_id="42")
        self.assertEqual(client.calls, [("read",), ("stop", "test-session"), ("read",)])

    async def test_stop_permission_checked(self):
        current = charger(active=True)
        current["evses"][0]["session"]["isRemoteStopEnabled"] = False
        client = Client(current)
        with self.assertRaises(HomeAssistantError):
            await coordinator(client).command("test-point", "stop", evse_id="42")
        self.assertEqual(client.calls, [("read",)])

    async def test_current_revalidates_fresh_server_limit(self):
        client = Client(charger(allowed_max_current_a=10, max_current_a=10))
        with self.assertRaises(HomeAssistantError):
            await coordinator(client).command("test-point", "setting", key="max_current_a", value=12)
        self.assertEqual(client.calls, [("read",)])

    async def test_power_patch_preserves_fresh_other_settings(self):
        client = Client(charger(enable_keep_awake=True))
        await coordinator(client).command("test-point", "setting", key="max_current_a", value=10)
        self.assertEqual(client.calls[1], ("patch", "test-point", {"max_current_a": 10, "min_charging_current": 6, "enable_keep_awake": True}))

    async def test_active_session_blocks_firmware_write(self):
        client = Client(charger(active=True))
        with self.assertRaises(HomeAssistantError):
            await coordinator(client).command("test-point", "firmware_install")
        self.assertFalse(any(call[0] == "firmware_write" for call in client.calls))

    async def test_ambiguous_command_is_not_replayed(self):
        client = Client(charger(active=True), error=ConnectionError("Result unknown"))
        with self.assertRaises(HomeAssistantError):
            await coordinator(client).command("test-point", "stop", evse_id="42")
        self.assertEqual(client.calls, [("read",), ("stop", "test-session")])

    async def test_firmware_check_records_visible_result(self):
        client = Client(charger())
        instance = coordinator(client)
        await instance.command("test-point", "firmware_check")
        self.assertTrue(instance.firmware_available["test-point"])


if __name__ == "__main__":
    unittest.main()
