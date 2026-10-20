"""Minimal Home Assistant import boundary for standalone offline tests.

This only supplies types/constants outside the subject under test when Home
Assistant is absent. api.py, climate.py, const.py and aiohttp are imported and
executed normally. This is not a Home Assistant integration/runtime fixture.
"""
from enum import IntFlag, StrEnum
import importlib.util
import sys
from types import ModuleType

import voluptuous as vol


def install_when_missing():
    if importlib.util.find_spec("homeassistant") is not None:
        return

    def module(name, **values):
        result = ModuleType(name)
        result.__path__ = []
        result.__dict__.update(values)
        sys.modules[name] = result
        if "." in name:
            parent, attr = name.rsplit(".", 1)
            setattr(sys.modules[parent], attr, result)
        return result

    class HVACMode(StrEnum):
        OFF = "off"
        COOL = "cool"
        HEAT = "heat"
        DRY = "dry"
        FAN_ONLY = "fan_only"
        AUTO = "auto"

    class ClimateEntityFeature(IntFlag):
        TARGET_TEMPERATURE = 1
        FAN_MODE = 8
        SWING_MODE = 32
        TURN_OFF = 128
        TURN_ON = 256

    class ClimateEntity:
        def async_write_ha_state(self):
            pass

    class UnitOfTemperature(StrEnum):
        CELSIUS = "°C"

    class HomeAssistantError(Exception):
        pass

    class ConfigFlow:
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__()

    class OptionsFlow:
        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}

        def async_create_entry(self, **kwargs):
            return {"type": "create_entry", **kwargs}

    module("homeassistant")
    module("homeassistant.components")
    module("homeassistant.components.climate", ClimateEntity=ClimateEntity)
    module(
        "homeassistant.components.climate.const",
        ClimateEntityFeature=ClimateEntityFeature,
        HVACMode=HVACMode,
        FAN_AUTO="auto",
        SWING_BOTH="both",
        SWING_HORIZONTAL="horizontal",
        SWING_VERTICAL="vertical",
        SWING_OFF="off",
    )
    module(
        "homeassistant.const",
        CONF_EMAIL="email", CONF_PASSWORD="password",
        ATTR_TEMPERATURE="temperature", UnitOfTemperature=UnitOfTemperature,
    )
    module("homeassistant.helpers")
    module(
        "homeassistant.helpers.config_validation",
        positive_int=vol.All(vol.Coerce(int), vol.Range(min=0)),
        positive_float=vol.All(vol.Coerce(float), vol.Range(min=0)),
        string=str,
        multi_select=lambda options: vol.All(list, [vol.In(options)]),
    )
    module("homeassistant.config_entries", ConfigEntry=type("ConfigEntry", (), {}),
           ConfigFlow=ConfigFlow, OptionsFlow=OptionsFlow, CONN_CLASS_CLOUD_POLL="cloud_poll")
    module(
        "homeassistant.core", HomeAssistant=type("HomeAssistant", (), {}),
        ServiceCall=type("ServiceCall", (), {}),
        callback=lambda fn: fn,
    )
    module("homeassistant.exceptions", HomeAssistantError=HomeAssistantError)


install_when_missing()
