"""Opt-in OFF compatibility must not change other devices or normal commands."""
import math

from tests.test_regressions import AirCloudHTTPCase, DEVICE
from custom_components.air_cloud.const import (
    URN_CONTROL_STATUS, URN_CONTROL_PAC_STATUS, URN_CONTROL_YUTAMPO_STATUS,
)


class OptionalOFFCompatibilityTests(AirCloudHTTPCase):
    async def send(self, *, device_id=123, sys_type=1, power='OFF', temperature=23.5, swing='VERTICAL'):
        self.set_token_pair(stale=False)
        self.api._device_cache[device_id] = {**DEVICE, 'id': device_id, 'SysType': sys_type}
        endpoint = {1: URN_CONTROL_STATUS, 2: URN_CONTROL_PAC_STATUS, 3: URN_CONTROL_YUTAMPO_STATUS}[sys_type]
        path = f'{endpoint}/{device_id}'
        self.queue(path, data={'commandId': 'accepted'})
        await self.api.execute_command(device_id, 456, power, temperature, 'COOLING', 'AUTO', swing, 0)
        return self.requests_for(path)[-1]['json']

    async def test_selected_rac_off_adds_fields_on_existing_endpoint(self):
        self.api.set_legacy_rac_off_device_ids([123])
        payload = await self.send()
        self.assertEqual(payload['adjustSwing'], 1)
        self.assertEqual(payload['iduTemperature'], 24)
        self.assertIs(type(payload['iduTemperature']), int)
        self.assertEqual(payload['mode'], 'COOLING')
        self.assertEqual(payload['humidity'], '0')

    async def test_selected_rac_off_disabled_swing_uses_zero(self):
        self.api.set_legacy_rac_off_device_ids([123])
        payload = await self.send(swing='OFF', temperature=23.0)
        self.assertEqual(payload['adjustSwing'], 0)
        self.assertEqual(payload['iduTemperature'], 23)

    async def test_unselected_rac_keeps_original_payload(self):
        self.api.set_legacy_rac_off_device_ids([999])
        payload = await self.send()
        self.assertNotIn('adjustSwing', payload)
        self.assertEqual(payload['iduTemperature'], 23.5)

    async def test_selected_on_keeps_fractional_temperature(self):
        self.api.set_legacy_rac_off_device_ids([123])
        payload = await self.send(power='ON')
        self.assertNotIn('adjustSwing', payload)
        self.assertEqual(payload['iduTemperature'], 23.5)

    async def test_removing_selection_restores_default_payload(self):
        self.api.set_legacy_rac_off_device_ids([123])
        self.api.set_legacy_rac_off_device_ids([])
        payload = await self.send()
        self.assertNotIn('adjustSwing', payload)
        self.assertEqual(payload['iduTemperature'], 23.5)

    async def test_non_rac_systems_are_unchanged_even_if_selected(self):
        self.api.set_legacy_rac_off_device_ids([123])
        for sys_type in [2, 3]:
            with self.subTest(sys_type=sys_type):
                payload = await self.send(sys_type=sys_type)
                self.assertNotIn('adjustSwing', payload)
                self.assertEqual(payload['iduTemperature'], 23.5 if sys_type == 2 else 24)

    async def test_selected_off_rejects_nonfinite_temperature_without_http(self):
        self.api.set_legacy_rac_off_device_ids([123])
        for temperature in [math.nan, math.inf, -math.inf]:
            with self.subTest(temperature=temperature):
                with self.assertRaises(ValueError):
                    await self.send(temperature=temperature)
                self.assertEqual(self.requests, [])

    async def test_device_choices_only_include_known_rac_devices(self):
        self.api._device_cache = {
            123: {**DEVICE},
            124: {**DEVICE, 'id': 124, 'SysType': 2},
            125: {**DEVICE, 'id': 125, 'SysType': 3},
        }
        choices = self.api.get_rac_device_options()
        self.assertEqual(set(choices), {'123'})
        self.assertIn('Test AC', choices['123'])
