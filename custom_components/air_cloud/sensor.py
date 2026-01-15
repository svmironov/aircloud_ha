import logging
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy
from .const import DOMAIN, API

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    api = hass.data[DOMAIN][API]
    entities = []
    family_ids = await api.load_family_ids()
    for family_id in family_ids:
        # Initial fetch to discover devices
        data = await api.load_energy_consumption_summary(family_id)
        if "individualRacsData" in data:
            for rac_data in data["individualRacsData"]:
                 entities.append(AirCloudEnergySensor(api, rac_data, family_id))
    
    if entities:
        async_add_entities(entities)

class AirCloudEnergySensor(SensorEntity):
    def __init__(self, api, rac_data, family_id):
        self._api = api
        self._family_id = family_id
        self._vendor_id = rac_data["vendorThingId"]
        self._rac_name = rac_data["racName"]
        self._attr_native_value = rac_data["energyConsumed"]
        self._attr_unique_id = f"{self._vendor_id}_energy"
        self._attr_name = f"{self._rac_name} Energy Consumption"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._vendor_id)},
            "name": self._rac_name,
            "manufacturer": "Hitachi",
            "model": "AirCloud Climate",
        }

    @property
    def device_class(self):
        return SensorDeviceClass.ENERGY

    @property
    def state_class(self):
        return SensorStateClass.TOTAL_INCREASING

    @property
    def native_unit_of_measurement(self):
        return UnitOfEnergy.KILO_WATT_HOUR

    async def async_update(self):
        data = await self._api.load_energy_consumption_summary(self._family_id)
        if "individualRacsData" in data:
             for rac in data["individualRacsData"]:
                 if rac["vendorThingId"] == self._vendor_id:
                     self._attr_native_value = rac["energyConsumed"]
                     break
