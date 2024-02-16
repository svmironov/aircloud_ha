# AirCloud Home Assistant Integration

![Logo](https://github.com/svmironov/aircloud_ha/blob/main/custom_components/aircloud/img/icon.png?raw=true)

This integration allows control Hitachi climate devices whit connected airCloud Home service.

## Features

* Temperature change
* Modes: HEATING, COOLING, FAN, DRY
* Swing modes: VERTICAL, HORIZONTAL, BOTH

## Installation

First install HACS if you don't have it yet. Add https://github.com/svmironov/aircloud_ha to HACS as user repository.

## Configuration

You can add integration in the UI or manual in configuration.yml

    air_cloud:
        email: "login" # supported only email authorization
        password: "pass"
        temp_adjust: -1 # optional parameter for adjustment current temp

    climate:
       - platform: air_cloud

All devices be loaded from AirCloud. For every device be created HA entity with name from AirCloud

## Sample lovelace object

      - type: thermostat
        entity: climate.kitchen_ac

## Usages

Integration does not currently support authorization by a phone and FrostWash mode. You're a model may not support some modes, but you will see it in the UI.
AirCloud API have low performance. Execution of commands and updating the UI occurs with latency from 1 to 5 seconds

The integration provides a service for a single command: 

    service: air_cloud.exec_command
    data:
      id: 15187 # AirCloud ID from developer panel 
      power: "OFF" # ON/OFF
      target_temp: 24 
      mode: COOLING # HEATING, COOLING, FAN, DRY or AUTO
      fan_speed: LV1 # Speed LV1-LV5 or AUTO
      fan_swing: "OFF" # VERTICAL, HORIZONTAL, BOTH or OFF
      humidity: 0 # It is magic number, select experimentally for your model from 0, 50, 2147483647

All product names, trademarks and registered trademarks in the images in this repository, are property of their respective owners. All images in this repository are used by the project for identification purposes only.
