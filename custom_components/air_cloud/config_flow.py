import asyncio
import logging

import aiohttp
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import (
    DOMAIN, CONF_EMAIL, CONF_PASSWORD, CONFIG_FLOW_SCHEMA,
    CONF_LEGACY_RAC_OFF_DEVICE_IDS,
)
from .api import AirCloudApi, AirCloudAuthenticationError

_LOGGER = logging.getLogger(__name__)

_LOGIN_ERRORS = {
    401: "invalid_auth",
    403: "account_disabled",
    412: "account_unverified",
    423: "account_locked",
    429: "too_many_attempts",
}


class AirCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return AirCloudOptionsFlow()

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            login = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]

            api = AirCloudApi(login, password)
            try:
                await api.validate_credentials(raise_on_error=True)
            except aiohttp.ClientResponseError as exc:
                error = _LOGIN_ERRORS.get(exc.status, "cannot_connect")
                _LOGGER.warning("AirCloud: sign-in failed (HTTP %s)", exc.status)
            except (aiohttp.ClientError, asyncio.TimeoutError):
                error = "cannot_connect"
                _LOGGER.warning("AirCloud: could not connect during sign-in")
            except AirCloudAuthenticationError:
                error = "unknown"
                _LOGGER.warning("AirCloud: sign-in returned an invalid authentication response")
            except Exception:
                error = "unknown"
                _LOGGER.error("AirCloud: unexpected error during sign-in")
            else:
                return self.async_create_entry(title=login.strip(), data=user_input)
            finally:
                await api.close_session()

            return self.async_show_form(
                step_id="user",
                data_schema=self.user_schema,
                errors={"base": error}
            )

        return self.async_show_form(
            step_id="user",
            data_schema=self.user_schema
        )

    @property
    def user_schema(self):
        return CONFIG_FLOW_SCHEMA


class AirCloudOptionsFlow(config_entries.OptionsFlow):
    """Select affected devices; no compatibility mode is enabled by default."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            options = {**self.config_entry.options, CONF_LEGACY_RAC_OFF_DEVICE_IDS: [
                int(device_id) for device_id in user_input.get(CONF_LEGACY_RAC_OFF_DEVICE_IDS, [])
            ]}
            return self.async_create_entry(title="", data=options)

        api = getattr(self.config_entry, "runtime_data", None)
        choices = api.get_rac_device_options() if api is not None else {}
        selected = [str(device_id) for device_id in
                    self.config_entry.options.get(CONF_LEGACY_RAC_OFF_DEVICE_IDS, [])]
        for device_id in selected:
            choices.setdefault(device_id, device_id)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_LEGACY_RAC_OFF_DEVICE_IDS, default=selected): cv.multi_select(choices)
            }),
        )
