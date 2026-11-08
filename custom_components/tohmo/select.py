"""LED levels offered by the app, preserving an existing out-of-menu value."""
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.entity import EntityCategory

from .entity import TohmoEntity, setup_entities
from .model import LED_LEVELS, supported_settings


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(coordinator, point_id, point):
        if "light_intensity" in supported_settings(point, coordinator.features):
            yield LedSelect(coordinator, point_id, "light_intensity")
    setup_entities(entry, async_add_entities, factory)


class LedSelect(TohmoEntity, SelectEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:brightness-6"

    @property
    def available(self):
        return super().available and self.key in supported_settings(self.point, self.coordinator.features)

    @property
    def options(self):
        options = [str(value) for value in LED_LEVELS.values()]
        if self.current_option is not None and self.current_option not in options:
            options.append(self.current_option)
        return options

    @property
    def current_option(self):
        value = self.point.get("light_intensity")
        return str(value) if value is not None else None

    async def async_select_option(self, option):
        if option == self.current_option:
            return
        await self.coordinator.command(self.point_id, "setting", key=self.key, value=int(option))

