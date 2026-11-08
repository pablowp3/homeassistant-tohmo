"""Charging session and supported boolean settings."""
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import EntityCategory

from .entity import TohmoEntity, setup_entities
from .model import BOOL_SETTINGS, session_active, supported_settings


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(coordinator, point_id, point):
        if point.get("isOwner") is True:
            for evse in point.get("evses", []):
                yield ChargingSwitch(coordinator, point_id, "charging", evse_id=str(evse["id"]))
        for key in BOOL_SETTINGS & supported_settings(point, coordinator.features):
            yield SettingSwitch(coordinator, point_id, key)
    setup_entities(entry, async_add_entities, factory)


class ChargingSwitch(TohmoEntity, SwitchEntity):
    _attr_icon = "mdi:ev-station"

    @property
    def is_on(self):
        return session_active(self.session)

    @property
    def available(self):
        return super().available and self.point.get("isOwner") is True

    async def async_turn_on(self, **kwargs):
        await self.coordinator.command(self.point_id, "start", evse_id=self.evse_id)

    async def async_turn_off(self, **kwargs):
        await self.coordinator.command(self.point_id, "stop", evse_id=self.evse_id)


class SettingSwitch(TohmoEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def available(self):
        return super().available and self.key in supported_settings(self.point, self.coordinator.features)

    @property
    def is_on(self):
        return self.point.get(self.key)

    async def async_turn_on(self, **kwargs):
        await self.coordinator.command(self.point_id, "setting", key=self.key, value=True)

    async def async_turn_off(self, **kwargs):
        await self.coordinator.command(self.point_id, "setting", key=self.key, value=False)

