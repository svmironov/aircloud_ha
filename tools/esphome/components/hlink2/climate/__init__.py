from esphome import automation
import esphome.config_validation as cv
import esphome.codegen as cg
from esphome.components import climate
from esphome.components.climate import (
    CONF_CURRENT_TEMPERATURE,
    CONF_MIN_HUMIDITY,
    CONF_MAX_HUMIDITY,
    CONF_TARGET_HUMIDITY,
    ClimateMode,
    ClimatePreset,
    ClimateSwingMode,
    ClimateFanMode,
)
from esphome.const import (
    CONF_ID,
    CONF_QOS,
    CONF_STATUS,
    CONF_COMMAND,
    CONF_SUPPORTED_MODES,
    CONF_SUPPORTED_SWING_MODES,
    CONF_SUPPORTED_FAN_MODES,
    CONF_SUPPORTED_PRESETS,
    CONF_VISUAL,
    CONF_MIN_TEMPERATURE,
    CONF_MAX_TEMPERATURE,
    CONF_TEMPERATURE_STEP,
    CONF_TARGET_TEMPERATURE,
)

from ..component import (
    generate_MessageParameters,
    CONF_HVAC_ACTIONS,
    CONF_COMMAND_MESSAGE,
    CONF_STATUS_MESSAGE,
    SCHEMA_MESSAGE_STS_PARAMS,
    SCHEMA_MESSAGE_CMD_PARAMS,
)

DEPENDENCIES = ["climate"]

from .. import hlink2_ns, Core, CONF_HLINK2_ID
Climate = hlink2_ns.class_("Climate", climate.Climate, cg.Component, cg.Parented.template(Core))


# allowed modes
HLINK2_AC_MODES = {
    "OFF": ClimateMode.CLIMATE_MODE_OFF,
    "COOL": ClimateMode.CLIMATE_MODE_COOL,
    "HEAT": ClimateMode.CLIMATE_MODE_HEAT,
    "DRY": ClimateMode.CLIMATE_MODE_DRY,
    "FAN_ONLY": ClimateMode.CLIMATE_MODE_FAN_ONLY,
    "HEAT_COOL": ClimateMode.CLIMATE_MODE_HEAT_COOL,
}

HLINK2_AC_SWING_MODES = {
    "OFF": ClimateSwingMode.CLIMATE_SWING_OFF,
    "VERTICAL": ClimateSwingMode.CLIMATE_SWING_VERTICAL,
    "HORIZONTAL": ClimateSwingMode.CLIMATE_SWING_HORIZONTAL,
    "BOTH": ClimateSwingMode.CLIMATE_SWING_BOTH,
}

HLINK2_AC_FAN_MODES = {
    "AUTO": ClimateFanMode.CLIMATE_FAN_AUTO,
    "LOW": ClimateFanMode.CLIMATE_FAN_LOW,
    "MEDIUM": ClimateFanMode.CLIMATE_FAN_MEDIUM,
    "MIDDLE": ClimateFanMode.CLIMATE_FAN_MIDDLE,
    "HIGH": ClimateFanMode.CLIMATE_FAN_HIGH,
    "QUIET": ClimateFanMode.CLIMATE_FAN_QUIET,
}

HLINK2_AC_PRESETS = {
    "NONE": ClimatePreset.CLIMATE_PRESET_NONE,
    "AWAY": ClimatePreset.CLIMATE_PRESET_AWAY,
    "ECO": ClimatePreset.CLIMATE_PRESET_ECO,
    "BOOST": ClimatePreset.CLIMATE_PRESET_BOOST,
    "SLEEP": ClimatePreset.CLIMATE_PRESET_SLEEP,
}

HLINK2_AC_CUSTOM_PRESETS = {
    "SILENCE": "Silence"
}


# default values
DEFAULT_MIN_TEMPERATURE = 16.0
DEFAULT_MAX_TEMPERATURE = 32.0
DEFAULT_TEMPERATURE_STEP = 0.5
DEFAULT_MODES = list(HLINK2_AC_MODES.keys())
DEFAULT_SWING_MODES = ["OFF", "VERTICAL"]
DEFAULT_FAN_MODES = list(HLINK2_AC_FAN_MODES.keys())
DEFAULT_PRESETS = list(HLINK2_AC_PRESETS) + list(HLINK2_AC_CUSTOM_PRESETS)


def validate_visual(v):
    if v.get(CONF_MIN_TEMPERATURE) >= v.get(CONF_MAX_TEMPERATURE):
        raise cv.Invalid("visual.min_temperature must be ≤ visual.max_temperature")
    if isinstance(v.get(CONF_TEMPERATURE_STEP), (int, float)):
        value = v.get(CONF_TEMPERATURE_STEP)
        v[CONF_TEMPERATURE_STEP] = {
            CONF_TARGET_TEMPERATURE: value,
            CONF_CURRENT_TEMPERATURE: value,
        }
    return v


CONFIG_SCHEMA = climate.climate_schema(
    Climate
).extend({
    cv.GenerateID(): cv.declare_id(Climate),
    cv.GenerateID(CONF_HLINK2_ID): cv.use_id(Core),
    cv.Optional(
        CONF_SUPPORTED_MODES,
        default=DEFAULT_MODES,
    ): cv.ensure_list(cv.enum(HLINK2_AC_MODES, upper=True)),
    cv.Optional(
        CONF_SUPPORTED_SWING_MODES,
        default=DEFAULT_SWING_MODES,
    ): cv.ensure_list(cv.enum(HLINK2_AC_SWING_MODES, upper=True)),
    cv.Optional(
        CONF_SUPPORTED_FAN_MODES,
        default=DEFAULT_FAN_MODES,
    ): cv.ensure_list(cv.enum(HLINK2_AC_FAN_MODES, upper=True)),
    cv.Optional(
        CONF_SUPPORTED_PRESETS,
        default=DEFAULT_PRESETS,
    ): cv.ensure_list(cv.enum(HLINK2_AC_PRESETS | HLINK2_AC_CUSTOM_PRESETS, upper=True)),
    cv.Optional(
        CONF_HVAC_ACTIONS,
        default=False,
    ): cv.boolean,
    cv.Optional(CONF_STATUS): SCHEMA_MESSAGE_STS_PARAMS,
    cv.Optional(CONF_COMMAND): SCHEMA_MESSAGE_CMD_PARAMS,
    cv.Optional(CONF_VISUAL): cv.All(
        cv.Schema({
            cv.Optional(
                CONF_MIN_TEMPERATURE,
                default = DEFAULT_MIN_TEMPERATURE
            ): cv.All(cv.float_, cv.Range(10, 35)),
            cv.Optional(
                CONF_MAX_TEMPERATURE,
                default= 32
            ): cv.All(cv.float_, cv.Range(10, 35)),
            cv.Optional(
                CONF_TEMPERATURE_STEP,
                default=DEFAULT_TEMPERATURE_STEP,
            ): cv.Any(
                cv.All(cv.float_, cv.one_of(0.5, 1, 2)),
                cv.Schema({
                    cv.Required(CONF_TARGET_TEMPERATURE): cv.All(cv.float_, cv.one_of(0.5, 1, 2)),
                    cv.Required(CONF_CURRENT_TEMPERATURE): cv.All(cv.float_, cv.one_of(0.5, 1, 2)),
                }),
            ),
        }),
        validate_visual,
    ),
})


async def to_code(config):
    parent = await cg.get_variable(config[CONF_HLINK2_ID])
    var = await climate.new_climate(config)
    cg.add(var.set_parent(parent))
    await cg.register_component(var, config)

    if modes := config.get(CONF_SUPPORTED_MODES):
        cg.add(var.set_supported_modes(modes))
    
    if swing_modes :=  config.get(CONF_SUPPORTED_SWING_MODES):
        cg.add(var.set_supported_swing_modes(swing_modes))

    if fan_modes :=  config.get(CONF_SUPPORTED_FAN_MODES):
        cg.add(var.set_supported_fan_modes(fan_modes))

    if presets :=  config.get(CONF_SUPPORTED_PRESETS):
        custom_presets = presets.copy()

        # remove custom presets from regular presets list
        for custom_preset in HLINK2_AC_CUSTOM_PRESETS:
            if custom_preset in presets:
                presets.remove(custom_preset)
        
        # remove regular presets from custom presets list
        for preset in HLINK2_AC_PRESETS:
            if preset in custom_presets:
                custom_presets.remove(preset)

        # add NONE preset if not present
        if "NONE" not in presets:
            presets.append(HLINK2_AC_PRESETS["NONE"])

        cg.add(var.set_supported_presets(presets))
        if custom_presets:
            cg.add(var.set_supported_custom_presets(custom_presets))

    if actions := config.get(CONF_HVAC_ACTIONS):
        cg.add(var.set_supports_hvac_actions(actions))
    
    cg.add(var.set_message_status_parameters(generate_MessageParameters(hlink2_ns, config.get(CONF_STATUS))))
    cg.add(var.set_message_command_parameters(generate_MessageParameters(hlink2_ns, config.get(CONF_COMMAND))))


