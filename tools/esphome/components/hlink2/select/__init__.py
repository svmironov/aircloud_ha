import esphome.config_validation as cv
import esphome.codegen as cg
from esphome.components import select
from esphome.const import (
    CONF_CUSTOM,
    CONF_NAME,
    CONF_RAW,
    CONF_OPTIONS,
    ENTITY_CATEGORY_CONFIG,
    ENTITY_CATEGORY_DIAGNOSTIC,
    ICON_BUG,
    ICON_DATABASE,
)

from .. import hlink2_ns, Core, CONF_HLINK2_ID, CODEOWNERS
from ..component import (
    config_schema,
    schema_mnemonic,
    generate_mnemonic,
    generate_MessageParameters,
    generate_arguments,
    CONF_BUZZER,
    ICON_BELL,
    MNEMONIC_BUZZER,
    SCHEMA_MNEMONIC_CUSTOM,
    SCHEMA_QOS,
    FINAL_VALIDATE_SCHEMA,
)


DEPENDENCIES = ["select"]
CODEOWNERS = CODEOWNERS

CommandStatusComponent = hlink2_ns.class_("CommandStatusComponent", cg.Component, cg.Parented.template(Core))
Select = hlink2_ns.class_("Select", select.Select, CommandStatusComponent)


COMPONENTS_CONFIG = {
    CONF_OPTIONS: select.select_schema(
        Select,
        icon=ICON_DATABASE,
        entity_category=ENTITY_CATEGORY_CONFIG,
    ).extend({
        cv.Optional(CONF_OPTIONS, default= ["0", "1"]): cv.All(
            [cv.string],
            cv.Length(min=1),
        ),
        cv.Optional(CONF_BUZZER, default=False): cv.one_of(False),
        cv.Optional(CONF_RAW, default=True): cv.one_of(True),
    }).extend(SCHEMA_QOS) 
    .extend(schema_mnemonic(MNEMONIC_BUZZER)),
    
    CONF_CUSTOM: select.select_schema(
        Select,
        icon=ICON_BUG,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
    ).extend({
        cv.Required(CONF_OPTIONS): cv.All(
            [cv.string],
            cv.Length(min=1),
        ),
        cv.Optional(CONF_BUZZER): cv.boolean,
        cv.Optional(CONF_RAW, default=True): cv.one_of(True),
    }).extend(SCHEMA_MNEMONIC_CUSTOM)
    .extend(SCHEMA_QOS),
}

CONFIG_SCHEMA = config_schema(
    CONF_HLINK2_ID,
    Core,
    Select,
    **COMPONENTS_CONFIG,
)


FINAL_VALIDATE_SCHEMA = FINAL_VALIDATE_SCHEMA


async def to_code(config):
    parent = await cg.get_variable(config[CONF_HLINK2_ID])

    for name, conf in config.items():
        if name in COMPONENTS_CONFIG:
            var = await select.new_select(conf, options=conf.get(CONF_OPTIONS, []))
            cg.add(var.set_parent(parent))
            await cg.register_component(var, conf)

            cg.add(var.set_mnemonic_default(*generate_arguments(
                generate_mnemonic(hlink2_ns, conf),
                generate_MessageParameters(hlink2_ns, conf),
                conf.get(CONF_RAW)
            )))

