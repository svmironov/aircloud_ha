import asyncio
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (FAN_AUTO, FAN_HIGH,
                                                    FAN_LOW, FAN_MEDIUM,
                                                    FAN_MIDDLE, SWING_OFF,
                                                    SWING_VERTICAL,
                                                    SWING_HORIZONTAL,
                                                    SWING_BOTH)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.components.climate.const import HVACMode, ClimateEntityFeature

from .const import DOMAIN, API, CONF_TEMP_ADJUST

SUPPORT_FAN = [
    FAN_AUTO,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_MIDDLE,
    FAN_HIGH
]
SUPPORT_SWING = [
    SWING_OFF,
    SWING_VERTICAL,
    SWING_HORIZONTAL,
    SWING_BOTH
]
SUPPORT_HVAC = [
    HVACMode.OFF,
    HVACMode.COOL,
    HVACMode.DRY,
    HVACMode.FAN_ONLY,
    HVACMode.AUTO,
    HVACMode.HEAT
]
NO_HUMIDITY_VALUE = 2147483647


async def _async_setup(hass, async_add):
    api = hass.data[DOMAIN][API]
    temp_adjust = hass.data[DOMAIN][CONF_TEMP_ADJUST]

    family_ids = await api.load_family_ids()
    for family_id in family_ids:
        family_devices = await api.load_climate_data(family_id)
        for device in family_devices:
            async_add([AirCloudClimateEntity(api, device, hass, family_id)], update_before_add=False)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    await _async_setup(hass, async_add_entities)


async def async_setup_entry(hass, config_entry, async_add_devices):
    api = hass.data[DOMAIN][API]
    entities = []
    family_ids = await api.load_family_ids()
    for family_id in family_ids:
        family_devices = await api.load_climate_data(family_id)
        for device in family_devices:
            entities.append(AirCloudClimateEntity(api, device, hass, family_id))

    if entities:
        async_add_devices(entities)


class AirCloudClimateEntity(ClimateEntity):
    _enable_turn_on_off_backwards_compatibility = False
    _attr_has_entity_name = True

    def __init__(self, api, device, hass, family_id):
        self._target_temp = 0
        self._api = api
        self._hass = hass
        self._id = device["id"]
        self._name = device["name"]
        self._vendor_id = device["vendorThingId"]
        self._update_lock = False
        self._family_id = family_id
        self.__update_data(device)

    @property
    def unique_id(self):
        return self._vendor_id

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._vendor_id)},
            "name": self._name,
            "manufacturer": "Hitachi",
            "model": "AirCloud Climate",
        }

    @property
    def extra_state_attributes(self):
        return {"family_id": self._family_id, "air_cloud_id": self._id}

    @property
    def supported_features(self):
        support_flags = (ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
                         | ClimateEntityFeature.SWING_MODE | ClimateEntityFeature.TURN_ON
                         | ClimateEntityFeature.TURN_OFF)
        return support_flags

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self):
        return self._room_temp

    @property
    def target_temperature(self):
        return self._target_temp

    @property
    def target_temperature_step(self):
        return 0.5

    @property
    def max_temp(self):
        return 32.0

    @property
    def min_temp(self):
        return 16.0

    @property
    def name(self):
        return self._name

    @property
    def hvac_mode(self):
        if self._power == "OFF":
            return HVACMode.OFF
        elif self._mode == "COOLING":
            return HVACMode.COOL
        elif self._mode == "HEATING":
            return HVACMode.HEAT
        elif self._mode == "FAN":
            return HVACMode.FAN_ONLY
        elif self._mode == "DRY":
            return HVACMode.DRY
        elif self._mode == "AUTO":
            return HVACMode.AUTO
        else:
            return HVACMode.OFF

    @property
    def hvac_modes(self):
        return SUPPORT_HVAC

    @property
    def fan_mode(self):
        if self._fan_speed == "AUTO":
            return FAN_AUTO
        elif self._fan_speed == "LV1":
            return FAN_LOW
        elif self._fan_speed == "LV2":
            return FAN_MEDIUM
        elif self._fan_speed == "LV3":
            return FAN_MIDDLE
        elif self._fan_speed == "LV4":
            return FAN_HIGH
        else:
            return FAN_AUTO

    @property
    def fan_modes(self):
        return SUPPORT_FAN

    @property
    def swing_mode(self):
        if self._fan_swing == "VERTICAL":
            return SWING_VERTICAL
        elif self._fan_swing == "HORIZONTAL":
            return SWING_HORIZONTAL
        elif self._fan_swing == "BOTH":
            return SWING_VERTICAL
        else:
            return SWING_OFF

    @property
    def swing_modes(self):
        return SUPPORT_SWING

    def turn_on(self):
        asyncio.run(self.async_turn_on())

    def turn_off(self):
        asyncio.run(self.async_turn_off())

    def set_hvac_mode(self, hvac_mode):
        asyncio.run(self.async_set_hvac_mode(hvac_mode))

    def set_preset_mode(self, preset_mode):
        asyncio.run(self.async_set_preset_mode(preset_mode))

    def set_fan_mode(self, fan_mode):
        asyncio.run(self.async_set_fan_mode(fan_mode))

    def set_swing_mode(self, swing_mode):
        asyncio.run(self.async_set_swing_mode(swing_mode))

    def set_temperature(self, **kwargs):
        asyncio.run(self.async_set_temperature(**kwargs))

    def update(self):
        asyncio.run(self.async_update())

    async def async_turn_on(self):
        self._power = "ON"
        await self.__execute_command()

    async def async_turn_off(self):
        self._power = "OFF"
        await self.__execute_command()

    async def async_set_hvac_mode(self, hvac_mode):
        self._update_lock = True

        if hvac_mode != HVACMode.OFF:
            self._power = "ON"

        if hvac_mode == HVACMode.OFF:
            self._power = "OFF"
        elif hvac_mode == HVACMode.COOL:
            self._mode = "COOLING"
        elif hvac_mode == HVACMode.DRY:
            self._mode = "DRY"
        elif hvac_mode == HVACMode.FAN_ONLY:
            self._mode = "FAN"
        elif hvac_mode == HVACMode.AUTO:
            self._mode = "AUTO"
        elif hvac_mode == HVACMode.HEAT:
            self._mode = "HEATING"
        else:
            self._power = "OFF"

        await self.__execute_command()

    async def async_set_preset_mode(self, preset_mode):
        await self.__execute_command()

    async def async_set_fan_mode(self, fan_mode):
        self._update_lock = True

        if fan_mode == FAN_AUTO:
            self._fan_speed = "AUTO"
        elif fan_mode == FAN_LOW:
            self._fan_speed = "LV1"
        elif fan_mode == FAN_MIDDLE:
            self._fan_speed = "LV2"
        elif fan_mode == FAN_MEDIUM:
            self._fan_speed = "LV3"
        elif fan_mode == FAN_HIGH:
            self._fan_speed = "LV4"
        else:
            self._fan_speed = "AUTO"

        await self.__execute_command()

    async def async_set_swing_mode(self, swing_mode):
        self._update_lock = True

        if swing_mode == SWING_VERTICAL:
            self._fan_swing = "VERTICAL"
        elif swing_mode == SWING_HORIZONTAL:
            self._fan_swing = "HORIZONTAL"
        elif swing_mode == SWING_BOTH:
            self._fan_swing = "BOTH"
        else:
            self._fan_swing = "OFF"

        await self.__execute_command()

    async def async_set_temperature(self, **kwargs):
        self._update_lock = True

        target_temp = kwargs.get(ATTR_TEMPERATURE)
        if target_temp is None:
            return

        self._target_temp = target_temp
        await self.__execute_command()

    async def async_update(self):
        if self._update_lock is False:
            try:
                devices = await asyncio.wait_for(self._api.load_climate_data(self._family_id), timeout=10)
                for device in devices:
                    if self._id == device["id"]:
                        self.__update_data(device)
            except asyncio.TimeoutError:
                pass

    async def __execute_command(self):
        target_temp = self._target_temp

        if self._mode == "FAN":
            target_temp = 0

        await self._api.execute_command(self._id, self._family_id, self._power, target_temp, self._mode,
                                        self._fan_speed, self._fan_swing, self._humidity)
        await asyncio.sleep(10)
        self._update_lock = False
        await self.async_update()

    def __update_data(self, climate_data):
        self._power = climate_data["power"]
        self._mode = climate_data["mode"]
        self._target_temp = climate_data["iduTemperature"]

        self._room_temp = climate_data["roomTemperature"]

        # Get adjustment from shared data
        adjust_data = self._hass.data[DOMAIN].get(CONF_TEMP_ADJUST, {})
        temp_adjust = adjust_data.get(self._id)

        if temp_adjust is None:
            temp_adjust = 0.0

        self._room_temp = climate_data.get("roomTemperature")

        if self._room_temp is not None:
            self._room_temp = self._room_temp + temp_adjust

        self._fan_speed = climate_data["fanSpeed"]
        self._fan_swing = climate_data["fanSwing"]

        self._humidity = climate_data.get("humidity", 0)
        if self._humidity < NO_HUMIDITY_VALUE:
            self._humidity = 50
        elif self._humidity == NO_HUMIDITY_VALUE:
            self._humidity = 0
