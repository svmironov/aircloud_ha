# AirCloud Home Assistant Integration

![Logo](https://github.com/svmironov/aircloud_ha/blob/main/custom_components/air_cloud/img/icon.png?raw=true)

This integration allows control Hitachi climate devices whit connected airCloud Home service

## Features

* Temperature change
* Modes: HEATING, COOLING, FAN, DRY
* Swing modes: VERTICAL, HORIZONTAL, BOTH
* Energy Consumption (requires activation of "Energy Cost" in the AirCloud app).

## Installation

First install HACS if you don't have it yet. Add https://github.com/svmironov/aircloud_ha to HACS as user repository.

## Configuration

You can add integration in the UI or manual in configuration.yml

```yml
    air_cloud:
        email: "login" # supported only email authorization
        password: "pass"

    climate:
       - platform: air_cloud
```         

All devices be loaded from AirCloud. For every device be created HA entity with name from AirCloud

## Sample lovelace object

```yml
      - type: thermostat
        entity: climate.kitchen_ac
```

## Usages

Integration does not currently support authorization by a phone and FrostWash mode. You're a model may not support some modes, but you will see it in the UI.
AirCloud API have low performance. Execution of commands and updating the UI occurs with latency from 1 to 5 seconds

The integration provides a service for a single command: 

```yml service: air_cloud.exec_command
    data:
      id: 15187 # AirCloud ID from developer panel
      family_id: 809423 # family_id from developer panel 
      power: "OFF" # ON/OFF
      target_temp: 24 
      mode: COOLING # HEATING, COOLING, FAN, DRY or AUTO
      fan_speed: LV1 # Speed LV1-LV5 or AUTO
      fan_swing: "OFF" # VERTICAL, HORIZONTAL, BOTH or OFF
      humidity: 0 # It is magic number, select experimentally for your model from 0, 50, 2147483647
```

This software is not affiliated with or endorsed by Hitachi or any of its affiliated companies. Use of this software is entirely at your own risk. Under no circumstances shall the author be held liable for any damage, loss of property, or harm to third parties resulting from the use of this software.

All product names, trademarks, and registered trademarks mentioned or shown in this repository are the property of their respective owners. All images in this repository are used solely for identification purposes.
