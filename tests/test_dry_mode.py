"""Tests for DRY mode command normalization and cloud error reporting."""
import asyncio
from unittest.mock import AsyncMock, Mock, patch
import unittest

from aiohttp.client_exceptions import ClientResponseError
from homeassistant.exceptions import HomeAssistantError

from tests.test_regressions import AirCloudHTTPCase, DEVICE
from custom_components.air_cloud import climate as climate_module
from custom_components.air_cloud.climate import AirCloudClimateEntity
from custom_components.air_cloud.const import URN_CONTROL_STATUS


RAC_CONFIG_WITH_DRY_RESTRICTIONS = {
    "cloudId": "test-cloud-id",
    "racOperationModes": [
        {
            "mode": "COOLING",
            "enableSettings": {"temperature": True, "fan": True, "swing": True, "humidity": False},
            "enableFanSpeed": {"AUTO": True, "LV1": True, "LV2": True, "LV3": True, "LV4": True, "LV5": True},
            "defaultFanSpeed": {"AUTO": True},
            "minTemperature": 16.0,
            "maxTemperature": 30.0,
            "defaultTemperature": 27.0,
            "temperatureSetting": "ABSOLUTE",
        },
        {
            "mode": "DRY",
            "enableSettings": {"temperature": False, "fan": False, "swing": True, "humidity": False},
            "enableFanSpeed": {"AUTO": False, "LV1": True, "LV2": False, "LV3": False, "LV4": False, "LV5": False},
            "defaultFanSpeed": {"LV1": True},
            "minTemperature": 0.0,
            "maxTemperature": 0.0,
            "defaultTemperature": 0.0,
            "temperatureSetting": "ABSOLUTE",
        },
        {
            "mode": "FAN",
            "enableSettings": {"temperature": False, "fan": True, "swing": True, "humidity": False},
            "enableFanSpeed": {"AUTO": False, "LV1": True, "LV2": True, "LV3": True, "LV4": True, "LV5": True},
            "defaultFanSpeed": {"LV1": True},
            "minTemperature": 0.0,
            "maxTemperature": 0.0,
            "defaultTemperature": 0.0,
            "temperatureSetting": "ABSOLUTE",
        },
    ],
    "swing": {"VERTICAL": True, "HORIZONTAL": False},
}


class DryModeCommandTests(AirCloudHTTPCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.sleep_patch = patch.object(climate_module.asyncio, "sleep", new=AsyncMock())
        self.sleep_patch.start()

    async def asyncTearDown(self):
        self.sleep_patch.stop()
        await super().asyncTearDown()

    def setUpEntity(self, initial_snapshot=None):
        self.set_token_pair(stale=False)
        snapshot = {
            **DEVICE,
            **(initial_snapshot or {}),
        }
        self.api._device_cache[123] = snapshot
        hass = Mock(data={})
        entity = AirCloudClimateEntity(
            self.api,
            snapshot,
            hass,
            family_id=456,
            rac_config=RAC_CONFIG_WITH_DRY_RESTRICTIONS,
        )
        entity.async_write_ha_state = Mock()
        self.api.load_climate_data = AsyncMock(return_value=[snapshot])
        return entity

    async def test_turn_off_in_dry_mode_normalizes_fan_and_temperature(self):
        # Unit is currently ON in DRY mode, with residual fanSpeed AUTO from previous cooling mode
        entity = self.setUpEntity({
            "power": "ON",
            "mode": "DRY",
            "fanSpeed": "AUTO",
            "iduTemperature": 24.0,
        })
        self.assertEqual(entity._mode, "DRY")
        self.assertEqual(entity._fan_speed, "AUTO")

        path = f"{URN_CONTROL_STATUS}/123"
        self.queue(path, data={"commandId": "accepted"})

        await entity.async_turn_off()

        reqs = self.requests_for(path)
        self.assertEqual(len(reqs), 1)
        sent = reqs[0]["json"]
        self.assertEqual(sent["power"], "OFF")
        self.assertEqual(sent["mode"], "DRY")
        # Fan speed must be normalized to LV1 (only enabled speed in DRY), NOT unvalidated AUTO
        self.assertEqual(sent["fanSpeed"], "LV1")
        # Temperature must be clamped to 0.0 for DRY mode
        self.assertEqual(sent["iduTemperature"], 0.0)

    async def test_turn_on_in_dry_mode_normalizes_fan_and_temperature(self):
        entity = self.setUpEntity({
            "power": "OFF",
            "mode": "DRY",
            "fanSpeed": "AUTO",
            "iduTemperature": 22.0,
        })

        path = f"{URN_CONTROL_STATUS}/123"
        self.queue(path, data={"commandId": "accepted"})

        await entity.async_turn_on()

        reqs = self.requests_for(path)
        self.assertEqual(len(reqs), 1)
        sent = reqs[0]["json"]
        self.assertEqual(sent["power"], "ON")
        self.assertEqual(sent["mode"], "DRY")
        self.assertEqual(sent["fanSpeed"], "LV1")
        self.assertEqual(sent["iduTemperature"], 0.0)

    async def test_fan_mode_without_auto_normalizes_to_enabled_fan_speed(self):
        # In FAN mode, enableFanSpeed does not include AUTO
        entity = self.setUpEntity({
            "power": "ON",
            "mode": "FAN",
            "fanSpeed": "AUTO",
            "iduTemperature": 24.0,
        })

        path = f"{URN_CONTROL_STATUS}/123"
        self.queue(path, data={"commandId": "accepted"})

        await entity.async_turn_off()

        reqs = self.requests_for(path)
        self.assertEqual(len(reqs), 1)
        sent = reqs[0]["json"]
        self.assertEqual(sent["power"], "OFF")
        self.assertEqual(sent["mode"], "FAN")
        self.assertEqual(sent["fanSpeed"], "LV1")

    async def test_rejected_command_surfaces_stack_trace_in_error(self):
        entity = self.setUpEntity({
            "power": "ON",
            "mode": "DRY",
            "fanSpeed": "LV1",
            "iduTemperature": 0.0,
        })

        path = f"{URN_CONTROL_STATUS}/123"
        self.queue(path, status=400, data={"stackTrace": "INVALID_FAN_SPEED"})

        with self.assertRaises(HomeAssistantError) as ctx:
            await entity.async_turn_off()

        err_msg = str(ctx.exception)
        self.assertIn("INVALID_FAN_SPEED", err_msg)
