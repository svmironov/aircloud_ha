"""Options persistence/form contract; HA frontend rendering is not exercised."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
import unittest
from tests import ha_boundary  # noqa: F401
from custom_components import air_cloud
from custom_components.air_cloud import config_flow

KEY = 'legacy_rac_off_device_ids'


class CompatibilityOptionsTests(unittest.IsolatedAsyncioTestCase):
    def make_flow(self, options, api=None):
        entry = SimpleNamespace(options=options, runtime_data=api)

        class Flow(config_flow.AirCloudOptionsFlow):
            @property
            def config_entry(self):
                return entry

        flow = Flow()
        flow.async_show_form = Mock(side_effect=lambda **kwargs: kwargs)
        flow.async_create_entry = Mock(side_effect=lambda **kwargs: kwargs)
        return flow

    async def test_options_default_to_empty_selection(self):
        flow = self.make_flow({}, Mock(get_rac_device_options=lambda: {'123': 'Test AC'}))
        form = await flow.async_step_init()
        self.assertEqual(form['data_schema']({}), {KEY: []})

    async def test_existing_offline_selection_is_preserved_in_form(self):
        flow = self.make_flow({KEY: [123]}, Mock(get_rac_device_options=lambda: {}))
        form = await flow.async_step_init()
        self.assertEqual(form['data_schema']({}), {KEY: ['123']})

    async def test_saving_selection_keeps_other_options(self):
        flow = self.make_flow({'existing_setting': True})
        result = await flow.async_step_init({KEY: ['123']})
        self.assertEqual(result['data'], {'existing_setting': True, KEY: [123]})

    async def test_empty_selection_disables_compatibility(self):
        flow = self.make_flow({KEY: [123]})
        result = await flow.async_step_init({KEY: []})
        self.assertEqual(result['data'][KEY], [])

    async def test_entry_options_update_only_their_api_and_can_disable(self):
        hass = SimpleNamespace(
            data={},
            config_entries=SimpleNamespace(async_forward_entry_setups=AsyncMock()),
        )
        entry = SimpleNamespace(
            data={'email': 'test@example.invalid', 'password': 'synthetic'},
            options={KEY: [123]},
            add_update_listener=Mock(),
            async_on_unload=Mock(),
        )
        await air_cloud.async_setup_entry(hass, entry)
        api = entry.runtime_data
        self.addAsyncCleanup(api.close_session)
        other_api = air_cloud.AirCloudApi('other@example.invalid', 'synthetic')
        self.addAsyncCleanup(other_api.close_session)
        other_api.set_legacy_rac_off_device_ids([999])

        self.assertEqual(api._legacy_rac_off_device_ids, {123})
        # The listener must retain this entry's API even if global data changes.
        hass.data['air_cloud']['api'] = other_api
        listener = entry.add_update_listener.call_args.args[0]
        entry.options = {KEY: [456]}
        await listener(hass, entry)
        self.assertEqual(api._legacy_rac_off_device_ids, {456})
        self.assertEqual(other_api._legacy_rac_off_device_ids, {999})
        entry.options = {KEY: []}
        await listener(hass, entry)
        self.assertEqual(api._legacy_rac_off_device_ids, set())
        entry.async_on_unload.assert_called_once_with(entry.add_update_listener.return_value)
