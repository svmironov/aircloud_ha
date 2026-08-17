import datetime

import os
from esphome import core
import esphome.config_validation as cv
import esphome.codegen as cg
from esphome.components import uart
from esphome.const import (
    CONF_ID,
    CONF_DATA,
    CONF_ITEMS,
    CONF_NAME,
    CONF_MODE,
    CONF_DEST,
    CONF_TYPE,
    CONF_LAMBDA,
    CONF_PARAMETERS,
    UNIT_MILLISECOND,
    UNIT_SECOND,
)


from .mnemonics import (
    Mnemonic,
    Mnemonics,
    MNEMONIC_CPP,
    MNEMONIC_JSON,
)
from .component import (
    validate_mnemonic,
    CONF_FLAG,
    CONF_MNEMONICS,
    SCHEMA_MESSAGE_CMD_PARAMS,
    SCHEMA_MNEMONIC_CUSTOM,
    SCHEMA_FLAG,
)

CODEOWNERS = ["@clsergent"]
DEPENDENCIES = ["uart"]


Mnemonics.init()
# builtin mnemonics
Mnemonic.get('Buzz', Mnemonic.Dest.IDU, Mnemonic.Mode.CMD, Mnemonic.Type.INT, builtin=True),
Mnemonic.get('FanS', Mnemonic.Dest.IDU, Mnemonic.Mode.STS | Mnemonic.Mode.CMD, Mnemonic.Type.INT, builtin=True),
Mnemonic.get('FanSw', Mnemonic.Dest.IDU, Mnemonic.Mode.STS | Mnemonic.Mode.CMD, Mnemonic.Type.INT, builtin=True),
Mnemonic.get('FilS', Mnemonic.Dest.IDU, Mnemonic.Mode.STS | Mnemonic.Mode.CMD, Mnemonic.Type.INT, builtin=True),
Mnemonic.get('FltT', Mnemonic.Dest.IDU, Mnemonic.Mode.STS, Mnemonic.Type.INT, builtin=True),
Mnemonic.get('HExT', Mnemonic.Dest.IDU, Mnemonic.Mode.STS, Mnemonic.Type.FLOAT, builtin=True),
Mnemonic.get('HExT', Mnemonic.Dest.ODU, Mnemonic.Mode.STS, Mnemonic.Type.FLOAT, builtin=True),
Mnemonic.get('Hr', Mnemonic.Dest.IDU, Mnemonic.Mode.STS, Mnemonic.Type.FLOAT, builtin=True),
Mnemonic.get('Mode', Mnemonic.Dest.IDU, Mnemonic.Mode.STS | Mnemonic.Mode.CMD, Mnemonic.Type.INT, builtin=True),
Mnemonic.get('Modl', Mnemonic.Dest.IDU, Mnemonic.Mode.STS, Mnemonic.Type.STR, builtin=True),
Mnemonic.get('OnOf', Mnemonic.Dest.IDU, Mnemonic.Mode.STS | Mnemonic.Mode.CMD, Mnemonic.Type.INT, builtin=True),
Mnemonic.get('Opt1', Mnemonic.Dest.IDU, Mnemonic.Mode.STS | Mnemonic.Mode.CMD, Mnemonic.Type.INT, builtin=True),
Mnemonic.get('Opt2', Mnemonic.Dest.IDU, Mnemonic.Mode.STS | Mnemonic.Mode.CMD, Mnemonic.Type.INT, builtin=True),
Mnemonic.get('Opt3', Mnemonic.Dest.IDU, Mnemonic.Mode.STS | Mnemonic.Mode.CMD, Mnemonic.Type.INT, builtin=True),
Mnemonic.get('Opt4', Mnemonic.Dest.IDU, Mnemonic.Mode.STS | Mnemonic.Mode.CMD, Mnemonic.Type.INT, builtin=True),
Mnemonic.get('Pwd', Mnemonic.Dest.IDU, Mnemonic.Mode.CMD, Mnemonic.Type.STR, builtin=True),
Mnemonic.get('PwrC', Mnemonic.Dest.IDU, Mnemonic.Mode.STS, Mnemonic.Type.INT, builtin=True),
Mnemonic.get('PwrI', Mnemonic.Dest.IDU, Mnemonic.Mode.STS, Mnemonic.Type.INT, builtin=True),
Mnemonic.get('Rair', Mnemonic.Dest.IDU, Mnemonic.Mode.STS, Mnemonic.Type.INT, builtin=True),
Mnemonic.get('RlMd', Mnemonic.Dest.IDU, Mnemonic.Mode.STS, Mnemonic.Type.INT, builtin=True),
Mnemonic.get('SetT', Mnemonic.Dest.IDU, Mnemonic.Mode.STS | Mnemonic.Mode.CMD, Mnemonic.Type.FLOAT, builtin=True),
Mnemonic.get('SSID', Mnemonic.Dest.IDU, Mnemonic.Mode.CMD, Mnemonic.Type.STR, builtin=True),
Mnemonic.get('Ta', Mnemonic.Dest.ODU, Mnemonic.Mode.STS, Mnemonic.Type.FLOAT, builtin=True),
Mnemonic.get('Time', Mnemonic.Dest.IDU, Mnemonic.Mode.STS, Mnemonic.Type.STR, builtin=True),
Mnemonic.get('Tr', Mnemonic.Dest.IDU, Mnemonic.Mode.STS, Mnemonic.Type.FLOAT, builtin=True),
Mnemonic.get('WSt', Mnemonic.Dest.IDU, Mnemonic.Mode.STS | Mnemonic.Mode.CMD, Mnemonic.Type.INT, builtin=True),
Mnemonic.get('WtmS', Mnemonic.Dest.IDU, Mnemonic.Mode.STS | Mnemonic.Mode.CMD, Mnemonic.Type.INT, builtin=True),
Mnemonics.dump()

# namespace
hlink2_ns = cg.esphome_ns.namespace("hlink2")
Core = hlink2_ns.class_("Core", cg.Component, uart.UARTDevice)
CONF_HLINK2_ID = 'hlink2_id'
CONF_RAC_HANDSHAKE = 'rac_handshake'
CONF_FACTORY_SSID = 'factory_ssid'
CONF_FACTORY_KEY = 'factory_key'
CONF_PREMIUM_POLLING = 'premium_polling'


def add_mnemonic(conf):
    try:
        mnemonic = Mnemonic.get(conf[CONF_NAME], conf[CONF_DEST], conf[CONF_MODE], None, builtin=False)  # conf[CONF_TYPE]
    except Exception as e:
        raise cv.Invalid(e)
    Mnemonics.dump()
    return conf


def validate_mode(value) -> int:
    if isinstance(value, str):
        names = [value]
    else:
        names = cv.ensure_list(cv.string)(value)
    mode = Mnemonic.Mode.NONE
    for name in names:
        try:
            mode |= Mnemonic.Mode.get(name)
        except ValueError as e:
            raise cv.Invalid(f"Invalid Mnemonic Mode {value}, allowed values: {[m.name for m in Mnemonic.Mode]}")
    return int(mode)


 
CONFIG_SCHEMA = cv.All(
    cv.Schema({
        cv.GenerateID(): cv.declare_id(Core),
    })
    .extend({
        cv.Optional(CONF_PARAMETERS, default={}): cv.Schema({
            cv.Optional('uart_tx_chunck_size'): cv.All(cv.positive_int, cv.Range(4, 128)),
            cv.Optional('message_mnemonics_capacity'): cv.All(cv.positive_int, cv.Range(3, 19)),
            cv.Optional('task_timeout'): cv.All(
                cv.positive_time_period, cv.Range(core.TimePeriod(milliseconds=10), core.TimePeriod(milliseconds=40))
            ),
            cv.Optional('message_update_interval'): cv.All(
                cv.positive_time_period, cv.Range(core.TimePeriod(seconds=2), core.TimePeriod(days=7))
            ),
            cv.Optional('sensor_update_interval'): cv.All(
                cv.positive_time_period, cv.Range(core.TimePeriod(seconds=2), core.TimePeriod(days=7))
            ),
            cv.Optional('text_sensor_update_interval'): cv.All(
                cv.positive_time_period, cv.Range(core.TimePeriod(seconds=2), core.TimePeriod(days=7))
            ),
            cv.Optional('message_update_timeout'): cv.All(
                cv.positive_time_period, cv.Range(core.TimePeriod(milliseconds=100), core.TimePeriod(seconds=5))
            ),
        })
    })
    .extend({
        cv.Optional(CONF_MNEMONICS, default=[]): cv.ensure_list(
            cv.All(cv.Schema({
                cv.Required(CONF_NAME): cv.string,
                cv.Required(CONF_MODE): validate_mode,
                cv.Required(CONF_DEST): cv.one_of(*[d.name for d in Mnemonic.Dest]),
                cv.Optional(CONF_LAMBDA): cv.lambda_,
            }), add_mnemonic)
        ),
        cv.Optional(CONF_RAC_HANDSHAKE): cv.Schema({
            cv.Required(CONF_FACTORY_SSID): cv.string_strict,
            cv.Required(CONF_FACTORY_KEY): cv.string_strict,
            cv.Optional(CONF_PREMIUM_POLLING, default=False): cv.boolean,
        }),
    })
    .extend(uart.UART_DEVICE_SCHEMA),
)


# code generation
async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)

    # custom mnemonics
    for i, m in enumerate(config.get(CONF_MNEMONICS, [])):
        mnemonic = Mnemonic.get(m[CONF_NAME], m[CONF_DEST], m[CONF_MODE], None, builtin=False)  # m[CONF_TYPE]
        if mnemonic.builtin:
            name = f'esphome::hlink2::Mnemonic::{mnemonic.id}'
        else:
            name = f'esphome::hlink2::Mnemonic::custom_Mnemonics[{Mnemonics.index(mnemonic)}]'

        if m.get(CONF_LAMBDA):
            cg.add(cg.RawExpression(f'{name}.add_callback([mnemonic=&{name}](){{ {m[CONF_LAMBDA]} }});'))

    if CONF_RAC_HANDSHAKE in config:
        rac = config[CONF_RAC_HANDSHAKE]
        cg.add(var.set_rac_factory_credentials(
            rac[CONF_FACTORY_SSID],
            rac[CONF_FACTORY_KEY],
        ))
        cg.add(var.set_rac_premium_polling_enabled(
            rac[CONF_PREMIUM_POLLING],
        ))

    # parameters
    for name, value in config.get(CONF_PARAMETERS, {}).items():
        if isinstance(value, core.TimePeriod):
            cg.add_define('CONF_'+name.upper(), value.total_milliseconds)
        else:
            cg.add_define('CONF_'+name.upper(), value)

    
    Mnemonics.dump()
    Mnemonics.to_code()
