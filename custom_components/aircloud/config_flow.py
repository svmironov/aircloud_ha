from homeassistant import config_entries
from .const import DOMAIN, CONF_EMAIL, CONF_PASSWORD, CONF_TEMP_ADJUST, CONFIG_FLOW_SCHEMA
from .api import AirCloudApi


class AirCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            login = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]
            temp_adjust = user_input.get(CONF_TEMP_ADJUST)

            if await AirCloudApi(login, password).validate_credentials():
                return self.async_create_entry(title=login, data=user_input)

            return self.async_show_form(
                step_id="user",
                data_schema=self.user_schema,
                errors={"base": "invalid_credentials"}
            )

        return self.async_show_form(
            step_id="user",
            data_schema=self.user_schema
        )

    @property
    def user_schema(self):
        return CONFIG_FLOW_SCHEMA
