from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .api import AirCloudApi
from .const import (
    API,
    ARG_FAMILY_ID,
    ARG_FAN_SPEED,
    ARG_FAN_SWING,
    ARG_HUMIDITY,
    ARG_ID,
    ARG_MODE,
    ARG_POWER,
    ARG_TARGET_TEMP,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_TEMP_ADJUST,
    CONF_TEMP_STEP,
    DOMAIN,
    PLATFORM_BINARY_SENSOR,
    PLATFORM_BUTTON,
    PLATFORM_CLIMATE,
    PLATFORM_NUMBER,
    PLATFORM_SENSOR,
    SERVICE_EXEC_COMMAND,
    SERVICE_EXEC_COMMAND_DATA_SCHEMA,
)

PLATFORMS = [PLATFORM_BINARY_SENSOR, PLATFORM_BUTTON, PLATFORM_CLIMATE, PLATFORM_NUMBER, PLATFORM_SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api = AirCloudApi(entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
    hass.data[DOMAIN] = {
        API: api,
        CONF_TEMP_ADJUST: {},
        CONF_TEMP_STEP: {},
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    conf = config.get(DOMAIN)
    if conf:
        api = AirCloudApi(conf.get(CONF_EMAIL, ""), conf.get(CONF_PASSWORD, ""))
        hass.data[DOMAIN] = {
            API: api,
            CONF_TEMP_ADJUST: {},
            CONF_TEMP_STEP: {},
        }

    async def _service_exec_command(call: ServiceCall) -> None:
        await hass.data[DOMAIN][API].execute_command(
            call.data[ARG_ID],
            call.data[ARG_FAMILY_ID],
            call.data[ARG_POWER],
            call.data[ARG_TARGET_TEMP],
            call.data[ARG_MODE],
            call.data[ARG_FAN_SPEED],
            call.data[ARG_FAN_SWING],
            call.data[ARG_HUMIDITY],
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_EXEC_COMMAND,
        _service_exec_command,
        schema=SERVICE_EXEC_COMMAND_DATA_SCHEMA,
    )
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await hass.data[DOMAIN][API].close_session()
        hass.data.pop(DOMAIN)
    return unload_ok
