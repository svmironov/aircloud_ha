# Third-party notices for the local ESPHome firmware

## `clsergent/hitachi_altwifi`

The HLINK2 implementation under `components/hlink2/`, the RTL8710BN replacement
firmware approach, hardware access information and protocol reverse-engineering
foundation are derived from:

- Project: [`clsergent/hitachi_altwifi`](https://github.com/clsergent/hitachi_altwifi)
- Author: clsergent and project contributors
- Upstream license: EUPL-1.2-or-later
- License text: [European Union Public Licence 1.2](https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12)

The local copy contains additional modifications for ESPHome compatibility, bounded
I/O, startup sequencing, protocol diagnostics and AmebaZ UART reliability. The public
firmware uses one common configuration for every compatible model.

Those upstream-derived files remain under EUPL-1.2-or-later. The MIT license at the
repository root applies to the original AirCloud Home Assistant integration and other
MIT-covered project code; it does not relicense EUPL-covered material.

## Other projects

The firmware is built with ESPHome, LibreTiny, ArduinoCore-API and their transitive
dependencies. Their respective source distributions and build metadata contain the
applicable copyright and license terms.
