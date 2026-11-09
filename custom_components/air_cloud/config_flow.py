from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import (
    DOMAIN, CONF_EMAIL, CONF_PASSWORD, CONFIG_FLOW_SCHEMA,
    CONF_LEGACY_RAC_OFF_DEVICE_IDS, CONF_COMMAND_DELAY, DEFAULT_COMMAND_DELAY,
)
from .api import AirCloudApi


class AirCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return AirCloudOptionsFlow()

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            login = (user_input.get(CONF_EMAIL) or "").strip()
            password = (user_input.get(CONF_PASSWORD) or "").strip()
            sanitized_input = {**user_input, CONF_EMAIL: login, CONF_PASSWORD: password}

            api = AirCloudApi(login, password)
            try:
                valid = await api.validate_credentials()
            finally:
                await api.close_session()

            if valid:
                return self.async_create_entry(title=login, data=sanitized_input)

            return self.async_show_form(
                step_id="user",
                data_schema=self.user_schema,
                errors={"base": "invalid_auth"}
            )

        return self.async_show_form(
            step_id="user",
            data_schema=self.user_schema
        )

    @property
    def user_schema(self):
        return CONFIG_FLOW_SCHEMA


class AirCloudOptionsFlow(config_entries.OptionsFlow):
    """Select affected devices and command delay; no compatibility mode is enabled by default."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            options = {**self.config_entry.options, CONF_LEGACY_RAC_OFF_DEVICE_IDS: [
                int(device_id) for device_id in user_input.get(CONF_LEGACY_RAC_OFF_DEVICE_IDS, [])
            ]}
            if CONF_COMMAND_DELAY in user_input:
                options[CONF_COMMAND_DELAY] = int(user_input[CONF_COMMAND_DELAY])
            return self.async_create_entry(title="", data=options)

        api = getattr(self.config_entry, "runtime_data", None)
        choices = api.get_rac_device_options() if api is not None else {}
        selected = [str(device_id) for device_id in
                    self.config_entry.options.get(CONF_LEGACY_RAC_OFF_DEVICE_IDS, [])]
        for device_id in selected:
            choices.setdefault(device_id, device_id)
        current_delay = self.config_entry.options.get(CONF_COMMAND_DELAY, DEFAULT_COMMAND_DELAY)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_LEGACY_RAC_OFF_DEVICE_IDS, default=selected): cv.multi_select(choices),
                vol.Optional(CONF_COMMAND_DELAY, default=current_delay): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=120)
                ),
            }),
        )
