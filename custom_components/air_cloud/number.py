from homeassistant.components.number import RestoreNumber
from homeassistant.const import UnitOfTemperature
from .const import DOMAIN, API, CONF_TEMP_ADJUST

class AirCloudTempAdjustNumber(RestoreNumber):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_step = 0.5
    _attr_native_min_value = -10.0
    _attr_native_max_value = 10.0

    def __init__(self, api, device, family_id, hass):
        self._api = api
        self._id = device["id"]
        self._name = device["name"]
        self._vendor_id = device["vendorThingId"]
        self._family_id = family_id
        self._hass = hass
        self._attr_unique_id = f"{self._vendor_id}_temp_adjust"
        self._attr_name = "Temperature Adjustment"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._vendor_id)},
            "name": self._name,
            "manufacturer": "Hitachi",
            "model": "AirCloud Climate",
        }

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last_state = await self.async_get_last_number_data()
        if last_state:
            self._attr_native_value = last_state.native_value
        else:
            self._attr_native_value = 0.0
        
        self._update_shared_data()

    def _update_shared_data(self):
        if DOMAIN in self._hass.data and CONF_TEMP_ADJUST in self._hass.data[DOMAIN]:
             self._hass.data[DOMAIN][CONF_TEMP_ADJUST][self._id] = self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self._update_shared_data()
        self.async_write_ha_state()

async def async_setup_entry(hass, config_entry, async_add_entities):
    api = hass.data[DOMAIN][API]
    
    entities = []
    family_ids = await api.load_family_ids()
    for family_id in family_ids:
        family_devices = await api.load_climate_data(family_id)
        for device in family_devices:
            entities.append(AirCloudTempAdjustNumber(api, device, family_id, hass))

    if entities:
        async_add_entities(entities)
