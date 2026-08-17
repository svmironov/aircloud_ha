import esphome.config_validation as cv
import esphome.codegen as cg
from esphome.components import text
from esphome.const import (
    CONF_CUSTOM,
    CONF_DEST,
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
    generate_mnemonic,
    generate_lambda,
    generate_MessageParameters,
    generate_arguments,
    final_validate_mnemonics,
    CONF_BUZZER,
    ICON_FORM,
    ICON_PASSWORD,
    MNEMONIC_SSID,
    MNEMONIC_PASSWORD,
    SCHEMA_MNEMONIC_CUSTOM,
    SCHEMA_MESSAGE_CMD_PARAMS,
    FINAL_VALIDATE_SCHEMA,
)


DEPENDENCIES = ["text"]
CODEOWNERS = CODEOWNERS

CommandComponent = hlink2_ns.class_("CommandComponent", cg.Component, cg.Parented.template(Core))
Text = hlink2_ns.class_("Text", text.Text, CommandComponent)


COMPONENTS_CONFIG = {
    CONF_SSID: text.text_schema(
        Text,
        icon=ICON_WIFI,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        mode=CONF_TEXT,
    ).extend(schema_mnemonic(MNEMONIC_SSID))
    .extend({
        cv.Optional(CONF_RAW, default=False): cv.one_of(False),
    }).extend(SCHEMA_MESSAGE_CMD_PARAMS),

    CONF_PASSWORD: text.text_schema(
        Text,
        icon=ICON_PASSWORD,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        mode=CONF_PASSWORD,
    ).extend(schema_mnemonic(MNEMONIC_PASSWORD))
    .extend({
        cv.Optional(CONF_RAW, default=False): cv.one_of(False),
    }).extend(SCHEMA_MESSAGE_CMD_PARAMS),

    CONF_CUSTOM: text.text_schema(
        Text,
        icon=ICON_FORM,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
    ).extend(SCHEMA_MNEMONIC_CUSTOM)
    .extend({
        cv.Optional(CONF_RAW): cv.boolean,
    }).extend(SCHEMA_MESSAGE_CMD_PARAMS),
}

CONFIG_SCHEMA = config_schema(
    CONF_HLINK2_ID,
    Core,
    Text,
    **COMPONENTS_CONFIG,
) 


FINAL_VALIDATE_SCHEMA = cv.All(lambda a: final_validate_mnemonics(a, Mnemonic.Mode.CMD))


async def to_code(config):
    parent = await cg.get_variable(config[CONF_HLINK2_ID])

    for name in COMPONENTS_CONFIG:
        if conf := config.get(name):
            var = await text.new_text(conf)
            cg.add(var.set_parent(parent))
            await cg.register_component(var, conf)

            mnemonic_cg = generate_mnemonic(hlink2_ns, conf)
            params_cg = generate_MessageParameters(hlink2_ns, conf)

            if lambda_cg := generate_lambda(conf, mnemonic=str(mnemonic_cg), text=var):
                cg.add(var.set_mnemonic(*generate_arguments(mnemonic_cg, lambda_cg, params_cg, conf.get(CONF_RAW))))
            else:
                cg.add(var.set_mnemonic_default(*generate_arguments(mnemonic_cg, params_cg, conf.get(CONF_RAW))))
