from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy
from .const import API, DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(hours=1)


async def _build_entities(hass) -> list[AirCloudEnergySensor]:
    api = hass.data[DOMAIN][API]
    entities: list[AirCloudEnergySensor] = []
    seen_vendor_ids: set[str] = set()
    family_ids = await api.load_family_ids()

    for family_id in family_ids:
        data = await api.load_energy_consumption_summary(family_id)
        racs_data = data.get("individualRacsData") or []
        for rac_data in racs_data:
            vendor_id = rac_data.get("vendorThingId")
            if vendor_id and vendor_id not in seen_vendor_ids:
                seen_vendor_ids.add(vendor_id)
                entities.append(AirCloudEnergySensor(api, rac_data, family_id, data))

        # Fallback if summary had no individual RACs data at setup time:
        # Check all/racs to see if user has selected RACs for energy monitoring
        if not seen_vendor_ids:
            try:
                all_racs = await api.load_energy_all_racs(family_id)
                selected_rac_ids = {
                    rac["racId"]
                    for rac in all_racs
                    if rac.get("isSelected", False) or rac.get("isEnergyConsumptionSupported", False)
                }
                if selected_rac_ids:
                    devices = await api.load_climate_data(family_id)
                    for device in devices:
                        if device.get("id") in selected_rac_ids:
                            vendor_id = device.get("vendorThingId")
                            if vendor_id and vendor_id not in seen_vendor_ids:
                                seen_vendor_ids.add(vendor_id)
                                fallback_rac_data = {
                                    "vendorThingId": vendor_id,
                                    "racName": device.get("name", "AirCloud"),
                                    "energyConsumed": None,
                                    "racId": device.get("id"),
                                }
                                entities.append(
                                    AirCloudEnergySensor(api, fallback_rac_data, family_id, data)
                                )
            except Exception as exc:
                _LOGGER.debug(
                    "AirCloud: fallback RAC energy discovery failed for family %s: %s",
                    family_id,
                    exc,
                )

    return entities


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    entities = await _build_entities(hass)
    if entities:
        async_add_entities(entities)


async def async_setup_entry(hass, config_entry, async_add_entities):
    entities = await _build_entities(hass)
    if entities:
        async_add_entities(entities)


class AirCloudEnergySensor(SensorEntity):
    def __init__(
        self,
        api,
        rac_data: dict[str, Any],
        family_id: int,
        summary_data: dict[str, Any] | None = None,
    ) -> None:
        self._api = api
        self._family_id = family_id
        self._vendor_id: str = rac_data.get("vendorThingId", "")
        self._rac_name: str = rac_data.get("racName", "AirCloud")
        self._attr_native_value: float | None = None
        if rac_data.get("energyConsumed") is not None:
            try:
                self._attr_native_value = float(rac_data["energyConsumed"])
            except (ValueError, TypeError):
                self._attr_native_value = None

        self._cost: float | None = rac_data.get("cost")
        all_racs = (summary_data or {}).get("allRacsData") or {}
        self._currency: str | None = all_racs.get("currency")
        self._period_from: str | None = (summary_data or {}).get("from")
        self._period_to: str | None = (summary_data or {}).get("to")

        self._attr_unique_id = f"{self._vendor_id}_energy"
        self._attr_name = f"{self._rac_name} Energy Consumption"

    @property
    def native_value(self) -> float | None:
        return self._attr_native_value

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vendor_id)},
            "name": self._rac_name,
            "manufacturer": "Hitachi",
            "model": "AirCloud Climate",
        }

    @property
    def device_class(self) -> SensorDeviceClass:
        return SensorDeviceClass.ENERGY

    @property
    def state_class(self) -> SensorStateClass:
        return SensorStateClass.TOTAL_INCREASING

    @property
    def native_unit_of_measurement(self) -> str:
        return UnitOfEnergy.KILO_WATT_HOUR

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "family_id": self._family_id,
        }
        if self._cost is not None:
            attrs["cost"] = self._cost
        if self._currency:
            attrs["currency"] = self._currency
        if self._period_from:
            attrs["period_from"] = self._period_from
        if self._period_to:
            attrs["period_to"] = self._period_to
        return attrs

    async def async_update(self) -> None:
        data = await self._api.load_energy_consumption_summary(self._family_id)
        racs_data = data.get("individualRacsData") or []
        for rac in racs_data:
            if rac.get("vendorThingId") == self._vendor_id:
                if rac.get("energyConsumed") is not None:
                    try:
                        self._attr_native_value = float(rac["energyConsumed"])
                    except (ValueError, TypeError):
                        self._attr_native_value = None
                if "cost" in rac:
                    self._cost = rac["cost"]
                all_racs = data.get("allRacsData") or {}
                if "currency" in all_racs:
                    self._currency = all_racs["currency"]
                self._period_from = data.get("from")
                self._period_to = data.get("to")
                break
