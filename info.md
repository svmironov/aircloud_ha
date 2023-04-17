# AirCloud Home Assistant Integration

This integration allows control Hitachi climate devices whit connected airCloud Home service. 
For change temperature with step 0.5 recommend uses alternative thermostat UI

## Features

* Temperature change
* Support modes: HEATING, COOLING, FAN, DRY

## Configuration

    air_cloud:
        email: "login"
        password: "pass"

    climate:
       - platform: air_cloud




