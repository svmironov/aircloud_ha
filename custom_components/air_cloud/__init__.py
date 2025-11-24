from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (DOMAIN, PLATFORM_CLIMATE, PLATFORM_NUMBER, API, CONF_EMAIL, CONF_PASSWORD,
                    CONF_TEMP_ADJUST, SERVICE_EXEC_COMMAND, SERVICE_EXEC_COMMAND_DATA_SCHEMA,
                    ARG_ID, ARG_FAMILY_ID, ARG_POWER, ARG_TARGET_TEMP, ARG_MODE,
                    ARG_FAN_SPEED, ARG_FAN_SWING, ARG_HUMIDITY)
from .api import AirCloudApi

PLATFORMS = [PLATFORM_CLIMATE, PLATFORM_NUMBER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    login = entry.data.get(CONF_EMAIL)
    password = entry.data.get(CONF_PASSWORD)
    temp_adjust = entry.data.get(CONF_TEMP_ADJUST)

    api = AirCloudApi(login, password)
    hass.data[DOMAIN] = {API: api, CONF_TEMP_ADJUST: {}}
    if temp_adjust is not None:
         hass.data[DOMAIN][CONF_TEMP_ADJUST]["global"] = temp_adjust

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_setup(hass: HomeAssistant, config: dict):
    conf = config.get(DOMAIN)

    if conf:
        login = config[DOMAIN].get(CONF_EMAIL)
        password = config[DOMAIN].get(CONF_PASSWORD)
        temp_adjust = config[DOMAIN].get(CONF_TEMP_ADJUST)

        api = AirCloudApi(login, password)
        hass.data[DOMAIN] = {API: api, CONF_TEMP_ADJUST: {}}
        if temp_adjust is not None:
             hass.data[DOMAIN][CONF_TEMP_ADJUST]["global"] = temp_adjust

    async def service_exec_command(service_call):
        service_data = service_call.data
        await hass.data[DOMAIN][API].execute_command(service_data[ARG_ID],
                                                     service_data[ARG_FAMILY_ID],
                                                     service_data[ARG_POWER],
                                                     service_data[ARG_TARGET_TEMP],
                                                     service_data[ARG_MODE],
                                                     service_data[ARG_FAN_SPEED],
                                                     service_data[ARG_FAN_SWING],
                                                     service_data[ARG_HUMIDITY])

    hass.services.async_register(
        DOMAIN,
        SERVICE_EXEC_COMMAND,
        service_exec_command,
        schema=SERVICE_EXEC_COMMAND_DATA_SCHEMA,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.data[DOMAIN][API].close_session()
    return await hass.config_entries.async_forward_entry_unload(entry, PLATFORMS)
