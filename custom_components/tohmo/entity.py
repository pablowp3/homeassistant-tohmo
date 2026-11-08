"""Shared entity identity, device grouping and dynamic discovery."""
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


def setup_entities(entry, async_add_entities, factory):
    coordinator = entry.runtime_data
    known = set()

    def discover():
        added = []
        for point_id, point in coordinator.data.items():
            for entity in factory(coordinator, point_id, point):
                if entity.unique_id not in known:
                    known.add(entity.unique_id)
                    added.append(entity)
        if added:
            async_add_entities(added)

    discover()
    entry.async_on_unload(coordinator.async_add_listener(discover))


class TohmoEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, point_id, key, *, evse_id=None):
        super().__init__(coordinator)
        self.point_id = point_id
        self.key = key
        self.evse_id = evse_id
        self._attr_unique_id = f"{point_id}_{evse_id + '_' if evse_id else ''}{key}"
        self._attr_translation_key = key

    @property
    def point(self):
        return self.coordinator.data.get(self.point_id, {})

    @property
    def evse(self):
        return next((item for item in self.point.get("evses", []) if str(item.get("id")) == self.evse_id), {})

    @property
    def session(self):
        return self.evse.get("session") or {}

    @property
    def available(self):
        return super().available and bool(self.point) and (self.evse_id is None or bool(self.evse))

    @property
    def device_info(self):
        return DeviceInfo(identifiers={(DOMAIN, self.point_id)},
                          name=self.point.get("name") or "Tohmo charger",
                          sw_version=self.point.get("firmware_version"))
