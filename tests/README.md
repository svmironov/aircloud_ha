# Offline regression tests

The historical manual patch was also tested in a real Home Assistant installation
in Brazil, identified by its owner as version 2.2.8, and kept physical AC control
working. The owner confirmed this on 20 October 2026. The limitations below
describe this automated suite and the new implementation, not that historical
field test. See the validation notes in [README.MD](../README.MD).

From the repository root, with Python 3.12 or later:

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements-test.txt
.venv/bin/python -m unittest discover -s tests -v
```

The tests import and execute the actual integration modules. `aiohttp` sends real
HTTP requests to an ephemeral loopback server; no AirCloud account or external
network is used. Home Assistant import types/constants are supplied by the small
`ha_boundary.py` fixture only if Home Assistant is not installed. This keeps
these tests independent of a running Home Assistant installation, but it does
**not** validate entity registration, config entry reloads, the Home Assistant
service dispatcher, HACS installation, cloud acceptance or physical AC behavior.
The follow-up WebSocket snapshot is substituted at the API boundary in climate
command tests. Token and command HTTP responses are deliberately synthetic.

Tests include malformed/expired token recovery, atomic credential updates,
concurrent refresh and forced-login coalescing, transient-error handling, failed
command state preservation, cancellation, successful command behavior, closed
sessions, and preservation of the default RAC payload including half degrees.
A successful HTTP response in these tests proves local request handling only.

The options tests exercise selection defaults/persistence with HA form boundary
fixtures; they do not render the frontend. Compatibility tests verify that only
selected RAC OFF requests change, while ON, fractional temperatures, other RAC
units, GPAC and Yutampo keep their original payloads.
