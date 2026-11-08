"""Regression for diagnostic sensors without an inherited unit attribute."""
import importlib
import sys
import types
import unittest
from unittest.mock import patch

import test_api  # Establish the independent package without importing HA.


class EntityInterface:
    def __init__(self, coordinator, point_id, key, **kwargs):
        self.key = key
        self.session = {"currency": {"code": "EUR"}}


class SensorInterface:
    # Deliberately no _attr_native_unit_of_measurement: HA does not supply it.
    pass


def module(name, **attrs):
    result = types.ModuleType(name)
    result.__dict__.update(attrs)
    return result


with patch.dict(sys.modules, {
    "homeassistant": module("homeassistant"),
    "homeassistant.components": module("components"),
    "homeassistant.components.sensor": module("sensor", SensorEntity=SensorInterface,
        SensorDeviceClass=types.SimpleNamespace(POWER="power", ENERGY="energy", DURATION="duration", MONETARY="monetary", ENUM="enum"),
        SensorStateClass=types.SimpleNamespace(MEASUREMENT="measurement")),
    "homeassistant.const": module("const", UnitOfEnergy=types.SimpleNamespace(WATT_HOUR="Wh", KILO_WATT_HOUR="kWh"),
        UnitOfPower=types.SimpleNamespace(WATT="W"), UnitOfTime=types.SimpleNamespace(SECONDS="s")),
    "homeassistant.helpers": module("helpers"),
    "homeassistant.helpers.entity": module("entity", EntityCategory=types.SimpleNamespace(DIAGNOSTIC="diagnostic")),
    "tohmo_client_test.entity": module("entity", TohmoEntity=EntityInterface, setup_entities=None),
}):
    ChargerSensor = importlib.import_module("tohmo_client_test.sensor").ChargerSensor


class SensorTests(unittest.TestCase):
    def test_diagnostic_units_are_explicitly_unitless(self):
        for key in ("firmware_version", "firmware_update"):
            with self.subTest(key=key):
                self.assertIsNone(ChargerSensor(None, "test-point", key).native_unit_of_measurement)

    def test_measured_and_currency_units_are_preserved(self):
        for key, expected in (("power", "W"), ("energy", "Wh"), ("duration", "s"),
                              ("amount", "EUR"), ("last_month_energy_kwh", "kWh"), ("status", None)):
            with self.subTest(key=key):
                self.assertEqual(ChargerSensor(None, "test-point", key).native_unit_of_measurement, expected)
