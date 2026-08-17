from esphome import core
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import (
    CONF_CUSTOM,
    CONF_DEST,
    CONF_HIGH,
    CONF_LAMBDA,
    CONF_LOW,
    CONF_MAX_VALUE,
    CONF_MEDIUM,
    CONF_MIN_VALUE,
    CONF_MODE,
    CONF_NAME,
    CONF_QOS,
    CONF_STEP,
    CONF_UPDATE_INTERVAL,
)


from .mnemonics import (
    Mnemonics,
    Mnemonic,
)

CONF_AIRFLOW = "airflow"
CONF_BUZZER = "buzzer"
CONF_FILTER_USAGE = "filter_usage"
CONF_FILTER_RESET = "filter_reset"
CONF_FLAG = "flag"
CONF_HVAC_ACTIONS = "hvac_actions"
CONF_INDOOR_EXCHANGER_TEMPERATURE = "indoor_exchanger"
CONF_INDOOR_TEMPERATURE = "indoor_temperature"
CONF_INDOOR_HUMIDITY = "indoor_humidity"
CONF_LED_WIFI = "led_wifi"
CONF_LED_TIMER = "led_timer"
CONF_MNEMONIC = "mnemonic"
CONF_MNEMONICS = "mnemonics"
CONF_OUTDOOR_EXCHANGER_TEMPERATURE = "outdoor_exchanger"
CONF_OUTDOOR_TEMPERATURE = "outdoor_temperature"
CONF_PROMOTE = "promote"
CONF_REMOTE_LOCK = "remote_lock"
CONF_STATUS_MESSAGE = "status_message"
CONF_TARGET_TEMPERATURE = "target_temperature"
CONF_COMMAND_MESSAGE = "command_message"

MNEMONIC_AIRFLOW = "IDU_Rair"
MNEMONIC_ENERGY = "IDU_PwrC"
MNEMONIC_POWER = "IDU_PwrI"
MNEMONIC_INDOOR_EXCHANGER_TEMPERATURE = "IDU_HExT"
MNEMONIC_INDOOR_TEMPERATURE = "IDU_Tr"
MNEMONIC_INDOOR_HUMIDITY = "IDU_Hr"
MNEMONIC_MODEL = "IDU_Modl"
MNEMONIC_OUTDOOR_EXCHANGER_TEMPERATURE = "ODU_HExT"
MNEMONIC_OUTDOOR_TEMPERATURE = "ODU_Ta"
MNEMONIC_PASSWORD = "IDU_Pwd"
MNEMONIC_SSID = "IDU_SSID"
MNEMONIC_FILTER_USAGE = "IDU_FltT"
MNEMONIC_FILTER_STATUS = "IDU_FilS"
MNEMONIC_OPT1 = "IDU_Opt1"
MNEMONIC_TARGET_TEMPERATURE = "IDU_SetT"
MNEMONIC_BUZZER = "IDU_Buzz"
MNEMONIC_LED_WIFI = "IDU_WSt"
MNEMONIC_LED_TIMER = "IDU_WtmS"

ICON_BELL = "mdi:bell"
ICON_FILTER = "mdi:air-filter"
ICON_FORM = "mdi:form-textbox"
ICON_INFORMATION = "mdi:information-outline"
ICON_LED = "mdi:led-outline"
ICON_LED_ON = "di:led-on"
ICON_LED_OFF = "mdi:led-variant-off"
ICON_LIGHTNING_BOLT = "mdi:lightning-bolt"
ICON_PASSWORD = "mdi:form-textbox-password"
ICON_POWER_PLUG = "mdi:power-plug"
ICON_REMOTE_OFF = "mdi:remote-off"
ICON_SPROUT = "mdi:sprout"
ICON_TARGET_TEMPERATURE = "mdi:thermometer-plus"

UNIT_LITRE_SECOND = "L/s"

VALUES_QOS = [CONF_HIGH, CONF_MEDIUM, CONF_LOW]


def scope(ns, *values) -> str:
    scopes = [str(ns)]
    scopes.extend(values)
    return "::".join(scopes)


# --- CODE VALIDATION ---

def config_schema(parent_id, parent_type, *component_type, **conponents_config) -> cv.Schema:
    """create components schema"""
    return cv.Schema({   
        **{cv.GenerateID(): cv.declare_id(typ) for typ in component_type},
        cv.GenerateID(parent_id): cv.use_id(parent_type),
    }).extend({cv.Optional(type): schema for type, schema in conponents_config.items()})


def validate_flag(config: dict | str):
    """ validate message flag """
    if isinstance(config, str):
        values = config.split("_")
        if len(values) != 2:
            raise cv.Invalid(f"Invalid flag {config}")
        mode = values[0]
        dest = values[1]
    elif isinstance(config, dict):
        mode = config[CONF_MODE]
        dest = config[CONF_DEST]
    else:
        raise cv.Invalid("Invalid flag format")
    
    errors = []
    if mode not in (modes := [m.name for m in Mnemonics.Mode]):
        errors.append(f'Invalid "mode" field, valid values: {modes}')
    if dest not in (dests := [d.name for d in Mnemonic.Dest]):
        errors.append(f'Invalid "dest" field, valid values: {dests}')

    if errors:
        raise cv.Invalid('\n'.join(errors))

    return f'{mode}_{dest}'

def validate_mnemonic(config: dict | str, *modes):
    """ validate mnemonic schema """
    errors = []

    if isinstance(config, dict):
        if config[CONF_DEST] not in (dests := [dest.name for dest in Mnemonic.Dest]):
            errors.append(f'Invalid "dest" field, valid values: {dests}')
        if config[CONF_NAME] not in (mn := [m.name for m in Mnemonics]):
            errors.append(f'Invalid "name" field, valid values: {mn}')

        config = f'{config[CONF_DEST]}_{config[CONF_NAME]}'

    if not errors:
        Mnemonics.load()
        mnemonic = Mnemonics.find(config)

        if mnemonic == Mnemonic.NONE:
            errors.append(f'{config} is not a valid mnemonic {[m.id for m in Mnemonics]}')

        for mode in modes:
            if mnemonic.mode & mode != mode:
                errors.append(f"{config} mnemonic doesn't handle mode {Mnemonic.Mode(mode).name}")

    if errors:
        raise cv.Invalid('\n'.join(errors))
        
    return config

def validate_component_type(config):
    raise ValueError("unused function")
    """validate with alternative classes, with schema type being a list[type0, type1]"""
    mnemonic = Mnemonics.find(config.get(CONF_MNEMONIC, ""))
    if Mnemonic.Mode.CMD & mnemonic.mode != Mnemonic.Mode.CMD:
        raise cv.Invalid("Mnemonic must handle CMD mode")
    if isinstance(config['id'].type, (list, tuple)) and len(config['id'].type) == 2:
        if Mnemonic.Mode.STS & mnemonic.mode == Mnemonic.Mode.STS:
            config['id'].type = config['id'].type[1]
        else:
            config['id'].type = config['id'].type[0]
    return config


def format_mnemonic(config: dict| str):
    if isinstance(config, dict):
        config = f'{config[CONF_DEST]}_{config[CONF_NAME]}'
    return config

SCHEMA_MNEMONIC_CUSTOM = cv.Schema({
    cv.Required(CONF_MNEMONIC): cv.All(
        cv.Any(
            cv.string,
            cv.Schema({
                cv.Required(CONF_NAME): cv.string,
                cv.Required(CONF_DEST): cv.string,
            }),
        ),
        format_mnemonic,
    )
})


SCHEMA_FLAG =cv.Schema({
    cv.Required(CONF_FLAG): cv.templatable(cv.All(
        cv.Any(
            cv.string,
            cv.Schema({
                cv.Required(CONF_MODE): cv.All(
                    cv.string,
                    cv.one_of([i.name for i in Mnemonic.Mode if i.name != "NONE"])
                ),
                cv.Required(CONF_DEST): cv.All(
                    cv.string,
                    cv.one_of([i.name for i in Mnemonic.Mode if i.name != "NONE"])
                ),
            })
        ),
        validate_flag,
    ))
})

def schema_mnemonic(name, dest=None):
    if dest:
        default = validate_mnemonic({
            CONF_NAME: name,
            CONF_DEST: dest
        })
    else:
        default = validate_mnemonic(name)
    return cv.Schema({cv.Optional(CONF_MNEMONIC, default=default): cv.one_of(default)})


SCHEMA_QOS = cv.Schema({
    cv.Optional(CONF_QOS): cv.All(
        cv.one_of(*VALUES_QOS),
        lambda qos: "QOS_"+ qos.upper()
    )
})


def validate_number(config: dict) -> dict:
    if config[CONF_MIN_VALUE] >= config[CONF_MAX_VALUE]:
        raise cv.Invalid('min must be lower than max')
    if config[CONF_MIN_VALUE] % config[CONF_STEP] or config[CONF_MAX_VALUE] % config[CONF_STEP]:
        raise cv.Invalid('min and max values must match step')
    return config


def schema_number(mins: list, maxs: list, steps: list):
    return cv.All(
    cv.Schema({
        cv.Optional(CONF_MIN): cv.Range(*mins),
        cv.Optional(CONF_MAX): cv.Range(*maxs),
        v.Optional(CONF_STEP): cv.one_of(*steps),
    }),
    validate_number
)


SCHEMA_MESSAGE_CMD_PARAMS = cv.Schema({
    cv.Optional(CONF_BUZZER): cv.boolean,
    cv.Optional(CONF_LAMBDA): cv.lambda_,
}).extend(SCHEMA_QOS)


SCHEMA_MESSAGE_STS_PARAMS = cv.Schema({
    cv.Optional(CONF_UPDATE_INTERVAL): cv.All(
        cv.positive_time_period,
        cv.Range(core.TimePeriod(seconds=2), core.TimePeriod(hours=24)),
        (lambda a: a.total_milliseconds)
    ),
    cv.Optional(CONF_LAMBDA): cv.lambda_,
}).extend(SCHEMA_QOS)


SCHEMA_MNEMONIC_PARAMS = cv.Schema({
    cv.Optional(CONF_PROMOTE): cv.boolean,
}).extend(SCHEMA_MESSAGE_STS_PARAMS)


# --- FINAL VALIDATION ---


def final_validate_status_menmonics(config: dict):
    errors = []
    for platform in config.values():
        if isinstance(platform, dict) and (conf := platform.get(CONF_MNEMONIC)):
            try:
                validate_mnemonic(conf, mode=Mnemonic.Mode.STS)
            except cv.Invalid as e:
                errors.append(str(e))
    
    if errors:
        raise cv.Invalid("\n".join(errors))
    
    return config

def final_validate_mnemonics(config: dict, *modes):
    """ validate mnemonics and their required modes """
    errors = []
    for platform in config.values():
        if isinstance(platform, dict) and (conf := platform.get(CONF_MNEMONIC)):
            try:
                validate_mnemonic(conf, *modes)
            except cv.Invalid as e:
                errors.append(str(e))
    
    if errors:
        raise cv.Invalid("\n".join(errors))
    
    return config

FINAL_VALIDATE_SCHEMA = cv.All(final_validate_mnemonics)

# --- CODE GENERATION ---

def generate_lambda(config: dict, *args, capture_="", **kwargs) -> cg.RawExpression | None:
    if lambda_ := config.get(CONF_LAMBDA):
        if len(args) + len(kwargs):
            capture_ += ','.join(list(args) + [f'{key}={value}' for key, value in kwargs.items()])
        return cg.RawExpression(f'[{capture_}]() {{ {lambda_} }}')
    else:
        return None

def generate_mnemonic(ns, config: dict) -> cg.RawExpression | None:
    if mnemonic_id := config.get(CONF_MNEMONIC):
        if mnemonic := Mnemonics.find(mnemonic_id):
            if mnemonic.builtin:
                return cg.RawExpression("&" + scope(ns, "Mnemonic", config[CONF_MNEMONIC]))
            else:
                index = Mnemonics.index(mnemonic)
                return cg.RawExpression("&" + scope(ns, "Mnemonic", f'custom_Mnemonics[{index}]'))
        else:
            print(f'failed to find mnemonic for id {mnemonic_id}')
    return None


def generate_qos(ns, config: dict) -> cg.RawExpression | None:
    if mnemonic_id := config.get(CONF_QOS):
        return cg.RawExpression(scope(ns, "Message", "QoS", config[CONF_QOS]))
    return None


def generate_MessageParameters(ns, config: dict) -> cg.StructInitializer:
    """configure MessageParameters from a configuration dict"""
    if config is None:
        config = dict()
    params = cg.StructInitializer(
        ns.struct("MessageParameters"),
        (CONF_UPDATE_INTERVAL, config.get(CONF_UPDATE_INTERVAL)),
        (CONF_QOS, generate_qos(ns, config)),
        (CONF_BUZZER, config.get(CONF_BUZZER)),
    )
    return params


def generate_arguments(*args):
    """return the list of valid (ie not None) arguments""" 
    return [arg for arg in args if arg is not None]
