"""Config-entry setup and service behavior after YAML setup removal."""
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from tests import ha_boundary  # noqa: F401
from custom_components import air_cloud
from custom_components.air_cloud.const import (
    API,
    CONF_COMMAND_DELAY,
    CONF_LEGACY_RAC_OFF_DEVICE_IDS,
    DOMAIN,
    SERVICE_EXEC_COMMAND,
)


YAML_CONFIG = {
    DOMAIN: {
        "email": "old@example.invalid",
        "password": "old-synthetic-password",
        CONF_COMMAND_DELAY: 99,
        CONF_LEGACY_RAC_OFF_DEVICE_IDS: [999],
    },
}


class ConfigEntrySetupTests(unittest.IsolatedAsyncioTestCase):
    def make_hass(self):
        return SimpleNamespace(
            data={},
            services=SimpleNamespace(async_register=Mock()),
            config_entries=SimpleNamespace(async_forward_entry_setups=AsyncMock()),
        )

    async def test_global_setup_does_not_create_api_from_yaml(self):
        for config in ({}, YAML_CONFIG):
            with self.subTest(configured_in_yaml=DOMAIN in config):
                hass = self.make_hass()
                with patch.object(air_cloud, "AirCloudApi") as api_factory:
                    self.assertTrue(await air_cloud.async_setup(hass, config))
                api_factory.assert_not_called()
                self.assertEqual(hass.data, {})
                hass.services.async_register.assert_called_once()

    async def test_stale_yaml_preserves_active_entry_and_command_service(self):
        hass = self.make_hass()
        api = SimpleNamespace(execute_command=AsyncMock())
        runtime_data = {API: api, CONF_COMMAND_DELAY: 15}
        hass.data[DOMAIN] = runtime_data

        with patch.object(air_cloud, "AirCloudApi") as api_factory:
            self.assertTrue(await air_cloud.async_setup(hass, YAML_CONFIG))
        api_factory.assert_not_called()
        self.assertIs(hass.data[DOMAIN], runtime_data)
        self.assertEqual(hass.data[DOMAIN][CONF_COMMAND_DELAY], 15)

        registration = hass.services.async_register.call_args
        self.assertEqual(registration.args[:2], (DOMAIN, SERVICE_EXEC_COMMAND))
        command = registration.kwargs["schema"]({
            "id": 123, "family_id": 456, "power": "ON", "target_temp": 23.5,
            "mode": "COOLING", "fan_speed": "AUTO", "fan_swing": "OFF",
            "humidity": 0,
        })
        await registration.args[2](SimpleNamespace(data=command))
        api.execute_command.assert_awaited_once_with(
            123, 456, "ON", 23.5, "COOLING", "AUTO", "OFF", 0,
        )

    async def test_entry_setup_uses_ui_credentials_and_forwards_all_platforms(self):
        hass = self.make_hass()
        entry = SimpleNamespace(
            data={"email": "ui@example.invalid", "password": "synthetic-password"},
            options={CONF_COMMAND_DELAY: 12, CONF_LEGACY_RAC_OFF_DEVICE_IDS: [123]},
            add_update_listener=Mock(),
            async_on_unload=Mock(),
        )
        self.assertTrue(await air_cloud.async_setup_entry(hass, entry))
        api = entry.runtime_data
        self.addAsyncCleanup(api.close_session)

        self.assertIs(hass.data[DOMAIN][API], api)
        self.assertEqual(api._login, "ui@example.invalid")
        self.assertEqual(api._password, "synthetic-password")
        self.assertEqual(api._legacy_rac_off_device_ids, {123})
        self.assertEqual(hass.data[DOMAIN][CONF_COMMAND_DELAY], 12)
        hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(
            entry, ["binary_sensor", "button", "climate", "number", "sensor"],
        )
