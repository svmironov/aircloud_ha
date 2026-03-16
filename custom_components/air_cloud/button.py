from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity

from .const import API, DOMAIN

_LOGGER = logging.getLogger(__name__)

class AirCloudFrostWashButton(ButtonEntity):

    _attr_has_entity_name = True
    _attr_device_class = ButtonDeviceClass.UPDATE

    def __init__(self, api, device: dict[str, Any], family_id: int) -> None:
        self._api = api
        self._device_id = device["id"]
        self._name = device["name"]
        self._vendor_id = device["vendorThingId"]
        self._family_id = family_id

        self._attr_unique_id = f"{self._vendor_id}_frost_wash_indoor"
        self._attr_name = "Start Indoor FrostWash"

    @property
    def device_info(self) -> dict:
        return {
            "identifiers": {(DOMAIN, self._vendor_id)},
            "name": self._name,
            "manufacturer": "Hitachi",
            "model": "AirCloud Climate",
        }

    async def async_press(self) -> None:
        _LOGGER.debug("AirCloud: Triggering FrostWash for device %s", self._device_id)
        await self._api.execute_frost_wash(self._device_id, self._family_id)

async def async_setup_entry(hass, config_entry, async_add_entities) -> None:
    api = hass.data[DOMAIN][API]
    entities: list[ButtonEntity] = []

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
        # Check if FrostWash is supported by the device
        if device.get("iduFrostWash", False) or "iduFrostWashStatus" in device:
            entities.append(AirCloudFrostWashButton(api, device, family_id))

    if entities:
        async_add_entities(entities)
