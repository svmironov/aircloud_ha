"""Sign-in request compatibility and configuration errors (offline HTTP)."""
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
from aiohttp import web

from tests.test_regressions import AirCloudHTTPCase, NEW_PAIR, NEW_RESPONSE, OLD_PAIR
from custom_components.air_cloud import config_flow
from custom_components.air_cloud.const import URN_AUTH


class LoginTests(AirCloudHTTPCase):
    async def test_login_matches_android_form_and_headers(self):
        await self.api.close_session()
        self.api = config_flow.AirCloudApi(
            " \ttest@example.invalid\r\n", "\t test-password \n"
        )
        self.queue(URN_AUTH, data=NEW_RESPONSE)
        self.assertTrue(await self.api.validate_credentials(raise_on_error=True))
        self.assertEqual(self.token_pair, NEW_PAIR)
        request, = self.requests_for(URN_AUTH)
        self.assertEqual(request["json"], {
            "email": "test@example.invalid", "password": "test-password",
        })
        self.assertEqual(request["headers"]["Accept"], "application/json")
        self.assertEqual(request["headers"]["Content-Type"], "application/json")
        self.assertEqual(request["headers"]["User-Agent"], "okhttp/5.3.2")
        self.assertIsNone(request["authorization"])

    async def test_login_preserves_internal_spaces_and_unicode_password(self):
        await self.api.close_session()
        password = "\u00a0a b\u00a0"
        self.api = config_flow.AirCloudApi("test@example.invalid", password)
        self.queue(URN_AUTH, data=NEW_RESPONSE)
        await self.api.validate_credentials(raise_on_error=True)
        self.assertEqual(self.requests_for(URN_AUTH)[0]["json"]["password"], password)

    async def test_legacy_boolean_validation_still_returns_false(self):
        self.queue(URN_AUTH, status=401, data={"errorState": "UNKNOWN_USER"})
        with self.assertLogs(level="ERROR"):
            self.assertFalse(await self.api.validate_credentials())
        self.assertEqual(self.token_pair, OLD_PAIR)
        self.assertEqual(len(self.requests_for(URN_AUTH)), 1)

    async def test_rejected_login_logs_only_known_error_states(self):
        for state in ("UNKNOWN_USER", "Invalid UserId Or Password", "SOFT_LOCK", "HARD_LOCK",
                      "private-response", ["private-response"]):
            with self.subTest(state=state):
                self.requests.clear()
                self.queue(URN_AUTH, status=401, data={
                    "errorState": state, "email": "private-email", "token": "private-token",
                })
                with self.assertLogs(level="WARNING") as logs:
                    with self.assertRaises(aiohttp.ClientResponseError) as raised:
                        await self.api.validate_credentials(raise_on_error=True)
                self.assertEqual(raised.exception.status, 401)
                expected = state if isinstance(state, str) and state in (
                    "UNKNOWN_USER", "Invalid UserId Or Password", "SOFT_LOCK", "HARD_LOCK",
                ) else "unrecognized"
                self.assertIn(f"errorState={expected}", " ".join(logs.output))
                for secret in ("private-response", "private-email", "private-token", "test-password"):
                    self.assertNotIn(secret, " ".join(logs.output))
                self.assertEqual(self.token_pair, OLD_PAIR)
                self.assertEqual(len(self.requests_for(URN_AUTH)), 1)

    async def test_non_json_login_failure_preserves_http_status(self):
        self.queue(URN_AUTH, status=503, text="private-response")
        with self.assertLogs(level="WARNING") as logs:
            with self.assertRaises(aiohttp.ClientResponseError) as raised:
                await self.api.validate_credentials(raise_on_error=True)
        self.assertEqual(raised.exception.status, 503)
        self.assertNotIn("private-response", " ".join(logs.output))
        self.assertEqual(self.token_pair, OLD_PAIR)
        self.assertEqual(len(self.requests_for(URN_AUTH)), 1)

    async def test_error_body_timeout_preserves_http_status(self):
        release = asyncio.Event()

        async def blocked_error_body(request):
            response = web.StreamResponse(status=401)
            await response.prepare(request)
            await release.wait()
            return response

        self.handlers[URN_AUTH] = blocked_error_body
        await self.api.close_session()
        self.api._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=0.05))
        try:
            with self.assertLogs(level="WARNING"):
                with self.assertRaises(aiohttp.ClientResponseError) as raised:
                    await self.api.validate_credentials(raise_on_error=True)
            self.assertEqual(raised.exception.status, 401)
            self.assertEqual(self.token_pair, OLD_PAIR)
            self.assertEqual(len(self.requests_for(URN_AUTH)), 1)
        finally:
            release.set()


class LoginFlowTests(AirCloudHTTPCase):
    def make_flow(self):
        flow = config_flow.AirCloudConfigFlow()
        flow.async_show_form = Mock(side_effect=lambda **kwargs: {"type": "form", **kwargs})
        flow.async_create_entry = Mock(side_effect=lambda **kwargs: {"type": "create_entry", **kwargs})
        return flow

    async def submit(self):
        flow = self.make_flow()
        with patch.object(config_flow, "AirCloudApi", return_value=self.api):
            return await flow.async_step_user({
                "email": "test@example.invalid", "password": "test-password",
            })

    async def test_success_closes_validation_session_and_keeps_entry_data(self):
        self.queue(URN_AUTH, data=NEW_RESPONSE)
        result = await self.submit()
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["data"], {
            "email": "test@example.invalid", "password": "test-password",
        })
        self.assertTrue(self.api._session.closed)

    async def test_http_errors_have_translated_messages_and_do_not_retry(self):
        expected = {
            401: "invalid_auth", 403: "account_disabled", 412: "account_unverified",
            423: "account_locked", 429: "too_many_attempts", 500: "cannot_connect",
            503: "cannot_connect",
        }
        base = Path(__file__).resolve().parents[1] / "custom_components/air_cloud"
        for status, error in expected.items():
            with self.subTest(status=status):
                await self.api.close_session()
                self.api = config_flow.AirCloudApi("test@example.invalid", "test-password")
                self.requests.clear()
                self.queue(URN_AUTH, status=status, data={"secret": "private-response"})
                with self.assertLogs(level="WARNING") as logs:
                    result = await self.submit()
                self.assertEqual(result["errors"], {"base": error})
                self.assertTrue(self.api._session.closed)
                self.assertEqual(len(self.requests_for(URN_AUTH)), 1)
                self.assertNotIn("private-response", " ".join(logs.output))
                self.assertNotIn("test-password", " ".join(logs.output))
                for filename in ("strings.json", "translations/en.json", "translations/pt-BR.json"):
                    self.assertIn(error, json.loads((base / filename).read_text())["config"]["error"])

    async def test_network_and_unexpected_failures_close_session(self):
        for exception, error in (
            (aiohttp.ClientConnectionError(), "cannot_connect"),
            (asyncio.TimeoutError(), "cannot_connect"),
            (RuntimeError("private-response"), "unknown"),
        ):
            with self.subTest(exception=type(exception).__name__):
                with patch.object(self.api, "validate_credentials", AsyncMock(side_effect=exception)):
                    with self.assertLogs(config_flow.__name__) as logs:
                        result = await self.submit()
                self.assertEqual(result["errors"], {"base": error})
                self.assertTrue(self.api._session.closed)
                self.assertNotIn("private-response", " ".join(logs.output))

    async def test_malformed_auth_response_is_not_reported_as_wrong_password(self):
        self.queue(URN_AUTH, data={"token": "private-response"})
        with self.assertLogs(config_flow.__name__, level="WARNING"):
            result = await self.submit()
        self.assertEqual(result["errors"], {"base": "unknown"})
        self.assertTrue(self.api._session.closed)

    async def test_cancellation_propagates_and_closes_validation_session(self):
        with patch.object(self.api, "validate_credentials", AsyncMock(side_effect=asyncio.CancelledError)):
            with self.assertRaises(asyncio.CancelledError):
                await self.submit()
        self.assertTrue(self.api._session.closed)

    async def test_initial_form_does_not_open_http_session(self):
        with patch.object(config_flow, "AirCloudApi") as api:
            result = await self.make_flow().async_step_user()
        self.assertEqual(result["type"], "form")
        api.assert_not_called()
