"""Wh, W and seconds from the cloud, without inference from suspended status."""
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfEnergy, UnitOfPower, UnitOfTime
from homeassistant.helpers.entity import EntityCategory

from .entity import TohmoEntity, setup_entities

SENSORS = {
    "status": (None, None, None),
    "power": (SensorDeviceClass.POWER, UnitOfPower.WATT, SensorStateClass.MEASUREMENT),
    "energy": (SensorDeviceClass.ENERGY, UnitOfEnergy.WATT_HOUR, None),
    "duration": (SensorDeviceClass.DURATION, UnitOfTime.SECONDS, None),
    "amount": (SensorDeviceClass.MONETARY, None, None),
    "session_status": (None, None, None),
}


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(coordinator, point_id, point):
        yield ChargerSensor(coordinator, point_id, "firmware_version")
        yield ChargerSensor(coordinator, point_id, "last_month_energy_kwh")
        if point.get("isFirmwareUpdatesSupported") is True:
            yield ChargerSensor(coordinator, point_id, "firmware_update")
        for evse in point.get("evses", []):
            for key in SENSORS:
                yield ChargerSensor(coordinator, point_id, key, evse_id=str(evse["id"]))
    setup_entities(entry, async_add_entities, factory)


class ChargerSensor(TohmoEntity, SensorEntity):
    def __init__(self, coordinator, point_id, key, **kwargs):
        super().__init__(coordinator, point_id, key, **kwargs)
        self._attr_native_unit_of_measurement = None
        if key in SENSORS:
            self._attr_device_class, self._attr_native_unit_of_measurement, self._attr_state_class = SENSORS[key]
        elif key in {"firmware_version", "firmware_update"}:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            if key == "firmware_update":
                self._attr_device_class = SensorDeviceClass.ENUM
                self._attr_options = ["available", "installing"]
        elif key == "last_month_energy_kwh":
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    @property
    def native_value(self):
        if self.key == "firmware_update":
            if self.point.get("isFirmwareUpdating"):
                return "installing"
            return "available" if self.coordinator.firmware_available.get(self.point_id) is True else None
        if self.evse_id is None:
            return self.point.get(self.key)
        if self.key == "status":
            return self.evse.get("status")
        if self.key == "session_status":
            return self.session.get("status")
        return self.session.get(self.key)

    @property
    def native_unit_of_measurement(self):
        if self.key == "amount":
            currency = self.session.get("currency")
            return currency.get("code") if isinstance(currency, dict) else None
        return self._attr_native_unit_of_measurement
