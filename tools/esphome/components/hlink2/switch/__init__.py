import esphome.config_validation as cv
import esphome.codegen as cg
from esphome.components import switch
from esphome.const import (
    CONF_CUSTOM,
    CONF_ID,
    CONF_NAME,
    CONF_PRESET_ECO,
    CONF_QOS,
    CONF_RESTORE_MODE,
    DEVICE_CLASS_SWITCH,
    ENTITY_CATEGORY_CONFIG,
    ENTITY_CATEGORY_DIAGNOSTIC,
    ICON_BUG,
)

from .. import hlink2_ns, Core, CONF_HLINK2_ID, CODEOWNERS
from ..component import (
    config_schema,
    schema_mnemonic,
    generate_mnemonic,
    generate_MessageParameters,
    CONF_BUZZER,
    CONF_LED_WIFI,
    CONF_LED_TIMER,
    CONF_MNEMONIC,
    CONF_REMOTE_LOCK,
    ICON_BELL,
    ICON_LED,
    ICON_REMOTE_OFF,
    ICON_SPROUT,
    MNEMONIC_BUZZER,
    MNEMONIC_LED_WIFI,
    MNEMONIC_LED_TIMER,
    MNEMONIC_OPT1,
    SCHEMA_MNEMONIC_CUSTOM,
    SCHEMA_QOS,
    FINAL_VALIDATE_SCHEMA,
)


DEPENDENCIES = ["switch"]
CODEOWNERS = CODEOWNERS

CommandComponent = hlink2_ns.class_("CommandComponent", cg.Component, cg.Parented.template(Core))
Switch = hlink2_ns.class_("Switch", switch.Switch, CommandComponent)
BuzzerSwitch = hlink2_ns.class_("BuzzerSwitch", switch.Switch, cg.Component, cg.Parented.template(Core))


COMPONENTS_CONFIG = {
    CONF_BUZZER: switch.switch_schema(
        BuzzerSwitch,
        icon=ICON_BELL,
        entity_category=ENTITY_CATEGORY_CONFIG,
        device_class=DEVICE_CLASS_SWITCH,
    ).extend({
        cv.Optional(CONF_RESTORE_MODE, default='RESTORE_DEFAULT_OFF'): cv.enum(switch.RESTORE_MODES),
        cv.Optional(CONF_BUZZER, default=False): cv.one_of(False),
    }).extend(SCHEMA_QOS)
    .extend(schema_mnemonic(MNEMONIC_BUZZER)),
    
    CONF_PRESET_ECO: switch.switch_schema(
        Switch,
        icon=ICON_SPROUT,
        entity_category=ENTITY_CATEGORY_CONFIG,
        device_class=DEVICE_CLASS_SWITCH,
    ).extend({
        cv.Optional(CONF_RESTORE_MODE, default='RESTORE_DEFAULT_OFF'): cv.enum(switch.RESTORE_MODES),
        cv.Optional(CONF_BUZZER, default=True): cv.boolean,
    }).extend(SCHEMA_QOS)
    .extend(schema_mnemonic(MNEMONIC_OPT1)),

    CONF_LED_WIFI: switch.switch_schema(
        Switch,
        icon=ICON_LED,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        device_class=DEVICE_CLASS_SWITCH,
    ).extend({
        cv.Optional(CONF_RESTORE_MODE, default='RESTORE_DEFAULT_OFF'): cv.enum(switch.RESTORE_MODES),
        cv.Optional(CONF_BUZZER, default=True): cv.boolean,
    }).extend(SCHEMA_QOS)
    .extend(schema_mnemonic(MNEMONIC_LED_WIFI)),

    CONF_LED_TIMER: switch.switch_schema(
        Switch,
        icon=ICON_LED,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        device_class=DEVICE_CLASS_SWITCH,
    ).extend({
        cv.Optional(CONF_RESTORE_MODE, default='RESTORE_DEFAULT_OFF'): cv.enum(switch.RESTORE_MODES),
        cv.Optional(CONF_BUZZER, default=True): cv.boolean,
    }).extend(SCHEMA_QOS)
    .extend(schema_mnemonic(MNEMONIC_LED_TIMER)),

    # CONF_REMOTE_LOCK: switch.switch_schema(
    #     Switch,
    #     icon=ICON_REMOTE_OFF,
    #     entity_category=ENTITY_CATEGORY_CONFIG,
    #     device_class=DEVICE_CLASS_SWITCH,
    # ).extend({
    #     cv.Optional(CONF_RESTORE_MODE, default='RESTORE_DEFAULT_OFF'): cv.enum(switch.RESTORE_MODES),
    #     cv.Optional(CONF_BUZZER, default=True): cv.boolean,
    # }).extend(SCHEMA_QOS)
    # .extend(schema_mnemonic(MNEMONIC_REMOTE_LOCK)),
    
    CONF_CUSTOM: switch.switch_schema(
        Switch,
        icon=ICON_BUG,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
    ).extend({
        cv.Optional(CONF_RESTORE_MODE, default='RESTORE_DEFAULT_OFF'): cv.enum(switch.RESTORE_MODES),
        cv.Optional(CONF_BUZZER): cv.boolean,
    }).extend(SCHEMA_MNEMONIC_CUSTOM)
    .extend(SCHEMA_QOS),
}

CONFIG_SCHEMA = config_schema(
    CONF_HLINK2_ID,
    Core,
    Switch,
    BuzzerSwitch,
    **COMPONENTS_CONFIG,
)


FINAL_VALIDATE_SCHEMA = FINAL_VALIDATE_SCHEMA


async def to_code(config):
    parent = await cg.get_variable(config[CONF_HLINK2_ID])

    for name in COMPONENTS_CONFIG:
        if conf := config.get(name):
            var = await switch.new_switch(conf)
            cg.add(var.set_parent(parent))
            await cg.register_component(var, conf)
            cg.add(var.set_restore_mode(conf[CONF_RESTORE_MODE]))

            if name != CONF_BUZZER:
                cg.add(var.set_mnemonic_default(
                    generate_mnemonic(hlink2_ns, conf),
                    generate_MessageParameters(hlink2_ns, conf)
                ))



