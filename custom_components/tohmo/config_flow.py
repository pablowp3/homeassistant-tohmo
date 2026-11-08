"""Sign in with the same account used by the Android app."""
import hashlib

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import AuthenticationError, TohmoClient, TohmoError
from .const import DOMAIN


class TohmoConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        return await self._login(user_input, reauth=False)

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        return await self._login(user_input, reauth=True)

    async def _login(self, user_input, *, reauth):
        errors = {}
        entry = self._get_reauth_entry() if reauth else None
        if user_input is not None:
            username = (entry.data[CONF_USERNAME] if entry else user_input[CONF_USERNAME]).strip().lower()
            client = TohmoClient(async_get_clientsession(self.hass))
            try:
                await client.login(username, user_input[CONF_PASSWORD])
                points = await client.charge_points()
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except TohmoError:
                errors["base"] = "cannot_connect"
            else:
                if not points:
                    errors["base"] = "no_chargers"
                else:
                    unique_id = hashlib.sha256(username.encode()).hexdigest()
                    await self.async_set_unique_id(unique_id)
                    data = {CONF_USERNAME: username, "tokens": client.tokens}
                    if entry:
                        self._abort_if_unique_id_mismatch()
                        return self.async_update_reload_and_abort(entry, data_updates=data)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(title="Tohmo", data=data)
        fields = {}
        if not reauth:
            fields[vol.Required(CONF_USERNAME)] = TextSelector(TextSelectorConfig(type=TextSelectorType.EMAIL))
        fields[vol.Required(CONF_PASSWORD)] = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
        return self.async_show_form(step_id="reauth_confirm" if reauth else "user",
                                    data_schema=vol.Schema(fields), errors=errors)

