from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORM_CLIMATE, API, CONF_EMAIL, CONF_PASSWORD, CONF_TEMP_ADJUST
from .api import AirCloudApi


async def async_setup(hass: HomeAssistant, config: dict):
    conf = config.get(DOMAIN)
    login = config[DOMAIN].get(CONF_EMAIL)
    password = config[DOMAIN].get(CONF_PASSWORD)
    temp_adjust = config[DOMAIN].get(CONF_TEMP_ADJUST)

    if conf:
        hass.data[DOMAIN] = {}
        hass.data[DOMAIN][API] = AirCloudApi(login, password)
        hass.data[DOMAIN][CONF_TEMP_ADJUST] = temp_adjust

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, PLATFORM_CLIMATE)
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    return await hass.config_entries.async_forward_entry_unload(entry, PLATFORM_CLIMATE)
