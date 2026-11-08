"""Explicit charger commands, with no optimistic state or automatic replay."""
from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.helpers.entity import EntityCategory

from .entity import TohmoEntity, setup_entities
from .model import START_STATUSES, session_active


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(coordinator, point_id, point):
        if point.get("isOwner") is not True:
            return
        yield ChargerButton(coordinator, point_id, "reboot")
        if point.get("isFirmwareUpdatesSupported") is True:
            yield ChargerButton(coordinator, point_id, "firmware_check")
            yield ChargerButton(coordinator, point_id, "firmware_install")
        for evse in point.get("evses", []):
            for action in ("start", "stop"):
                yield ChargerButton(coordinator, point_id, action, evse_id=str(evse["id"]))
            if point.get("is_connector_lock_supported") is True:
                yield ChargerButton(coordinator, point_id, "unlock", evse_id=str(evse["id"]))
    setup_entities(entry, async_add_entities, factory)


class ChargerButton(TohmoEntity, ButtonEntity):
    def __init__(self, coordinator, point_id, key, **kwargs):
        super().__init__(coordinator, point_id, key, **kwargs)
        if key == "reboot":
            self._attr_device_class = ButtonDeviceClass.RESTART
            self._attr_entity_category = EntityCategory.CONFIG
        if key.startswith("firmware"):
            self._attr_entity_category = EntityCategory.CONFIG

    @property
    def available(self):
        if not super().available or self.point.get("isOwner") is not True:
            return False
        if self.key == "start":
            return not session_active(self.session) and self.evse.get("status") in START_STATUSES
        if self.key == "stop":
            return (session_active(self.session) and self.session.get("status") != "stopping"
                    and self.session.get("isRemoteStopEnabled") is True
                    and self.session.get("isRemoteStopSupported") is True)
        if self.key == "unlock":
            return self.point.get("is_connector_lock_supported") is True
        if self.key == "reboot":
            return not self.point.get("is_rebooting", False)
        if self.key.startswith("firmware"):
            if self.point.get("isFirmwareUpdatesSupported") is not True:
                return False
            if self.key == "firmware_install":
                return (not self.point.get("isFirmwareUpdating") and
                        not any(session_active(evse.get("session")) for evse in self.point.get("evses", [])))
        return True

    async def async_press(self):
        await self.coordinator.command(self.point_id, self.key, evse_id=self.evse_id)

