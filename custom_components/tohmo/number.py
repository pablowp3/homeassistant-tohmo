"""Current limits, bounded by the charger's own reported capabilities."""
from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.helpers.entity import EntityCategory

from .entity import TohmoEntity, setup_entities
from .model import NUMBER_SETTINGS, current_limits, supported_settings


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(coordinator, point_id, point):
        for key in NUMBER_SETTINGS & supported_settings(point, coordinator.features):
            yield CurrentNumber(coordinator, point_id, key)
    setup_entities(entry, async_add_entities, factory)


class CurrentNumber(TohmoEntity, NumberEntity):
    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def available(self):
        return super().available and self.key in supported_settings(self.point, self.coordinator.features)

    @property
    def native_value(self):
        return self.point.get(self.key)

    @property
    def native_min_value(self):
        limits = current_limits(self.point)
        return limits[0] if limits else None

    @property
    def native_max_value(self):
        limits = current_limits(self.point)
        return limits[1] if limits else None

    async def async_set_native_value(self, value):
        await self.coordinator.command(self.point_id, "setting", key=self.key, value=value)

