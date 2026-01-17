import asyncio
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (FAN_AUTO, SWING_OFF,
                                                    SWING_VERTICAL,
                                                    SWING_HORIZONTAL,
                                                    SWING_BOTH)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.components.climate.const import HVACMode, ClimateEntityFeature

from .const import DOMAIN, API, CONF_TEMP_ADJUST, CONF_TEMP_STEP

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
    
    cloud_ids = []
    all_devices = []

    for family_id in family_ids:
        family_devices = await api.load_climate_data(family_id)
        for device in family_devices:
             cloud_ids.append(device["cloudId"])
             all_devices.append((device, family_id))
    
    if cloud_ids:
        rac_configs = await api.load_rac_configuration(cloud_ids)
        rac_config_map = {config["cloudId"]: config for config in rac_configs}

        for device, family_id in all_devices:
            rac_config = rac_config_map.get(device["cloudId"])
            entities.append(AirCloudClimateEntity(api, device, hass, family_id, rac_config))

    if entities:
        async_add_devices(entities)


class AirCloudClimateEntity(ClimateEntity):
    _enable_turn_on_off_backwards_compatibility = False
    _attr_has_entity_name = True

    def __init__(self, api, device, hass, family_id, rac_config):
        self._target_temp = 0
        self._api = api
        self._hass = hass
        self._id = device["id"]
        self._name = device["name"]
        self._vendor_id = device["vendorThingId"]
        self._cloud_id = device["cloudId"]
        self._update_lock = False
        self._family_id = family_id
        self._temp_limits = {}
        self.__update_data(device)
        self._update_capabilities(rac_config)

    def _update_capabilities(self, rac_config):
        self._attr_hvac_modes = [HVACMode.OFF]
        self._attr_fan_modes = [FAN_AUTO]
        self._attr_swing_modes = [SWING_OFF]

        if not rac_config:
            return

        # HVAC Modes
        for mode_data in rac_config.get("racOperationModes", []):
            mode = mode_data.get("mode")
            self._temp_limits[mode] = {
                "min": mode_data.get("minTemperature", 16.0),
                "max": mode_data.get("maxTemperature", 32.0)
            }
            if mode == "COOLING":
                self._attr_hvac_modes.append(HVACMode.COOL)
            elif mode == "HEATING":
                self._attr_hvac_modes.append(HVACMode.HEAT)
            elif mode == "DRY":
                self._attr_hvac_modes.append(HVACMode.DRY)
            elif mode == "FAN":
                self._attr_hvac_modes.append(HVACMode.FAN_ONLY)
            elif mode == "AUTO":
                self._attr_hvac_modes.append(HVACMode.AUTO)

        # Swing Modes
        swing_config = rac_config.get("swing", {})
        vertical = swing_config.get("VERTICAL", False)
        horizontal = swing_config.get("HORIZONTAL", False)
        
        if vertical:
            self._attr_swing_modes.append(SWING_VERTICAL)
        if horizontal:
            self._attr_swing_modes.append(SWING_HORIZONTAL)
        if vertical and horizontal:
             self._attr_swing_modes.append(SWING_BOTH)

        # Fan Modes
        available_speeds = set()
        for mode_data in rac_config.get("racOperationModes", []):
             enable_fan = mode_data.get("enableFanSpeed", {})
             for speed, enabled in enable_fan.items():
                 if enabled:
                     available_speeds.add(speed)
        
        if "LV1" in available_speeds:
            self._attr_fan_modes.append("Level 1")
        if "LV2" in available_speeds:
             self._attr_fan_modes.append("Level 2")
        if "LV3" in available_speeds:
             self._attr_fan_modes.append("Level 3")
        if "LV4" in available_speeds:
             self._attr_fan_modes.append("Level 4")
        if "LV5" in available_speeds:
             self._attr_fan_modes.append("Level 5")

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
        return {"family_id": self._family_id, "air_cloud_id": self._id, "cloud_id": self._cloud_id}

    @property
    def supported_features(self):
        support_flags = (ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
                         | ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF)
        
        if len(self._attr_swing_modes) > 1:
             support_flags |= ClimateEntityFeature.SWING_MODE
             
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
        step_data = self._hass.data[DOMAIN].get(CONF_TEMP_STEP, {})
        step = step_data.get(self._id)
        if step is None:
            return 0.5
        return step

    @property
    def max_temp(self):
        return self._temp_limits.get(self._mode, {}).get("max", 32.0)

    @property
    def min_temp(self):
        return self._temp_limits.get(self._mode, {}).get("min", 16.0)

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
        return self._attr_hvac_modes

    @property
    def fan_mode(self):
        if self._fan_speed == "AUTO":
            return FAN_AUTO
        elif self._fan_speed == "LV1":
            return "Level 1"
        elif self._fan_speed == "LV2":
            return "Level 2"
        elif self._fan_speed == "LV3":
            return "Level 3"
        elif self._fan_speed == "LV4":
            return "Level 4"
        elif self._fan_speed == "LV5":
            return "Level 5"
        else:
            return FAN_AUTO

    @property
    def fan_modes(self):
        return self._attr_fan_modes

    @property
    def swing_mode(self):
        if self._fan_swing == "VERTICAL":
            return SWING_VERTICAL
        elif self._fan_swing == "HORIZONTAL":
            return SWING_HORIZONTAL
        elif self._fan_swing == "BOTH":
            return SWING_BOTH
        else:
            return SWING_OFF

    @property
    def swing_modes(self):
        return self._attr_swing_modes

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
        elif fan_mode == "Level 1":
            self._fan_speed = "LV1"
        elif fan_mode == "Level 2":
            self._fan_speed = "LV2"
        elif fan_mode == "Level 3":
            self._fan_speed = "LV3"
        elif fan_mode == "Level 4":
            self._fan_speed = "LV4"
        elif fan_mode == "Level 5":
            self._fan_speed = "LV5"
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
        elif self._mode == "AUTO":
            # Clamp the value between -3 and +3 after subtracting 25
            target_temp = max(-3, min(3, target_temp - 25))

        await self._api.execute_command(self._id, self._family_id, self._power, target_temp, self._mode,
                                        self._fan_speed, self._fan_swing, self._humidity)
        await asyncio.sleep(10)
        self._update_lock = False
        await self.async_update()

    def __update_data(self, climate_data):
        self._power = climate_data["power"]
        self._mode = climate_data["mode"]
        if climate_data["mode"] == "AUTO":
            self._target_temp = climate_data["iduTemperature"] + 25
        else:
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