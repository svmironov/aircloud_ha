# AirCloud Home Assistant Integration

This integration allows control Hitachi climate devices whit connected airCloud Home service.
For change temperature with step 0.5 recommend uses a alternative thermostat UI

## Features

* Temperature change
* Modes: HEATING, COOLING, FAN, DRY
* Swing modes: VERTICAL, HORIZONTAL, BOTH
* Energy Consumption (requires activation of "Energy Cost" in the AirCloud app).

Integration does not currently support authorization by a phone and FrostWash mode. You're a model may not support some modes, but you will see it in the UI.

AirCloud API have low performance. Execution of commands and updating the UI occurs with latency from 1 to 5 seconds

## Configuration

    air_cloud:
        email: "login" #supported only email authorization
        password: "pass"

    climate:
       - platform: air_cloud

All devices be loaded from AirCloud. For every device be created HA entity with name from AirCloud

## Sample lovelace object

    type: custom:simple-thermostat
    entity: climate.kitchen_ac
    header:  
        name: Kitchen AC
    layout:  
    mode:    
        headings: false
