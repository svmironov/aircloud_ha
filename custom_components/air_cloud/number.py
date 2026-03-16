from __future__ import annotations

from homeassistant.components.number import RestoreNumber
from homeassistant.const import UnitOfTemperature

from .const import API, CONF_TEMP_ADJUST, CONF_TEMP_STEP, DOMAIN

class AirCloudTempAdjustNumber(RestoreNumber):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_step = 0.5
    _attr_native_min_value = -10.0
    _attr_native_max_value = 10.0

    def __init__(self, api, device: dict, family_id: int, hass) -> None:
        self._api = api
        self._id = device["id"]
        self._name = device["name"]
        self._vendor_id = device["vendorThingId"]
        self._family_id = family_id
        self._hass = hass
        self._attr_unique_id = f"{self._vendor_id}_temp_adjust"
        self._attr_name = "Temperature Adjustment"

    @property
    def device_info(self) -> dict:
        return {
            "identifiers": {(DOMAIN, self._vendor_id)},
            "name": self._name,
            "manufacturer": "Hitachi",
            "model": "AirCloud Climate",
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        self._attr_native_value = last.native_value if last else 0.0
        self._sync_to_hass()

    def _sync_to_hass(self) -> None:
        if DOMAIN in self._hass.data and CONF_TEMP_ADJUST in self._hass.data[DOMAIN]:
            self._hass.data[DOMAIN][CONF_TEMP_ADJUST][self._id] = self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self._sync_to_hass()
        self.async_write_ha_state()

class AirCloudTempStepNumber(RestoreNumber):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_step = 0.5
    _attr_native_min_value = 0.5
    _attr_native_max_value = 1.0

    def __init__(self, api, device: dict, family_id: int, hass) -> None:
        self._api = api
        self._id = device["id"]
        self._name = device["name"]
        self._vendor_id = device["vendorThingId"]
        self._family_id = family_id
        self._hass = hass
        self._attr_unique_id = f"{self._vendor_id}_temp_step"
        self._attr_name = "Temperature Step"

    @property
    def device_info(self) -> dict:
        return {
            "identifiers": {(DOMAIN, self._vendor_id)},
            "name": self._name,
            "manufacturer": "Hitachi",
            "model": "AirCloud Climate",
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        self._attr_native_value = last.native_value if last else 0.5
        self._sync_to_hass()

    def _sync_to_hass(self) -> None:
        if DOMAIN in self._hass.data and CONF_TEMP_STEP in self._hass.data[DOMAIN]:
            self._hass.data[DOMAIN][CONF_TEMP_STEP][self._id] = self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self._sync_to_hass()
        self.async_write_ha_state()

async def async_setup_entry(hass, config_entry, async_add_entities) -> None:
    api = hass.data[DOMAIN][API]
    entities: list = []

    if api._device_cache:
        device_list = [
            (device, family_id)
            for device_id, device in api._device_cache.items()
            for family_id in [api._device_family.get(device_id)]
            if family_id is not None
        ]
    else:
        device_list = []
        for family_id in await api.load_family_ids():
            for device in await api.load_climate_data(family_id):
                device_list.append((device, family_id))

    for device, family_id in device_list:
        entities.append(AirCloudTempAdjustNumber(api, device, family_id, hass))
        entities.append(AirCloudTempStepNumber(api, device, family_id, hass))

    if entities:
        async_add_entities(entities)
