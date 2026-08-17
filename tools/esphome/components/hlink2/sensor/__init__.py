import esphome.config_validation as cv
import esphome.codegen as cg
from esphome.components import sensor
from esphome.const import (
    CONF_ID,
    CONF_NAME,
    CONF_LAMBDA,
    CONF_CUSTOM,
    CONF_DEST,
    CONF_ENERGY,
    CONF_POWER,
    CONF_UPDATE_INTERVAL,
    DEVICE_CLASS_DURATION,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_TEMPERATURE,
    ENTITY_CATEGORY_DIAGNOSTIC,
    STATE_CLASS_MEASUREMENT,
    STATE_CLASS_TOTAL_INCREASING,
    UNIT_CELSIUS,
    UNIT_HOUR,
    UNIT_PERCENT,
    UNIT_WATT,
    UNIT_WATT_HOURS,
    ICON_HEATING_COIL,
    ICON_THERMOMETER,
    ICON_WATER_PERCENT,
    ICON_BUG,
    ICON_FAN,
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
    CONF_AIRFLOW,
    CONF_FILTER_USAGE,
    CONF_MNEMONIC,
    CONF_PROMOTE,
    CONF_OUTDOOR_EXCHANGER_TEMPERATURE,
    CONF_OUTDOOR_TEMPERATURE,
    CONF_INDOOR_EXCHANGER_TEMPERATURE,
    CONF_INDOOR_TEMPERATURE,
    CONF_INDOOR_HUMIDITY,
    CONF_TARGET_TEMPERATURE,
    ICON_FILTER,
    ICON_LIGHTNING_BOLT,
    ICON_POWER_PLUG,
    ICON_TARGET_TEMPERATURE,
    MNEMONIC_AIRFLOW,
    MNEMONIC_ENERGY,
    MNEMONIC_FILTER_USAGE,
    MNEMONIC_INDOOR_EXCHANGER_TEMPERATURE,
    MNEMONIC_INDOOR_TEMPERATURE,
    MNEMONIC_INDOOR_HUMIDITY,
    MNEMONIC_OUTDOOR_EXCHANGER_TEMPERATURE,
    MNEMONIC_OUTDOOR_TEMPERATURE,
    MNEMONIC_POWER,
    MNEMONIC_TARGET_TEMPERATURE,
    SCHEMA_MNEMONIC_PARAMS,
    SCHEMA_MNEMONIC_CUSTOM,
    FINAL_VALIDATE_SCHEMA,
    UNIT_LITRE_SECOND,
)


DEPENDENCIES = ['sensor', 'hlink2']
CODEOWNERS = CODEOWNERS

Sensor = hlink2_ns.class_('Sensor', sensor.Sensor, cg.Component)

COMPONENTS_CONFIG = {
    CONF_OUTDOOR_TEMPERATURE: sensor.sensor_schema(
        Sensor,
        unit_of_measurement=UNIT_CELSIUS,
        icon='mdi:sun-thermometer',
        accuracy_decimals=0,
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
    ).extend(SCHEMA_MNEMONIC_PARAMS)
    .extend(schema_mnemonic(MNEMONIC_OUTDOOR_TEMPERATURE)),
    
    CONF_INDOOR_TEMPERATURE : sensor.sensor_schema(Sensor,
        unit_of_measurement=UNIT_CELSIUS,
        icon=ICON_THERMOMETER,
        accuracy_decimals=1,
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
    ).extend(SCHEMA_MNEMONIC_PARAMS)
    .extend(schema_mnemonic(MNEMONIC_INDOOR_TEMPERATURE)),
    
    CONF_INDOOR_HUMIDITY: sensor.sensor_schema(Sensor,
        unit_of_measurement=UNIT_PERCENT,
        icon=ICON_WATER_PERCENT,
        accuracy_decimals=0,
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
    ).extend(SCHEMA_MNEMONIC_PARAMS)
    .extend(schema_mnemonic(MNEMONIC_INDOOR_HUMIDITY)),

    CONF_AIRFLOW: sensor.sensor_schema(Sensor,
        unit_of_measurement=UNIT_LITRE_SECOND,
        icon=ICON_FAN,
        accuracy_decimals=0,
        device_class="",
        state_class=STATE_CLASS_MEASUREMENT,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
    ).extend(SCHEMA_MNEMONIC_PARAMS)
    .extend(schema_mnemonic(MNEMONIC_AIRFLOW)),

    CONF_ENERGY: sensor.sensor_schema(Sensor,
        unit_of_measurement=UNIT_WATT_HOURS,
        icon=ICON_LIGHTNING_BOLT,
        accuracy_decimals=0,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=STATE_CLASS_TOTAL_INCREASING,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
    ).extend(SCHEMA_MNEMONIC_PARAMS)
    .extend(schema_mnemonic(MNEMONIC_ENERGY)),

    CONF_POWER: sensor.sensor_schema(Sensor,
        unit_of_measurement=UNIT_WATT,
        icon=ICON_POWER_PLUG,
        accuracy_decimals=0,
        device_class=DEVICE_CLASS_POWER,
        state_class=STATE_CLASS_MEASUREMENT,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
    ).extend(SCHEMA_MNEMONIC_PARAMS)
    .extend(schema_mnemonic(MNEMONIC_POWER)),

    CONF_TARGET_TEMPERATURE: sensor.sensor_schema(Sensor,
        unit_of_measurement=UNIT_CELSIUS,
        icon=ICON_TARGET_TEMPERATURE,
        accuracy_decimals=1,
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
    ).extend(SCHEMA_MNEMONIC_PARAMS)
    .extend(schema_mnemonic(MNEMONIC_TARGET_TEMPERATURE)),

    CONF_INDOOR_EXCHANGER_TEMPERATURE: sensor.sensor_schema(Sensor,
        unit_of_measurement=UNIT_CELSIUS,
        icon=ICON_HEATING_COIL,
        accuracy_decimals=0,
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
    ).extend(SCHEMA_MNEMONIC_PARAMS)
    .extend(schema_mnemonic(MNEMONIC_INDOOR_EXCHANGER_TEMPERATURE)),

    CONF_OUTDOOR_EXCHANGER_TEMPERATURE: sensor.sensor_schema(Sensor,
        unit_of_measurement=UNIT_CELSIUS,
        icon=ICON_HEATING_COIL,
        accuracy_decimals=0,
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
    ).extend(SCHEMA_MNEMONIC_PARAMS)
    .extend(schema_mnemonic(MNEMONIC_OUTDOOR_EXCHANGER_TEMPERATURE)),
    
    CONF_FILTER_USAGE: sensor.sensor_schema(Sensor,
        unit_of_measurement=UNIT_HOUR,
        icon=ICON_FILTER,
        accuracy_decimals=0,
        device_class=DEVICE_CLASS_DURATION,
        state_class=STATE_CLASS_TOTAL_INCREASING,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
    ).extend(SCHEMA_MNEMONIC_PARAMS)
    .extend(schema_mnemonic(MNEMONIC_FILTER_USAGE)),
    
    CONF_CUSTOM: sensor.sensor_schema(
        Sensor,
        icon=ICON_BUG,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        state_class=STATE_CLASS_MEASUREMENT,
    ).extend(SCHEMA_MNEMONIC_CUSTOM)
    .extend(SCHEMA_MNEMONIC_PARAMS), 
}


CONFIG_SCHEMA = config_schema(
    CONF_HLINK2_ID,
    Core,
    Sensor,
    **COMPONENTS_CONFIG,
)

FINAL_VALIDATE_SCHEMA = FINAL_VALIDATE_SCHEMA

async def to_code(config):
    parent = await cg.get_variable(config[CONF_HLINK2_ID])

    for name, conf in config.items():
        if name in COMPONENTS_CONFIG:
            var = await sensor.new_sensor(conf)
            cg.add(var.set_parent(parent))
            await cg.register_component(var, conf)

            mnemonic_cg = generate_mnemonic(hlink2_ns, conf)
            params_cg = generate_MessageParameters(hlink2_ns, conf)
            
            if lambda_cg := generate_lambda(conf, mnemonic=str(mnemonic_cg), sensor=var):
                cg.add(var.set_mnemonic(*generate_arguments(mnemonic_cg, lambda_cg, params_cg, conf.get(CONF_PROMOTE))))
            else:
                cg.add(var.set_mnemonic_default(*generate_arguments(mnemonic_cg, params_cg, conf.get(CONF_PROMOTE))))
    