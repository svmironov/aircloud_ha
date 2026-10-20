# Offline regression tests

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
