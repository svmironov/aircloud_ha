import esphome.config_validation as cv
import esphome.codegen as cg
from esphome.components import text_sensor
from esphome.const import (
    CONF_ID,
    CONF_NAME,
    CONF_LAMBDA,
    CONF_MODEL,
    CONF_DEST,
    CONF_CUSTOM,
    CONF_UPDATE_INTERVAL,
    CONF_QOS,
    CONF_RAW,
    ENTITY_CATEGORY_DIAGNOSTIC,
    ICON_BUG,
)



from .. import hlink2_ns, Core, CONF_HLINK2_ID, CODEOWNERS
from ..mnemonics import Mnemonics, Mnemonic
from ..component import (
    config_schema,
    generate_MessageParameters,
    generate_mnemonic,
    generate_lambda,
    generate_arguments,
    schema_mnemonic,
    CONF_MNEMONIC,
    CONF_PROMOTE,
    MNEMONIC_MODEL,
    ICON_INFORMATION,
    SCHEMA_MNEMONIC_PARAMS,
    SCHEMA_MNEMONIC_CUSTOM,
    FINAL_VALIDATE_SCHEMA,
)


DEPENDENCIES = ['text_sensor']
CODEOWNERS = CODEOWNERS

TextSensor = hlink2_ns.class_('TextSensor', text_sensor.TextSensor, cg.Component)


COMPONENTS_CONFIG = {
    CONF_MODEL: text_sensor.text_sensor_schema(TextSensor,
        icon=ICON_INFORMATION,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
    ).extend(SCHEMA_MNEMONIC_PARAMS)
    .extend(schema_mnemonic(MNEMONIC_MODEL)),

    CONF_CUSTOM: text_sensor.text_sensor_schema(
        TextSensor,
        icon=ICON_BUG,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
    ).extend(SCHEMA_MNEMONIC_CUSTOM)
    .extend(SCHEMA_MNEMONIC_PARAMS),
}


CONFIG_SCHEMA = config_schema(
    CONF_HLINK2_ID,
    Core,
    TextSensor,
    **COMPONENTS_CONFIG,
)


FINAL_VALIDATE_SCHEMA = FINAL_VALIDATE_SCHEMA


async def to_code(config):
    parent = await cg.get_variable(config[CONF_HLINK2_ID])

    for name, conf in config.items():
        if name in COMPONENTS_CONFIG:
            var = await text_sensor.new_text_sensor(conf)
            cg.add(var.set_parent(parent))
            await cg.register_component(var, conf)

            mnemonic_cg = generate_mnemonic(hlink2_ns, conf)
            params_cg = generate_MessageParameters(hlink2_ns, conf)
            
            if lambda_cg := generate_lambda(conf, mnemonic=str(mnemonic_cg), sensor=var):
                cg.add(var.set_mnemonic(*generate_arguments(mnemonic_cg, lambda_cg, params_cg, conf.get(CONF_PROMOTE))))
            else:
                cg.add(var.set_mnemonic_default(*generate_arguments(mnemonic_cg, params_cg, conf.get(CONF_PROMOTE))))

