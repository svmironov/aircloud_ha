# AirCloud Home Assistant Integration

![Logo](https://github.com/svmironov/aircloud_ha/blob/main/custom_components/air_cloud/img/icon.png?raw=true)

This integration controls Hitachi climate devices through the airCloud Home service.

This software is not affiliated with or endorsed by Hitachi or any of its affiliated companies. Use of this software is entirely at your own risk. Under no circumstances shall the author be held liable for any damage, loss of property, or harm to third parties resulting from the use of this software.

All product names, trademarks, and registered trademarks mentioned or shown in this repository are the property of their respective owners. All images in this repository are used solely for identification purposes.

## Features

* Temperature change
* Modes: HEATING, COOLING, FAN, DRY
* Swing modes: VERTICAL, HORIZONTAL, BOTH
* Energy Consumption (requires activation of "Energy Cost" in the AirCloud app).

## Installation

First install HACS if you do not have it yet. Add
https://github.com/svmironov/aircloud_ha to HACS as a custom repository.

## Configuration

You can add integration in the UI or manual in configuration.yml

```yml
    air_cloud:
        email: "login" # supported only email authorization
        password: "pass"

    climate:
       - platform: air_cloud
```

All devices are loaded from airCloud. A Home Assistant entity is created for every
device using its airCloud name.

## Sample lovelace object

```yml
      - type: thermostat
        entity: climate.kitchen_ac
```

## Usages

The integration does not currently support phone-number authorization or FrostWash.
Some modes may not be supported by every model. The airCloud API is relatively slow,
so commands and UI updates normally have a latency of one to five seconds.

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

## Fully local ESPHome mode

This repository also contains an experimental, cloud-independent universal firmware
for the original RTL8710BN Wi-Fi module used by selected Hitachi AirHome units. The
air-conditioner model entered by the user is identification metadata only; it does not
select a different firmware. Wi-Fi, API and OTA credentials are prepared by the
included setup script. This is a separate solution from the cloud integration below.

See [LOCAL_MODE.md](LOCAL_MODE.md) for the architecture, stock-pairing prerequisite,
source build, verified backup procedure, serial installation and OTA updates.

The local setup starts with:

```bash
tools/esphome/scripts/configure_local_firmware.sh
tools/esphome/scripts/build_local_firmware.sh
```

The setup script displays the ESPHome API encryption key needed by Home Assistant.
The API key and OTA password are both stored in the ignored
`tools/esphome/secrets.yaml`; the build does not print them, and the OTA helper reads
its password from that file automatically.

There is no fully local operating mode with the stock Hitachi firmware: the stock
mobile application and module depend on the Hitachi/Kii cloud and expose no discovered
LAN control API. True local control requires replacing the Wi-Fi module firmware or
adding an external HLINK/IR controller.
