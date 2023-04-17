# AirCloud Home Assistant Integration

This integration allows control Hitachi climate devices whit connected airCloud Home service.
For change temperature with step 0.5 recommend uses alternative thermostat UI

## Features

* Temperature change
* Support modes: HEATING, COOLING, FAN, DRY

## Installation

First install HACS if you don't have it yet. Add https://github.com/svmironov/aircloud_ha to HACS as user repository.

## Configuration

    air_cloud:
        email: "login"
        password: "pass"

    climate:
       - platform: air_cloud




