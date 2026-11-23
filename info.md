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

Open **Settings → Devices & services → Add integration**, search for **AirCloud**,
and enter your airCloud account's email address and password. YAML integration
setup is no longer supported.

All devices are loaded from airCloud. A Home Assistant entity is created for every
device using its airCloud name.

If you previously configured AirCloud in YAML, remove the top-level `air_cloud:`
block and the `platform: air_cloud` entries under `climate:` and `sensor:` from
your configuration files, then restart Home Assistant and add the integration
through the interface. Keep an existing UI integration entry if you already have
one. Restore any command delay or OFF compatibility settings in its **Configure**
dialog. Dashboard and automation YAML remains supported.

## Sample lovelace object

    type: custom:simple-thermostat
    entity: climate.kitchen_ac
    header:  
        name: Kitchen AC
    layout:  
    mode:    
        headings: false
