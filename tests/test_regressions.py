"""Behavioral regressions with real integration code and a loopback HTTP server."""
import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
from aiohttp import web
from aiohttp.test_utils import TestServer

from tests import ha_boundary  # noqa: F401 -- install only absent HA import types
from homeassistant.exceptions import HomeAssistantError
from custom_components.air_cloud import api as api_module
from custom_components.air_cloud import climate as climate_module
from custom_components.air_cloud.const import URN_AUTH, URN_REFRESH_TOKEN, URN_CONTROL_STATUS


OLD_PAIR = ("old-access-token", "old-refresh-token")
NEW_PAIR = ("new-access-token", "new-refresh-token")
NEW_RESPONSE = dict(zip(("token", "refreshToken"), NEW_PAIR))
DEVICE = {
    "id": 123, "vendorThingId": "test-device", "name": "Test AC",
    "SysType": 1, "power": "ON", "mode": "COOLING",
    "iduTemperature": 23.5, "fanSpeed": "AUTO", "fanSwing": "OFF",
    "humidity": 0, "online": True,
}


class AirCloudHTTPCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.requests = []
        self.replies = defaultdict(deque)
        self.handlers = {}
        app = web.Application()
        app.router.add_route("*", "/{path:.*}", self.handle_request)
        self.server = TestServer(app)
        await self.server.start_server()
        self.host_patch = patch.object(api_module, "HOST_API", str(self.server.make_url("/")))
        self.host_patch.start()
        self.api = api_module.AirCloudApi("test@example.invalid", "test-password")
        self.set_token_pair(stale=True)

    async def asyncTearDown(self):
        await self.api.close_session()
        await self.server.close()
        self.host_patch.stop()

    def set_token_pair(self, *, stale):
        self.api._token, self.api._ref_token = OLD_PAIR
        self.api._last_token_update = datetime.now() - timedelta(minutes=10 if stale else 0)

    @property
    def token_pair(self):
        return self.api._token, self.api._ref_token

    def queue(self, path, *, status=200, data=None, text=None):
        self.replies[path].append((status, data, text))

    def requests_for(self, path):
        return [request for request in self.requests if request["path"] == path]

    async def handle_request(self, request):
        path = request.match_info["path"]
        body = await request.text()
        self.requests.append({
            "path": path, "method": request.method, "query": dict(request.query),
            "json": await request.json() if body else None,
            "authorization": request.headers.get("Authorization"),
        })
        if path in self.handlers:
            return await self.handlers[path](request)
        if not self.replies[path]:
            return web.Response(status=500, text="Unexpected request in offline test")
        status, data, text = self.replies[path].popleft()
        if text is not None:
            return web.Response(status=status, text=text, content_type="application/json")
        return web.json_response(data, status=status)


class TokenRegressionTests(AirCloudHTTPCase):
    async def test_valid_refresh_updates_both_tokens_without_login(self):
        self.queue(URN_REFRESH_TOKEN, data=NEW_RESPONSE)
        await self.api._refresh_token()
        self.assertEqual(self.token_pair, NEW_PAIR)
        self.assertEqual(len(self.requests_for(URN_REFRESH_TOKEN)), 1)
        self.assertEqual(self.requests_for(URN_AUTH), [])
        self.assertEqual(self.requests_for(URN_REFRESH_TOKEN)[0]["authorization"], "Bearer old-refresh-token")

    async def test_fresh_tokens_do_not_make_auth_requests(self):
        self.set_token_pair(stale=False)
        await self.api._refresh_token()
        self.assertEqual(self.requests, [])
        self.assertEqual(self.token_pair, OLD_PAIR)

    async def test_malformed_refresh_responses_recover_once_via_login(self):
        malformed = [
            {}, [], None, "not an object",
            {"token": "partial-secret"},
            {"token": "", "refreshToken": "new-refresh"},
            {"token": "   ", "refreshToken": "new-refresh"},
            {"token": "new-access", "refreshToken": ""},
            {"token": 123, "refreshToken": "new-refresh"},
            {"token": "new-access", "refreshToken": None},
        ]
        for body in malformed:
            with self.subTest(body=body):
                self.set_token_pair(stale=True)
                self.requests.clear()
                self.replies.clear()
                self.queue(URN_REFRESH_TOKEN, data=body)
                self.queue(URN_AUTH, data=NEW_RESPONSE)
                await self.api._refresh_token()
                self.assertEqual(self.token_pair, NEW_PAIR)
                self.assertEqual(len(self.requests_for(URN_REFRESH_TOKEN)), 1)
                self.assertEqual(len(self.requests_for(URN_AUTH)), 1)

    async def test_invalid_json_refresh_recovers_once_via_login(self):
        self.queue(URN_REFRESH_TOKEN, text="{ invalid JSON")
        self.queue(URN_AUTH, data=NEW_RESPONSE)
        await self.api._refresh_token()
        self.assertEqual(self.token_pair, NEW_PAIR)
        self.assertEqual(len(self.requests_for(URN_AUTH)), 1)

    async def test_missing_refresh_token_uses_login(self):
        self.api._ref_token = None
        self.queue(URN_AUTH, data=NEW_RESPONSE)
        await self.api._refresh_token()
        self.assertEqual(self.token_pair, NEW_PAIR)
        self.assertEqual(len(self.requests_for(URN_AUTH)), 1)
        self.assertEqual(self.requests_for(URN_REFRESH_TOKEN), [])

    async def test_rejected_refresh_recovers_once_via_login(self):
        for status in (401, 403):
            with self.subTest(status=status):
                self.set_token_pair(stale=True)
                self.requests.clear()
                self.queue(URN_REFRESH_TOKEN, status=status, data={"error": "expired"})
                self.queue(URN_AUTH, data=NEW_RESPONSE)
                await self.api._refresh_token()
                self.assertEqual(self.token_pair, NEW_PAIR)
                self.assertEqual(len(self.requests_for(URN_REFRESH_TOKEN)), 1)
                self.assertEqual(len(self.requests_for(URN_AUTH)), 1)

    async def test_temporary_refresh_http_errors_do_not_trigger_login(self):
        for status in (429, 500, 503):
            with self.subTest(status=status):
                self.set_token_pair(stale=True)
                self.requests.clear()
                old_time = self.api._last_token_update
                self.queue(URN_REFRESH_TOKEN, status=status, data={"error": "retry later"})
                with self.assertRaises(aiohttp.ClientResponseError):
                    await self.api._refresh_token()
                self.assertEqual(self.token_pair, OLD_PAIR)
                self.assertEqual(self.api._last_token_update, old_time)
                self.assertEqual(self.requests_for(URN_AUTH), [])

    async def test_refresh_timeout_does_not_trigger_login_or_replace_tokens(self):
        release = asyncio.Event()

        async def timeout_response(request):
            await release.wait()
            return web.json_response(NEW_RESPONSE)

        self.handlers[URN_REFRESH_TOKEN] = timeout_response
        await self.api.close_session()
        self.api._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=0.05))
        try:
            with self.assertRaises(asyncio.TimeoutError):
                await self.api._refresh_token()
            self.assertEqual(self.token_pair, OLD_PAIR)
            self.assertEqual(self.requests_for(URN_AUTH), [])
        finally:
            release.set()

    async def test_invalid_login_never_partially_replaces_tokens_or_exposes_body(self):
        malformed = [
            {"token": "partial-secret"},
            {"refreshToken": "partial-secret"},
            {"token": "partial-secret", "refreshToken": ""},
            {"token": "partial-secret", "refreshToken": 123},
            {"token": "  ", "refreshToken": "partial-secret"},
            [], None,
        ]
        for body in malformed:
            with self.subTest(body=body):
                self.set_token_pair(stale=True)
                self.requests.clear()
                self.queue(URN_AUTH, data=body)
                old_time = self.api._last_token_update
                with self.assertRaises(Exception) as raised:
                    await self.api._refresh_token(forced=True)
                self.assertEqual(self.token_pair, OLD_PAIR)
                self.assertEqual(self.api._last_token_update, old_time)
                self.assertNotIsInstance(raised.exception, (KeyError, TypeError))
                self.assertNotIn("partial-secret", str(raised.exception))
                self.assertNotIn("test-password", str(raised.exception))
                self.assertEqual(len(self.requests_for(URN_AUTH)), 1)

    async def test_failed_fallback_login_is_not_retried(self):
        self.queue(URN_REFRESH_TOKEN, data={"error": "partial-secret"})
        self.queue(URN_AUTH, data={"token": "partial-secret"})
        with self.assertLogs(api_module.__name__, level="WARNING") as logs:
            with self.assertRaises(Exception) as raised:
                await self.api._refresh_token()
        self.assertEqual(self.token_pair, OLD_PAIR)
        self.assertEqual(len(self.requests_for(URN_AUTH)), 1)
        self.assertNotIn("partial-secret", str(raised.exception))
        self.assertNotIn("partial-secret", " ".join(logs.output))

    async def test_invalid_json_login_preserves_tokens_and_has_safe_error(self):
        self.queue(URN_AUTH, text='{"token": "partial-secret", invalid JSON')
        old_time = self.api._last_token_update
        with self.assertRaises(Exception) as raised:
            await self.api._refresh_token(forced=True)
        self.assertEqual(self.token_pair, OLD_PAIR)
        self.assertEqual(self.api._last_token_update, old_time)
        self.assertNotIn("partial-secret", str(raised.exception))
        self.assertEqual(len(self.requests_for(URN_AUTH)), 1)

    async def test_rejected_login_preserves_old_token_pair(self):
        self.queue(URN_AUTH, status=401, data={"error": "partial-secret"})
        with self.assertRaises(aiohttp.ClientResponseError) as raised:
            await self.api._refresh_token(forced=True)
        self.assertEqual(self.token_pair, OLD_PAIR)
        self.assertNotIn("partial-secret", str(raised.exception))
        self.assertEqual(len(self.requests_for(URN_AUTH)), 1)

    async def check_concurrent_auth(self, *, forced):
        entered = asyncio.Event()
        release = asyncio.Event()
        active = 0
        maximum_active = 0
        endpoint = URN_AUTH if forced else URN_REFRESH_TOKEN

        async def blocked_response(request):
            nonlocal active, maximum_active
            active += 1
            maximum_active = max(maximum_active, active)
            entered.set()
            try:
                await release.wait()
                return web.json_response(NEW_RESPONSE)
            finally:
                active -= 1

        self.handlers[endpoint] = blocked_response
        callers = [asyncio.create_task(self.api._refresh_token(forced=forced)) for _ in range(5)]
        try:
            await asyncio.wait_for(entered.wait(), timeout=2)
            # All tasks have started and observed the stale generation before release.
            await asyncio.sleep(0)
            release.set()
            await asyncio.gather(*callers)
        finally:
            release.set()
            for task in callers:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*callers, return_exceptions=True)
        self.assertEqual(self.token_pair, NEW_PAIR)
        self.assertEqual(len(self.requests_for(endpoint)), 1)
        self.assertEqual(maximum_active, 1)

    async def test_concurrent_refresh_uses_one_refresh_request(self):
        await self.check_concurrent_auth(forced=False)

    async def test_concurrent_forced_auth_uses_one_serialized_login(self):
        await self.check_concurrent_auth(forced=True)


class CommandRegressionTests(AirCloudHTTPCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.set_token_pair(stale=False)
        self.api._device_cache[123] = dict(DEVICE)
        self.entity = climate_module.AirCloudClimateEntity(
            self.api, dict(DEVICE), SimpleNamespace(data={}), 456, None,
        )
        self.entity.async_write_ha_state = Mock()
        self.api.load_climate_data = AsyncMock(return_value=[])
        self.sleep_patch = patch.object(climate_module.asyncio, "sleep", new=AsyncMock())
        self.sleep_patch.start()
        self.command_path = f"{URN_CONTROL_STATUS}/123"

    async def asyncTearDown(self):
        self.sleep_patch.stop()
        await super().asyncTearDown()

    def entity_state(self):
        return (self.entity._power, self.entity._mode, self.entity._target_temp,
                self.entity._fan_speed, self.entity._fan_swing)

    async def test_rejected_command_keeps_state_and_reports_ha_error(self):
        before = self.entity_state()
        self.queue(self.command_path, status=400, data={"error": "rejected"})
        with self.assertRaises(HomeAssistantError):
            await self.entity.async_turn_off()
        self.assertEqual(self.entity_state(), before)
        self.assertEqual(self.api._device_cache[123], DEVICE)
        self.entity.async_write_ha_state.assert_not_called()
        self.api.load_climate_data.assert_not_awaited()
        self.assertFalse(self.entity._command_in_flight)

    async def test_successful_command_preserves_state_update_and_refresh(self):
        self.queue(self.command_path, data={"commandId": "accepted"})
        await self.entity.async_turn_off()
        self.assertEqual(self.entity._power, "OFF")
        self.assertEqual(self.entity.target_temperature, 23.5)
        self.assertEqual(self.entity.async_write_ha_state.call_count, 2)
        self.api.load_climate_data.assert_awaited_once_with(456, force=True)
        self.assertFalse(self.entity._command_in_flight)

    async def test_followup_snapshot_replaces_optimistic_state(self):
        self.queue(self.command_path, data={"commandId": "accepted"})
        self.api.load_climate_data.return_value = [{**DEVICE, "iduTemperature": 22.0}]
        await self.entity.async_turn_off()
        self.assertEqual(self.entity._power, "ON")
        self.assertEqual(self.entity.target_temperature, 22.0)
        self.assertEqual(self.entity.async_write_ha_state.call_count, 2)

    async def test_followup_read_failure_does_not_turn_accepted_command_into_failure(self):
        self.queue(self.command_path, data={"commandId": "accepted"})
        self.api.load_climate_data.side_effect = aiohttp.ClientError("snapshot unavailable")
        await self.entity.async_turn_off()
        self.assertEqual(self.entity._power, "OFF")
        self.assertEqual(self.entity.target_temperature, 23.5)
        self.assertGreaterEqual(self.entity.async_write_ha_state.call_count, 1)
        self.assertFalse(self.entity._command_in_flight)

    async def test_default_rac_payload_and_status_endpoint_remain_unchanged(self):
        self.queue(self.command_path, data={"commandId": "accepted"})
        await self.api.execute_command(123, 456, "OFF", 23.5, "COOLING", "AUTO", "VERTICAL", 0)
        request = self.requests_for(self.command_path)[0]
        self.assertEqual(request["method"], "PUT")
        self.assertEqual(request["query"], {"familyId": "456"})
        self.assertEqual(request["json"], {
            "power": "OFF", "mode": "COOLING", "fanSpeed": "AUTO",
            "fanSwing": "VERTICAL", "humidity": "0", "iduTemperature": 23.5,
            "relativeTemperature": 0.0,
        })

    async def test_closed_api_session_does_not_report_command_success(self):
        await self.api.close_session()
        with self.assertRaises(Exception):
            await self.api.execute_command(123, 456, "OFF", 23.5, "COOLING", "AUTO", "OFF", 0)
        self.assertEqual(self.api._device_cache[123], DEVICE)
        self.assertEqual(self.requests, [])

    async def test_closed_session_leaves_entity_state_unchanged(self):
        before = self.entity_state()
        await self.api.close_session()
        with self.assertRaises(HomeAssistantError):
            await self.entity.async_turn_off()
        self.assertEqual(self.entity_state(), before)
        self.entity.async_write_ha_state.assert_not_called()
        self.assertFalse(self.entity._command_in_flight)

    async def test_cancelled_command_releases_flag_without_writing_state(self):
        self.api.execute_command = AsyncMock(side_effect=asyncio.CancelledError)
        before = self.entity_state()
        with self.assertRaises(asyncio.CancelledError):
            await self.entity.async_turn_off()
        self.assertEqual(self.entity_state(), before)
        self.entity.async_write_ha_state.assert_not_called()
        self.assertFalse(self.entity._command_in_flight)


if __name__ == "__main__":
    unittest.main()
