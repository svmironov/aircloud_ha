"""Tests for AirCloud authentication, credentials sanitization, and error reporting."""
import asyncio
from collections import defaultdict, deque
import unittest
from unittest.mock import Mock, patch

from aiohttp import web
from aiohttp.test_utils import TestServer

from tests import ha_boundary  # noqa: F401
from custom_components.air_cloud import api as api_module
from custom_components.air_cloud.api import AirCloudApi
from custom_components.air_cloud.config_flow import AirCloudConfigFlow
from custom_components.air_cloud.const import CONF_EMAIL, CONF_PASSWORD, URN_AUTH


AUTH_SUCCESS_RESPONSE = {
    "token": "valid-jwt-token",
    "refreshToken": "valid-refresh-token",
}


class AirCloudAuthTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.requests = []
        self.replies = defaultdict(deque)
        app = web.Application()
        app.router.add_route("*", "/{path:.*}", self.handle_request)
        self.server = TestServer(app)
        await self.server.start_server()
        self.host_patch = patch.object(api_module, "HOST_API", str(self.server.make_url("/")))
        self.host_patch.start()

    async def asyncTearDown(self):
        await self.server.close()
        self.host_patch.stop()

    def queue(self, path, *, status=200, data=None):
        self.replies[path].append((status, data))

    async def handle_request(self, request):
        path = request.match_info["path"]
        body = await request.text()
        self.requests.append({
            "path": path,
            "method": request.method,
            "headers": dict(request.headers),
            "json": await request.json() if body else None,
        })
        if not self.replies[path]:
            return web.Response(status=500, text="No reply queued")
        status, data = self.replies[path].popleft()
        return web.json_response(data, status=status)

    async def test_whitespace_stripped_from_credentials(self):
        api = AirCloudApi("  user@example.com \t\n", "  super-secret-password  ")
        self.assertEqual(api._login, "user@example.com")
        self.assertEqual(api._password, "super-secret-password")

        self.queue(URN_AUTH, status=200, data=AUTH_SUCCESS_RESPONSE)
        result = await api.validate_credentials()
        self.assertTrue(result)
        await api.close_session()

        self.assertEqual(len(self.requests), 1)
        sent = self.requests[0]["json"]
        self.assertEqual(sent["email"], "user@example.com")
        self.assertEqual(sent["password"], "super-secret-password")

    async def test_phone_number_detected_and_formatted(self):
        api = AirCloudApi("+1 (555) 234-5678", "secret123")
        self.assertEqual(api._login, "+1 (555) 234-5678")

        self.queue(URN_AUTH, status=200, data=AUTH_SUCCESS_RESPONSE)
        result = await api.validate_credentials()
        self.assertTrue(result)
        await api.close_session()

        self.assertEqual(len(self.requests), 1)
        sent = self.requests[0]["json"]
        self.assertNotIn("email", sent)
        self.assertEqual(sent["mobileNumber"], "+15552345678")
        self.assertEqual(sent["password"], "secret123")

    async def test_headers_include_accept_and_content_type(self):
        api = AirCloudApi("user@example.com", "secret")
        self.queue(URN_AUTH, status=200, data=AUTH_SUCCESS_RESPONSE)
        await api.validate_credentials()
        await api.close_session()

        self.assertEqual(len(self.requests), 1)
        headers = self.requests[0]["headers"]
        self.assertEqual(headers.get("Accept"), "application/json")
        self.assertEqual(headers.get("Content-Type"), "application/json")

    async def test_unknown_user_error_detail(self):
        api = AirCloudApi("unknown@example.com", "wrongpass")
        self.queue(URN_AUTH, status=401, data={"errorState": "UNKNOWN_USER"})
        with self.assertLogs(api_module.__name__, level="ERROR") as log_ctx:
            result = await api.validate_credentials()
        self.assertFalse(result)
        await api.close_session()

        output = " ".join(log_ctx.output)
        self.assertIn("UNKNOWN_USER", output)
        self.assertIn("account not found", output)

    async def test_invalid_password_error_detail(self):
        api = AirCloudApi("user@example.com", "wrongpass")
        self.queue(URN_AUTH, status=401, data={"errorState": "Invalid UserId Or Password"})
        with self.assertLogs(api_module.__name__, level="ERROR") as log_ctx:
            result = await api.validate_credentials()
        self.assertFalse(result)
        await api.close_session()

        output = " ".join(log_ctx.output)
        self.assertIn("Invalid UserId Or Password", output)
        self.assertIn("incorrect password", output)

    async def test_soft_lock_error_detail(self):
        api = AirCloudApi("user@example.com", "wrongpass")
        self.queue(URN_AUTH, status=423, data={"errorState": "SOFT_LOCK"})
        with self.assertLogs(api_module.__name__, level="ERROR") as log_ctx:
            result = await api.validate_credentials()
        self.assertFalse(result)
        await api.close_session()

        output = " ".join(log_ctx.output)
        self.assertIn("SOFT_LOCK", output)
        self.assertIn("account locked", output)

    async def test_empty_credentials_rejected_without_network(self):
        api = AirCloudApi("", "")
        with self.assertLogs(api_module.__name__, level="ERROR") as log_ctx:
            result = await api.validate_credentials()
        self.assertFalse(result)
        await api.close_session()
        self.assertEqual(len(self.requests), 0)
        self.assertIn("cannot be empty", " ".join(log_ctx.output))

    async def test_config_flow_strips_credentials(self):
        flow = AirCloudConfigFlow()
        flow.async_show_form = Mock(side_effect=lambda **kwargs: kwargs)
        flow.async_create_entry = Mock(side_effect=lambda **kwargs: {"type": "create_entry", **kwargs})
        self.queue(URN_AUTH, status=200, data=AUTH_SUCCESS_RESPONSE)
        result = await flow.async_step_user({
            CONF_EMAIL: "  spaced@example.com  ",
            CONF_PASSWORD: "  mypassword  ",
        })
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["data"][CONF_EMAIL], "spaced@example.com")
        self.assertEqual(result["data"][CONF_PASSWORD], "mypassword")
