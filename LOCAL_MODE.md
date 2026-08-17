# Hitachi AirHome fully local ESPHome mode

This document describes an experimental, fully local replacement firmware for the
original Hitachi AirHome Wi-Fi module. It runs ESPHome directly on the module's
Realtek RTL8710BN chip and talks to the indoor unit over HLINK2. Home Assistant then
connects directly to ESPHome over the local network; no Hitachi account, Internet
connection or cloud API is used at runtime.

This local firmware is separate from the `custom_components/air_cloud` integration in
this repository. The integration uses the stock airCloud service and remains
cloud-dependent. The firmware under `tools/esphome/` replaces that cloud path.

> [!WARNING]
> This procedure requires opening mains-powered HVAC equipment and writing firmware to
> its Wi-Fi board. Disconnect the air conditioner from mains power before removing the
> module. Never power the module from the indoor unit and a bench supply at the same
> time. Use 3.3 V logic only. You are responsible for hardware damage, loss of cloud
> access and warranty implications.

## Credits and source

The hardware access method, LibreTiny/ESPHome port, HLINK2 reverse engineering and the
original replacement-firmware work come from
[clsergent/hitachi_altwifi](https://github.com/clsergent/hitachi_altwifi). Its
[installation instructions](https://github.com/clsergent/hitachi_altwifi/blob/main/Instructions.md),
[hardware reconnaissance](https://github.com/clsergent/hitachi_altwifi/blob/main/Reconnaissance.md)
and [HLINK2 protocol draft](https://github.com/clsergent/hitachi_altwifi/blob/main/Protocol.md)
were the primary technical source for this work.

This project adds field work on RAK-DJ18PHAE and RAK-DJ25PHAE, the required one-time
stock registration, a universal HLINK2 configuration, non-blocking HLINK2 I/O,
AmebaZ UART RX fixes and long-running Home Assistant operation.

The local HLINK2 component is derived from `clsergent/hitachi_altwifi` and remains
subject to EUPL-1.2-or-later. See
[`tools/esphome/THIRD_PARTY_NOTICES.md`](tools/esphome/THIRD_PARTY_NOTICES.md).
The root MIT license does not relicense that third-party-derived code.

## Why the stock firmware cannot provide fully local control

The stock airCloud firmware has two very different communication paths:

```text
airCloud app <-> Hitachi/Kii cloud <-> stock Wi-Fi firmware
                                      |
                                      +-- UART/HLINK2 <-> indoor unit
```

The HLINK2 side is local, but it is only an internal UART link between the Wi-Fi board
and the indoor unit. The stock firmware does not expose that link as a supported or
discovered LAN API. The stock app sends commands through Hitachi/Kii services, and the
module requires cloud authentication and dynamically provisioned cloud messaging.
Blocking Internet access leaves the stock device offline; AP mode is only for
onboarding, not local climate control.

Consequently, there is no configuration switch that turns the stock firmware into an
autonomous LAN controller. The practical fully local choices are:

- replace the RTL8710BN application firmware with ESPHome, as documented here;
- install an external controller on a compatible HLINK connector;
- use an external IR transmitter, accepting limited or no state feedback;
- build an inline UART proxy if both stock cloud access and local observation are
  required.

Flashing ESPHome disables stock airCloud operation. On a correctly registered indoor
unit the blue Wi-Fi lamp can remain solid after the application firmware is replaced;
it does not mean that ESPHome is connected to the Hitachi cloud.

## How the local firmware works

The tested Wi-Fi board contains a Realtek AmebaZ `RTL8710BN` with 2 MiB flash. The
indoor unit connection uses HLINK2 over UART:

| Setting | Value |
|---|---|
| UART TX | GPIO23 |
| UART RX | GPIO18 |
| Baud rate | 9600 |
| Parity | odd |
| Data/stop bits | 8/1 |

ESPHome polls status fields and sends climate commands over HLINK2. It publishes a
native encrypted ESPHome API containing climate mode, target/current temperature,
humidity, fan, swing and selected diagnostic/energy entities.

The firmware also contains fixes found during live testing:

- bounded, non-blocking HLINK2 transmit and receive work;
- correct retry behavior after a partially sent request;
- 512-byte UART buffers for longer replies;
- AmebaZ UART RX re-enable after `UART_Init()` resets the receive path;
- protection against an ArduinoCore ring-buffer ISR/main-loop race;
- recovery that recreates the UART RX ring after an extended status stall.

## The mandatory stock-registration step

Register every physical air conditioner with the official app **before replacing the
stock firmware**:

1. Run the original firmware belonging to that exact Wi-Fi board.
2. Complete normal setup in the official airCloud application.
3. Wait until the blue Wi-Fi lamp is continuously on.
4. Confirm that the unit appears and can be controlled in the official app.
5. Do not perform the `MODE` + `ON TIMER` factory reset after this point.

This is not needed for cloud access after ESPHome is installed. It is needed because
the stock onboarding process leaves persistent state in the system:

- board-specific identity, certificates and settings live in the module's `kvs` and
  `userdata` flash regions;
- the indoor unit remembers that its built-in airCloud module has completed
  registration.

On an unregistered unit, the indoor unit repeatedly enters a ten-minute pairing
window, shows the three-flash indication and may later remove power from the Wi-Fi
board. Reproducing the visible HLINK2 registration/init frames alone did not clear that
state. A complete stock registration through the official application did. The state
survived replacement of the application firmware, after which ESPHome ran
continuously and the blue lamp stayed on.

If the board was already overwritten before official registration, restore **that
board's own full 2 MiB dump**, complete official onboarding, make another verified
post-pairing dump, and then install ESPHome again. Never use a stock dump from another
module: the final flash regions contain individual credentials and identity data.

## Universal firmware and tested hardware

There are no separate DJ18 and DJ25 builds. Both tested units run the same ESPHome
YAML, HLINK2 implementation, UART settings, entities and recovery logic. During setup
the user enters the model only to create the device's display name in ESPHome and
Home Assistant. It does not select code, protocol fields or a model feature table.

The compiled files for two installations are not necessarily byte-for-byte identical:
the unique node name, Wi-Fi credentials, API key and OTA password are embedded in each
image. Their executable firmware profile is nevertheless the same.

The universal profile has been tested on:

- Hitachi RAK-DJ18PHAE;
- Hitachi RAK-DJ25PHAE;
- Wi-Fi board with RTL8710BN and 2 MiB flash;
- six-pin indoor-unit connection carrying HLINK2.

Similar models may work, but model names alone are not sufficient. Before writing
anything, confirm:

- chip information reports `RTL8710BN`;
- real flash size is 2 MiB;
- board target is `generic-rtl8710bn-2mb-788k`;
- the connector and UART signals match the hardware documentation;
- you have two identical full backups.

## Repository layout

```text
tools/esphome/
  components/hlink2/                 local HLINK2 component
  include/hlink2_rx_fix.*            AmebaZ UART fixes
  hitachi-local.yaml                 universal production configuration
  secrets.example.yaml               generated-file format example
  scripts/configure_local_firmware.sh  identity and credential setup
  scripts/build_local_firmware.sh    reproducible source build
  scripts/backup_stock_firmware.sh   two-pass read-only backup
  scripts/flash_local_firmware.sh    guarded first serial installation
  scripts/ota_local_firmware.sh      subsequent OTA updates
```

Unit-specific research configurations are intentionally excluded from the public
workflow. Keep each physical unit's generated ESPHome node name, API key and OTA
password separate.

## Requirements

- macOS or Linux;
- [`uv`](https://docs.astral.sh/uv/) providing `uvx`;
- OpenSSL, used to generate API and OTA credentials;
- a 3.3 V USB-to-UART adapter known to work with the AmebaZ handshake;
- a stable external 3.3 V supply;
- soldered wires or suitable probes for LOG UART, ground and power;
- the module removed from and electrically disconnected from the air conditioner;
- the official app and working stock firmware for the one-time registration.

The helper scripts fetch pinned tool versions through `uvx`; a global ESPHome or
ltchiptool installation is not required.

## 1. Configure identity and Wi-Fi

Run the interactive setup from the repository root:

```bash
tools/esphome/scripts/configure_local_firmware.sh
```

It asks for:

- the indoor-unit model, for example `RAK-DJ25PHAE`;
- a unique lower-case ESPHome node name (press Enter to use the model-based default);
- the home Wi-Fi SSID;
- the home Wi-Fi password, entered without echo.

The model becomes `friendly_name` only. The script does not choose a model-specific
firmware. It writes the entered Wi-Fi credentials to the private
`tools/esphome/secrets.yaml` file and generates a fresh ESPHome API encryption key,
OTA password and disabled fallback-AP password.

The setup script prints the ESPHome API encryption key when it finishes. It does not
print the OTA password, and the build script prints neither credential. Both values
remain available in the private `secrets.yaml` file:

```bash
grep -E 'api_encryption_key|ota_password' tools/esphome/secrets.yaml
```

Use `api_encryption_key` when Home Assistant asks for the ESPHome encryption key.
The OTA helper reads `ota_password` automatically from `secrets.yaml`; it normally
does not need to be copied or entered manually. Treat both values as secrets and do
not paste their output into issue reports or public logs.

For automation, the same values can be supplied with `--model`, `--name`,
`--wifi-ssid` and `--wifi-password`, or with the environment variables shown by
`--help`. Interactive password entry is preferable because a command-line password
can remain in shell history.

`secrets.yaml`, `backups/`, `dist/` and `artifacts/` are ignored by Git. Never publish:

- `secrets.yaml`;
- stock flash dumps;
- serial logs containing credentials;
- UF2 files built from real secrets.

ESPHome embeds Wi-Fi, API and OTA credentials in the firmware image. Public releases
should therefore contain source, scripts and `secrets.example.yaml`, not a personal
prebuilt UF2.

The repository `.gitignore` also excludes captured cloud traffic, decompiled vendor
applications, stock firmware, unit-specific development notes and local test output.
Review `git status --untracked-files=all` before every public commit; ignore rules are
not a substitute for inspecting the actual diff.

Run the setup again with `--force` when intentionally replacing a configuration.
Save a private copy of each unit's `secrets.yaml` before configuring another physical
unit; the API and OTA credentials are unique per generated installation.

## 2. Complete official stock onboarding

While the original firmware is still installed:

1. Initialize pairing only if necessary.
2. Add the air conditioner in the official application.
3. Wait for a continuously lit blue Wi-Fi lamp.
4. Confirm control and state feedback in the official application.
5. Power-cycle the air conditioner and verify that it skips AP pairing.

Only continue when this succeeds. Installing ESPHome first and attempting to imitate
cloud registration later did not prevent the indoor unit from timing out and removing
module power.

## 3. Enter AmebaZ download mode

The original hardware procedure is documented by
[`clsergent/hitachi_altwifi`](https://github.com/clsergent/hitachi_altwifi/blob/main/Instructions.md).
The practical sequence used here is:

1. Disconnect the Wi-Fi board from the air conditioner.
2. Connect USB-UART RX to module LOG_TX/PA30.
3. Connect USB-UART TX to module LOG_RX/PA29.
4. Connect grounds.
5. Use a dedicated stable 3.3 V supply for the module.
6. Hold LOG_TX/PA30 low.
7. Apply module power.
8. Release LOG_TX/PA30.

Do not connect 5 V logic or power. Do not connect bench power while the board remains
powered by the indoor unit.

## 4. Make and verify two stock backups

From the repository root:

```bash
tools/esphome/scripts/backup_stock_firmware.sh \
  /dev/cu.usbmodemYOUR_PORT \
  tools/esphome/backups/before-local-mode
```

The script reads all `0x200000` bytes twice at 115200 baud, verifies both sizes,
compares them byte-for-byte and writes SHA-256 files. It refuses to overwrite an
existing backup directory.

Keep at least one copy outside this repository. For the most useful rollback image,
make this backup after successful official registration. An additional untouched
pre-experiment backup is recommended.

Do not continue if the two reads differ.

## 5. Build from source

Build the universal profile using the identity and credentials created in step 1:

```bash
tools/esphome/scripts/build_local_firmware.sh
```

The build is pinned to ESPHome 2026.3.3, LibreTiny 1.13.0 and the ArduinoCore-API
revision declared in the YAML. LibreTiny's linker does not correctly quote workspace
paths containing spaces, so the scripts use
`ESPHOME_DATA_DIR=/tmp/aircloud-esphome-data` by default.

Output UF2 and SHA-256 files are placed in `tools/esphome/dist/`. The filename follows
the unique `device_name` stored in `secrets.yaml`. The build helper does not display
the API encryption key or OTA password; use the command in step 1 if they need to be
retrieved again.

## 6. Install over serial

Keep the board in download mode. The guarded installer requires the two matching
backups as evidence that rollback is possible:

```bash
tools/esphome/scripts/flash_local_firmware.sh \
  /dev/cu.usbmodemYOUR_PORT \
  tools/esphome/dist/YOUR_DEVICE_NAME-local.uf2 \
  tools/esphome/backups/before-local-mode/stock-pass1.bin \
  tools/esphome/backups/before-local-mode/stock-pass2.bin
```

It checks that both dumps are identical full 2 MiB files, validates UF2 metadata,
asks for explicit confirmation and writes at 115200 baud with verification enabled.

After a successful write:

1. Remove bench power.
2. Disconnect every debug/programming wire.
3. Reinstall the board in the indoor unit.
4. Restore mains power.
5. Wait for the node to join the configured local Wi-Fi.
6. Add the discovered ESPHome device to Home Assistant using its API encryption key.

The production configuration does not start a fallback AP. Home Wi-Fi credentials
must be correct at build time.

## 7. Validate the installation

Watch logs by IP address:

```bash
ESPHOME_DATA_DIR=/tmp/aircloud-esphome-data \
uvx --from esphome==2026.3.3 esphome logs \
  tools/esphome/hitachi-local.yaml \
  --device 192.168.1.100
```

Verify:

- the node remains online;
- Home Assistant commands operate the indoor unit;
- remote-control changes return to Home Assistant;
- target and current state continue to update;
- `STS_IDU` does not enter a permanent timeout loop;
- uptime survives at least 24 hours;
- the indoor unit does not return to three-flash pairing or remove module power.

If no valid HLINK2 status is received for three minutes, current builds recreate the
UART software RX ring without rebooting the complete ESP. The recovery log is:

```text
stall guard restarted UART0
```

## 8. OTA updates

After the first serial installation, use:

```bash
tools/esphome/scripts/ota_local_firmware.sh \
  192.168.1.100
```

The helper builds the universal YAML with the current private configuration and
uploads it to the explicit address. Using the complete `esphome run` flow avoids
accidentally uploading a diagnostic image left in a shared build directory.
The OTA password is loaded from `secrets.yaml` automatically.

## 9. Restore the original firmware

Use only a verified full dump from the same physical board:

```bash
uvx --from ltchiptool ltchiptool flash write \
  -d /dev/cu.usbmodemYOUR_PORT \
  -b 115200 \
  -f ambz \
  -s 0x0 \
  tools/esphome/backups/before-local-mode/stock-pass1.bin
```

This is a full-flash restore, including individual `kvs` and `userdata` regions. A UF2
application image is not a substitute for a personal full backup.

After restoration, remove all programming connections before reinstalling the module.
If the restored dump predates official registration, complete pairing in the official
application again.

## Troubleshooting

### Three blue flashes or module power disappears

The indoor unit is still in AP/pairing state. Restore the module's own stock dump,
complete official application registration, verify solid blue after a power cycle,
make a new paired-stock backup, and reinstall ESPHome. Repeated `WSt` messages are not
a substitute for the official one-time registration.

### Commands work but state updates stop

This is the characteristic UART RX failure fixed in the current source. Rebuild the
latest configuration and verify that `HLINK2_UART_RX_IRQ_GUARD` and the 512-byte serial
buffer remain enabled. Commands use TX directly, so working commands do not prove that
the RX ring is healthy.

### No setup access point appears

The production configuration deliberately sets `ap_timeout: 0s` to preserve memory
and avoid an unrecoverable AmebaZ AP state. Correct home Wi-Fi credentials must be
entered through `configure_local_firmware.sh` before compiling. Run the script again
and reinstall over serial if those credentials are wrong.

### Stock app no longer controls the unit

Expected. ESPHome replaces the stock application and does not connect to Hitachi/Kii.
Home Assistant talks directly to the local ESPHome API.

## Known limitations

- Only the listed models and boards have been tested. The model label entered during
  setup does not prove hardware compatibility.
- The implementation is based on reverse engineering and remains experimental.
- Stock airCloud and local ESPHome cannot run simultaneously on the same firmware.
- Some model-specific functions and presets are unavailable; the universal profile
  intentionally exposes only the common tested controls.
- FrostWash has not been mapped to a usable HLINK2 mnemonic on these units.
- A solid blue lamp under ESPHome does not indicate a real Hitachi cloud session.

## Contributing test results

Do not attach stock dumps, `secrets.yaml`, factory keys, API keys or complete serial
logs containing credentials. Useful reports include:

- exact indoor-unit model;
- Wi-Fi board photos and non-secret markings;
- RTL chip information with MAC address redacted;
- ESPHome project version;
- relevant HLINK2 log excerpts;
- uptime and whether stock registration was completed before flashing.

When reusing or modifying the local HLINK2 implementation, preserve attribution to
[clsergent/hitachi_altwifi](https://github.com/clsergent/hitachi_altwifi) and comply
with its EUPL-1.2-or-later license.
