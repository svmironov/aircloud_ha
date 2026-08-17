import esphome.config_validation as cv
import esphome.codegen as cg
from esphome.components import button
from esphome.const import (
    CONF_CUSTOM,
    CONF_RAW,
    CONF_VALUE,
    CONF_ID,
    CONF_NAME,
    CONF_QOS,
    CONF_RESTORE_MODE,
    DEVICE_CLASS_BUTTON,
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
    generate_arguments,
    CONF_BUZZER,
    CONF_FILTER_RESET,
    CONF_MNEMONIC,
    CONF_REMOTE_LOCK,
    ICON_BELL,
    ICON_FILTER,
    ICON_REMOTE_OFF,
    MNEMONIC_FILTER_STATUS,
    MNEMONIC_BUZZER,
    SCHEMA_MNEMONIC_CUSTOM,
    SCHEMA_QOS,
    FINAL_VALIDATE_SCHEMA,
)


DEPENDENCIES = ["button"]
CODEOWNERS = CODEOWNERS

CommandComponent = hlink2_ns.class_("CommandComponent", cg.Component, cg.Parented.template(Core))
Button = hlink2_ns.class_("Button", button.Button, CommandComponent)


COMPONENTS_CONFIG = {
    CONF_BUZZER: button.button_schema(
        Button,
        icon=ICON_BELL,
        entity_category=ENTITY_CATEGORY_CONFIG,
        #device_class=DEVICE_CLASS_BUTTON,
    ).extend({
        cv.Optional(CONF_BUZZER, default=False): cv.one_of(False),
        cv.Optional(CONF_RAW, default=True): cv.one_of(True),
    }).extend(SCHEMA_QOS)
    .extend(schema_mnemonic(MNEMONIC_BUZZER)),
    
    CONF_FILTER_RESET: button.button_schema(
        Button,
        icon=ICON_FILTER,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        #device_class=DEVICE_CLASS_BUTTON,
    ).extend({
        cv.Optional(CONF_BUZZER, default=True): cv.boolean,
        cv.Optional(CONF_RAW, default=True): cv.one_of(True),
    }).extend(SCHEMA_QOS)
    .extend(schema_mnemonic(MNEMONIC_FILTER_STATUS)),
    
    CONF_CUSTOM: button.button_schema(
        Button,
        icon=ICON_BUG,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
    ).extend({
        cv.Optional(CONF_BUZZER): cv.boolean,
        cv.Optional(CONF_RAW): cv.boolean,
        cv.Optional(CONF_VALUE): cv.string,
    }).extend(SCHEMA_MNEMONIC_CUSTOM)
    .extend(SCHEMA_QOS),
}

CONFIG_SCHEMA = config_schema(
    CONF_HLINK2_ID,
    Core,
    Button,
    **COMPONENTS_CONFIG,
)

FINAL_VALIDATE_SCHEMA = FINAL_VALIDATE_SCHEMA

async def to_code(config):
    parent = await cg.get_variable(config[CONF_HLINK2_ID])

    for name in COMPONENTS_CONFIG:
        if conf := config.get(name):
            var = await button.new_button(conf)
            cg.add(var.set_parent(parent))
            await cg.register_component(var, conf)

            if value := conf.get(CONF_VALUE):
                cg.add(var.set_mnemonic(*generate_arguments(
                    generate_mnemonic(hlink2_ns, conf),
                    value,
                    generate_MessageParameters(hlink2_ns, conf),
                    conf.get(CONF_RAW)
              )))
            else:
                cg.add(var.set_mnemonic_default(*generate_arguments(
                    generate_mnemonic(hlink2_ns, conf),
                    generate_MessageParameters(hlink2_ns, conf),
                    conf.get(CONF_RAW)
                )))



