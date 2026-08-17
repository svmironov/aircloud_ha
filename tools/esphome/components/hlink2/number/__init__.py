import esphome.config_validation as cv
import esphome.codegen as cg
from esphome.components import number
from esphome.const import (
    CONF_CUSTOM,
    CONF_DEST,
    CONF_MIN_VALUE,
    CONF_MAX_VALUE,
    CONF_STEP,
    CONF_PASSWORD,
    CONF_RAW,
    CONF_RESTORE_MODE,
    CONF_SSID,
    CONF_TEXT,
    DEVICE_CLASS_SWITCH,
    ENTITY_CATEGORY_DIAGNOSTIC,
    ICON_WIFI,
)

from .. import hlink2_ns, Core, CONF_HLINK2_ID, CODEOWNERS
from ..mnemonics import Mnemonics, Mnemonic
from ..component import (
    config_schema,
    schema_mnemonic,
    schema_number,
    generate_mnemonic,
    generate_lambda,
    generate_MessageParameters,
    generate_arguments,
    validate_number,
    CONF_BUZZER,
    CONF_TARGET_TEMPERATURE,
    ICON_FORM,
    ICON_TARGET_TEMPERATURE,
    MNEMONIC_TARGET_TEMPERATURE,
    SCHEMA_MNEMONIC_CUSTOM,
    SCHEMA_MESSAGE_CMD_PARAMS,
    FINAL_VALIDATE_SCHEMA,
)


DEPENDENCIES = ["number"]
CODEOWNERS = CODEOWNERS

CommandStatusComponent = hlink2_ns.class_("CommandStatusComponent", cg.Component, cg.Parented.template(Core))
Number = hlink2_ns.class_("Number", number.Number, CommandStatusComponent)


COMPONENTS_CONFIG = {
    CONF_TARGET_TEMPERATURE: cv.All(
        number.number_schema(
            Number,
            icon=ICON_TARGET_TEMPERATURE,
            entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
            # disabled_by_default=True
        ).extend(schema_mnemonic(MNEMONIC_TARGET_TEMPERATURE))
        .extend({
            cv.Optional(CONF_MIN_VALUE, default=15): cv.Range(10,25),
            cv.Optional(CONF_MAX_VALUE, default=32): cv.Range(15,35),
            cv.Optional(CONF_STEP, default=0.5): cv.one_of(0.5, 1, 2),
        }).extend(SCHEMA_MESSAGE_CMD_PARAMS),
        validate_number,
    ),


    CONF_CUSTOM: cv.All(
        number.number_schema(
            Number,
            icon=ICON_FORM,
            entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        ).extend(SCHEMA_MNEMONIC_CUSTOM)
        .extend({
            cv.Required(CONF_MIN_VALUE): cv.float_,
            cv.Required(CONF_MAX_VALUE): cv.float_,
            cv.Required(CONF_STEP): cv.float_,
        }).extend(SCHEMA_MESSAGE_CMD_PARAMS),
        validate_number,
    ),
}

CONFIG_SCHEMA = config_schema(
    CONF_HLINK2_ID,
    Core,
    Number,
    **COMPONENTS_CONFIG,
) 

FINAL_VALIDATE_SCHEMA = FINAL_VALIDATE_SCHEMA

async def to_code(config):
    parent = await cg.get_variable(config[CONF_HLINK2_ID])

    for name in COMPONENTS_CONFIG:
        if conf := config.get(name):
            var = await number.new_number(conf, **{k:conf[k] for k in (CONF_MIN_VALUE, CONF_MAX_VALUE, CONF_STEP)})
            cg.add(var.set_parent(parent))
            await cg.register_component(var, conf)

            mnemonic_cg = generate_mnemonic(hlink2_ns, conf)
            params_cg = generate_MessageParameters(hlink2_ns, conf)

            if lambda_cg := generate_lambda(conf, mnemonic=str(mnemonic_cg), text=var):
                cg.add(var.set_mnemonic(mnemonic_cg, lambda_cg, params_cg))
            else:
                cg.add(var.set_mnemonic_default(mnemonic_cg, params_cg))
