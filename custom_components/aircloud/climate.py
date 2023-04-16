"""JciHitachi integration."""
import logging

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (FAN_AUTO, FAN_DIFFUSE,
                                                    FAN_FOCUS, FAN_HIGH,
                                                    FAN_LOW, FAN_MEDIUM,
                                                    HVAC_MODE_AUTO,
                                                    HVAC_MODE_COOL,
                                                    HVAC_MODE_DRY,
                                                    HVAC_MODE_FAN_ONLY,
                                                    HVAC_MODE_HEAT,
                                                    HVAC_MODE_OFF,
                                                    PRESET_BOOST, PRESET_ECO,
                                                    PRESET_NONE,
                                                    SUPPORT_FAN_MODE,
                                                    SUPPORT_PRESET_MODE,
                                                    SUPPORT_SWING_MODE,
                                                    SUPPORT_TARGET_TEMPERATURE,
                                                    SWING_BOTH,
                                                    SWING_HORIZONTAL,
                                                    SWING_OFF, SWING_VERTICAL)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature

from . import AirCloudApi, DOMAIN, API

_LOGGER = logging.getLogger(__name__)

FAN_SILENT = "silent"
FAN_RAPID = "rapid"
FAN_EXPRESS = "express"
PRESET_MOLD_PREVENTION = "Mold Prev"
PRESET_ECO_MOLD_PREVENTION = "Eco & Mold Prev"

SUPPORT_FAN = [
    FAN_AUTO,
    FAN_SILENT,    
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_RAPID,
    FAN_EXPRESS
]
SUPPORT_SWING = [
    SWING_OFF,
    SWING_VERTICAL,
    SWING_HORIZONTAL,
    SWING_BOTH
]
SUPPORT_HVAC = [
    HVAC_MODE_OFF,
    HVAC_MODE_COOL,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_AUTO,
    HVAC_MODE_HEAT,
]


async def _async_setup(hass, async_add):
    api = hass.data[DOMAIN][API]

    for thing in api.things.values():
        if thing.type == "AC":
            async_add(
                [AirCloudClimateEntity(thing, api)],
                update_before_add=True
            )

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    await _async_setup(hass, async_add_entities)

async def async_setup_entry(hass, config_entry, async_add_devices):
    await _async_setup(hass, async_add_devices)


class AirCloudClimateEntity(ClimateEntity, AirCloudApi):
    def __init__(self, thing, coordinator):
        super().__init__(thing, coordinator)
        self._supported_features = self.calculate_supported_features()
        self._supported_fan_modes = [fan_mode for i, fan_mode in enumerate(SUPPORT_FAN) if 2 ** i & self._thing.support_code.FanSpeed != 0]
        self._supported_hvac = [SUPPORT_HVAC[0]] + [hvac for i, hvac in enumerate(SUPPORT_HVAC[1:]) if 2 ** i & self._thing.support_code.Mode != 0]
        self._supported_presets = self.calculate_supported_presets()
        self._prev_target = self._thing.support_code.min_temp

    @property
    def supported_features(self):
        return self._supported_features

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self):
        return None

    @property
    def target_temperature(self):
        """Return the target temperature."""
        return None

    @property
    def target_temperature_step(self):
        """Return the target temperature step."""
        return 1.0

    @property
    def max_temp(self):
        """Return the maximum temperature."""

        return 2.0
    
    @property
    def min_temp(self):
        return 1.0

    @property
    def hvac_mode(self):
        status = "off"
        if status:
            if status.power == "off":
                return HVAC_MODE_OFF
            elif status.mode == "cool":
                return HVAC_MODE_COOL
            elif status.mode == "dry":
                return HVAC_MODE_DRY
            elif status.mode == "fan":
                return HVAC_MODE_FAN_ONLY
            elif status.mode == "auto":
                return HVAC_MODE_AUTO
            elif status.mode == "heat":
                return HVAC_MODE_HEAT

        _LOGGER.error("Missing hvac_mode")
        return None

    @property
    def hvac_modes(self):
        return self._supported_hvac
    
    @property
    def preset_mode(self):
        return None

    @property
    def preset_modes(self):
        return self._supported_presets

    @property
    def fan_mode(self):
        return None
    
    @property
    def fan_modes(self):
        return self._supported_fan_modes
    
    @property
    def swing_mode(self):
        return None

    @property
    def swing_modes(self):
        return SUPPORT_SWING

    @property
    def unique_id(self):
        return '123_climate'

    def calculate_supported_features(self):
        support_flags = SUPPORT_TARGET_TEMPERATURE
        return support_flags
    
    def calculate_supported_presets(self):
        supported_presets = [PRESET_NONE]
        return supported_presets

    def turn_on(self):
        """Turn the device on."""
        _LOGGER.debug(f"Turn {self.name} on")
        self.put_queue(status_name="power", status_str_value="on")
        self.update()
        
    def set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""

        _LOGGER.debug(f"Set {self.name} hvac_mode to {hvac_mode}")

        status = "off"
        if status.power == "off" and hvac_mode != HVAC_MODE_OFF:
            self.put_queue(status_name="power", status_str_value="on")

        if hvac_mode == HVAC_MODE_OFF:
            self.put_queue(status_name="power", status_str_value="off")
        elif hvac_mode == HVAC_MODE_COOL:
            self.put_queue(status_name="mode", status_str_value="cool")
        elif hvac_mode == HVAC_MODE_DRY:
            self.put_queue(status_name="mode", status_str_value="dry")
        elif hvac_mode == HVAC_MODE_FAN_ONLY:
            self.put_queue(status_name="mode", status_str_value="fan")
        elif hvac_mode == HVAC_MODE_AUTO:
            self.put_queue(status_name="mode", status_str_value="auto")
        elif hvac_mode == HVAC_MODE_HEAT:
            self.put_queue(status_name="mode", status_str_value="heat")
        else:
            _LOGGER.error("Invalid hvac_mode.")
        self.update()

    def set_preset_mode(self, preset_mode):
        """Set new target preset mode."""

        _LOGGER.debug(f"Set {self.name} preset_mode to {preset_mode}")
        
        if preset_mode == PRESET_ECO_MOLD_PREVENTION:
            self.put_queue(status_name="energy_save", status_str_value="enabled")
            self.put_queue(status_name="mold_prev", status_str_value="enabled")
            self.put_queue(status_name="fast_op", status_str_value="disabled")
        elif preset_mode == PRESET_ECO:
            self.put_queue(status_name="energy_save", status_str_value="enabled")
            self.put_queue(status_name="mold_prev", status_str_value="disabled")
            self.put_queue(status_name="fast_op", status_str_value="disabled")
        elif preset_mode == PRESET_MOLD_PREVENTION:
            self.put_queue(status_name="energy_save", status_str_value="disabled")
            self.put_queue(status_name="mold_prev", status_str_value="enabled")
            self.put_queue(status_name="fast_op", status_str_value="disabled")
        elif preset_mode == PRESET_BOOST:
            self.put_queue(status_name="energy_save", status_str_value="disabled")
            self.put_queue(status_name="mold_prev", status_str_value="disabled")
            self.put_queue(status_name="fast_op", status_str_value="enabled")
        elif preset_mode == PRESET_NONE:
            self.put_queue(status_name="energy_save", status_str_value="disabled")
            self.put_queue(status_name="mold_prev", status_str_value="disabled")
            self.put_queue(status_name="fast_op", status_str_value="disabled")
        else:
            _LOGGER.error("Invalid preset_mode.")
        self.update()

    def set_fan_mode(self, fan_mode):
        """Set new target fan mode."""

        _LOGGER.debug(f"Set {self.name} fan_mode to {fan_mode}")

        if fan_mode == FAN_AUTO:
            self.put_queue(status_name="air_speed", status_str_value="auto")
        elif fan_mode == FAN_SILENT:
            self.put_queue(status_name="air_speed", status_str_value="silent")
        elif fan_mode == FAN_LOW:
            self.put_queue(status_name="air_speed", status_str_value="low")
        elif fan_mode == FAN_MEDIUM:
            self.put_queue(status_name="air_speed", status_str_value="moderate")
        elif fan_mode == FAN_HIGH:
            self.put_queue(status_name="air_speed", status_str_value="high")
        elif fan_mode == FAN_RAPID:
            self.put_queue(status_name="air_speed", status_str_value="rapid")
        elif fan_mode == FAN_EXPRESS:
            self.put_queue(status_name="air_speed", status_str_value="express")
        else:
            _LOGGER.error("Invalid fan_mode.")
        self.update()

    def set_swing_mode(self, swing_mode):
        self.update()

    def set_temperature(self, **kwargs):
        self.update()

    def update(self):
        pass
