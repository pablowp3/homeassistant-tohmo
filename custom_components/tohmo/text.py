"""Rename an owned charger."""
from homeassistant.components.text import TextEntity
from homeassistant.helpers.entity import EntityCategory

from .entity import TohmoEntity, setup_entities
from .model import supported_settings


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(coordinator, point_id, point):
        if "name" in supported_settings(point, coordinator.features):
            yield ChargerName(coordinator, point_id, "name")
    setup_entities(entry, async_add_entities, factory)


class ChargerName(TohmoEntity, TextEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min = 1

    @property
    def available(self):
        return super().available and "name" in supported_settings(self.point, self.coordinator.features)

    @property
    def native_value(self):
        return self.point.get("name")

    async def async_set_value(self, value):
        await self.coordinator.command(self.point_id, "setting", key="name", value=value)

