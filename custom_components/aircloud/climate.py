from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (FAN_AUTO, FAN_HIGH,
                                                    FAN_LOW, FAN_MEDIUM,
                                                    HVAC_MODE_AUTO,
                                                    HVAC_MODE_COOL,
                                                    HVAC_MODE_DRY,
                                                    HVAC_MODE_FAN_ONLY,
                                                    HVAC_MODE_HEAT,
                                                    HVAC_MODE_OFF,
                                                    SUPPORT_FAN_MODE,
                                                    SUPPORT_SWING_MODE,
                                                    SUPPORT_TARGET_TEMPERATURE,
                                                    SWING_OFF, SWING_VERTICAL)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature

from . import AirCloudApi, DOMAIN, API

SUPPORT_FAN = [
    FAN_AUTO,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH
]
SUPPORT_SWING = [
    SWING_OFF,
    SWING_VERTICAL,
]
SUPPORT_HVAC = [
    HVAC_MODE_OFF,
    HVAC_MODE_COOL,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_AUTO,
    HVAC_MODE_HEAT
]


async def _async_setup(hass, async_add):
    api = hass.data[DOMAIN][API]

    devices = await hass.async_add_executor_job(api.load_climate_data)
    for device in devices:
        async_add([AirCloudClimateEntity(api, device)], update_before_add=False)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    await _async_setup(hass, async_add_entities)

async def async_setup_entry(hass, config_entry, async_add_devices):
    await _async_setup(hass, async_add_devices)


class AirCloudClimateEntity(ClimateEntity):
    def __init__(self, api, device):
        self._api = api
        self._id = device["id"]
        self._name = device["name"]
        self._vendor_id = device["vendorThingId"]
        self._update_lock = False
        self.__update_data(device)

    @property
    def unique_id(self):
         return self._vendor_id

    @property
    def supported_features(self):
        support_flags = SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE | SUPPORT_SWING_MODE
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
                return HVAC_MODE_OFF
        elif self._mode == "COOLING":
                return HVAC_MODE_COOL
        elif self._mode == "HEATING":
                return HVAC_MODE_HEAT
        elif self._mode == "FAN":
                return HVAC_MODE_FAN_ONLY
        elif self._mode == "DRY":
                return HVAC_MODE_DRY
        elif self._mode == "AUTO":
                return HVAC_MODE_AUTO
        else:
                return HVAC_MODE_OFF

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
                return FAN_MEDIUM
        elif self._fan_speed == "LV4":
                return FAN_MEDIUM
        elif self._fan_speed == "LV5":
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
        return SWING_OFF

    @property
    def swing_modes(self):
        return SUPPORT_SWING

    def turn_on(self):
        pass
        
    def set_hvac_mode(self, hvac_mode):
        self._update_lock = True

        if hvac_mode != HVAC_MODE_OFF:
                self._power = "ON"

        if hvac_mode == HVAC_MODE_OFF:
                self._power = "OFF"
        elif hvac_mode == HVAC_MODE_COOL:
                self._mode = "COOLING"
        elif hvac_mode == HVAC_MODE_DRY:
                self._mode = "DRY"
        elif hvac_mode == HVAC_MODE_FAN_ONLY:
                self._mode = "FAN"
        elif hvac_mode == HVAC_MODE_AUTO:
                self._mode = "AUTO"
        elif hvac_mode == HVAC_MODE_HEAT:
                self._mode = "HEATING"
        else:
                self._power = "OFF"
        
        self.__execute_command()

    def set_preset_mode(self, preset_mode):
        self.__execute_command()

    def set_fan_mode(self, fan_mode):
        self._update_lock = True

        if fan_mode == FAN_AUTO:
                self._fan_speed = "AUTO"
        elif fan_mode == FAN_LOW:
                self._fan_speed = "LV1"
        elif fan_mode == FAN_MEDIUM:
                self._fan_speed = "LV3"
        elif fan_mode == FAN_HIGH:
                self._fan_speed = "LV5"
        else:
                self._fan_speed = "AUTO"

        self.__execute_command()

    def set_swing_mode(self, swing_mode):
        self._update_lock = True
        
        if swing_mode == SWING_VERTICAL:
                self._power = "VERTICAL"
        else:
                self._power = "OFF"
        
        self.__execute_command()

    def set_temperature(self, **kwargs):
        self._update_lock = True

        target_temp = kwargs.get(ATTR_TEMPERATURE)
        if target_temp is None:
                return
        
        self._target_temp = target_temp
        self.__execute_command()

    def update(self):
        if self._update_lock is False:
                devices =  self._api.load_climate_data()
                for device in devices:
                        if self._id == device["id"]:
                                self.__update_data(device)
        self._update_lock = False

    def __execute_command(self):
        self._api.execute_command(self._id, self._power, self._target_temp, self._mode, self._fan_speed, self._fan_swing)

    def __update_data(self, climate_data):
        self._power = climate_data["power"]
        self._mode = climate_data["mode"]
        self._target_temp = climate_data["iduTemperature"]
        self._room_temp = climate_data["roomTemperature"]
        self._fan_speed = climate_data["fanSpeed"]
        self._fan_swing = climate_data["fanSwing"]
