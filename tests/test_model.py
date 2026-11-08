"""Capability gates and validation with synthetic account data only."""
import unittest

import test_api  # Establish the independent package without importing HA.
from tohmo_client_test.api import TohmoError
from tohmo_client_test.model import current_limits, session_active, setting_payload, supported_settings


def point(**updates):
    return {"id": "test-point", "isOwner": True, "name": "Test charger",
            "is_max_current_supported": True, "allowed_min_current_a": 6,
            "allowed_max_current_a": 16, "max_current_a": 16,
            "min_charging_current": 6, "enable_keep_awake": False,
            "requires_authorization": True, "is_connector_lock_supported": True,
            "connector_lock": False, "is_light_intensity_supported": True,
            "light_intensity": 100, **updates}


class CapabilityTests(unittest.TestCase):
    def test_non_owner_cannot_modify_settings(self):
        self.assertEqual(supported_settings(point(isOwner=False), {}), set())
        with self.assertRaises(TohmoError):
            setting_payload(point(isOwner=False), {}, "max_current_a", 6)

    def test_false_flags_and_auth_enforcement(self):
        enabled = supported_settings(point(is_max_current_supported=False,
            is_connector_lock_supported=False, is_light_intensity_supported=False),
            {"personalCharging": {"enforceAuthentication": True}})
        self.assertTrue({"max_current_a", "connector_lock", "light_intensity", "requires_authorization"}.isdisjoint(enabled))

    def test_unknown_limits_do_not_create_max_current(self):
        for invalid in (None, "not-a-number", float("nan"), float("inf"), -1):
            item = point(allowed_max_current_a=invalid)
            self.assertIsNone(current_limits(item))
            self.assertNotIn("max_current_a", supported_settings(item, {}))

    def test_power_group_preserves_other_fields(self):
        self.assertEqual(setting_payload(point(), {}, "max_current_a", 10),
                         {"max_current_a": 10, "min_charging_current": 6, "enable_keep_awake": False})
        self.assertEqual(setting_payload(point(), {}, "enable_keep_awake", True),
                         {"max_current_a": 16, "min_charging_current": 6, "enable_keep_awake": True})

    def test_out_of_range_and_inconsistent_current_rejected(self):
        for value in (True, 5, 17, 6.5, float("nan"), float("inf")):
            with self.assertRaises(TohmoError):
                setting_payload(point(), {}, "max_current_a", value)
        with self.assertRaises(TohmoError):
            setting_payload(point(max_current_a=10), {}, "min_charging_current", 11)

    def test_unknown_field_rejected(self):
        for key in ("disable_automatic_firmware_updates", "url", "smart_charging", "password"):
            with self.assertRaises(TohmoError):
                setting_payload(point(), {}, key, False)

    def test_led_only_verified_app_presets(self):
        self.assertEqual(setting_payload(point(), {}, "light_intensity", 50), {"light_intensity": 50})
        with self.assertRaises(TohmoError):
            setting_payload(point(), {}, "light_intensity", 100)

    def test_suspended_zero_power_session_still_active(self):
        self.assertTrue(session_active({"id": "synthetic-session", "status": "active", "stoppedAt": None, "power": 0, "evseStatus": "suspended"}))
        self.assertFalse(session_active({"id": "synthetic-session", "status": "finished", "stoppedAt": "2020-01-01"}))
        self.assertFalse(session_active(None))
        # Unknown in-progress states must not allow duplicate starts.
        self.assertTrue(session_active({"id": "synthetic-session", "status": "pending", "stoppedAt": None}))


if __name__ == "__main__":
    unittest.main()
