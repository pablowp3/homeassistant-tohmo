"""Poll charger data and validate explicit user commands."""
import asyncio
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AuthenticationError, TohmoClient, TohmoError
from .const import DOMAIN, POLL_SECONDS
from .model import START_STATUSES, session_active, setting_payload

LOGGER = logging.getLogger(__name__)


class TohmoCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: TohmoClient):
        super().__init__(hass, LOGGER, name=DOMAIN, config_entry=entry,
                         update_interval=timedelta(seconds=POLL_SECONDS))
        self.client = client
        self.features: dict = {}
        self._features_loaded = False
        self.command_lock = asyncio.Lock()
        self.firmware_available: dict[str, bool | None] = {}

    async def _async_update_data(self) -> dict:
        try:
            if not self._features_loaded:
                settings = await self.client.global_settings()
                self.features = settings.get("features", {})
                self._features_loaded = True
            return {str(point["id"]): point for point in await self.client.charge_points()}
        except AuthenticationError as error:
            raise ConfigEntryAuthFailed(str(error)) from None
        except TohmoError as error:
            raise UpdateFailed(str(error)) from None

    async def command(self, point_id: str, action: str, *, evse_id: str | None = None,
                      key: str | None = None, value=None) -> None:
        async with self.command_lock:
            # Re-check ownership, state and limits before every explicit command.
            await self.async_refresh()
            if not self.last_update_success:
                raise HomeAssistantError("Cannot verify the current charger state")
            point = self.data.get(point_id)
            if not point or point.get("isOwner") is not True:
                raise HomeAssistantError("Charger ownership is required")
            evse = next((item for item in point.get("evses", []) if str(item.get("id")) == evse_id), None)
            try:
                if action == "setting":
                    await self.client.update_point(point["id"], setting_payload(point, self.features, key, value))
                elif action == "reboot":
                    if point.get("is_rebooting"):
                        raise TohmoError("Charger is already restarting")
                    await self.client.reboot(point["id"])
                elif action in {"start", "stop", "unlock"}:
                    if not evse:
                        raise TohmoError("Connector is no longer present")
                    session = evse.get("session")
                    if action == "start":
                        if session_active(session):
                            raise TohmoError("A charging session is already active")
                        if evse.get("status") not in START_STATUSES:
                            raise TohmoError("Connector is not ready to start")
                        await self.client.start(evse["id"])
                    elif action == "stop":
                        if not session_active(session) or session.get("isRemoteStopSupported") is not True or session.get("isRemoteStopEnabled") is not True:
                            raise TohmoError("Remote stop is not currently available")
                        if session.get("status") == "stopping":
                            raise TohmoError("Session is already stopping")
                        await self.client.stop(session["id"])
                    else:
                        if point.get("is_connector_lock_supported") is not True:
                            raise TohmoError("Connector unlocking is not supported")
                        await self.client.unlock(point["id"], evse["id"])
                elif action in {"firmware_check", "firmware_install"}:
                    if point.get("isFirmwareUpdatesSupported") is not True:
                        raise TohmoError("Firmware updates are not supported")
                    # APK treats a successful check as an available update.
                    # A failed check is left unknown, never presented as up to date.
                    self.firmware_available[point_id] = None
                    self.async_update_listeners()
                    await self.client.firmware_check(point["id"])
                    self.firmware_available[point_id] = True
                    self.async_update_listeners()
                    if action == "firmware_install":
                        if point.get("isFirmwareUpdating") or any(session_active(item.get("session")) for item in point.get("evses", [])):
                            raise TohmoError("Stop charging and wait for any update to finish before installing firmware")
                        await self.client.firmware_install(point["id"])
                        self.firmware_available[point_id] = None
                else:
                    raise TohmoError("Unsupported charger command")
            except AuthenticationError as error:
                self.config_entry.async_start_reauth(self.hass)
                raise HomeAssistantError(str(error)) from None
            except TohmoError as error:
                raise HomeAssistantError(str(error)) from None
            await self.async_request_refresh()

