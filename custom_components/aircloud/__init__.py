from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORM_CLIMATE, API, CONF_EMAIL, CONF_PASSWORD
from .api import AirCloudApi


async def async_setup(hass: HomeAssistant, config: dict):
    conf = config.get(DOMAIN)

    if conf:
        hass.data[DOMAIN][API] = AirCloudApi(config[DOMAIN].get(CONF_EMAIL),  config[DOMAIN].get(CONF_PASSWORD))

        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, data=conf, context={"source": SOURCE_IMPORT}
            )
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, PLATFORM_CLIMATE)
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    return await hass.config_entries.async_forward_entry_unload(entry, PLATFORM_CLIMATE)
