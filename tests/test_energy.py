"""Tests for energy consumption API and sensor entities."""
import calendar
from datetime import datetime
from unittest.mock import AsyncMock

from tests.test_regressions import AirCloudHTTPCase, NEW_RESPONSE
from custom_components.air_cloud import sensor as sensor_module
from custom_components.air_cloud.api import (
    get_current_month_date_range,
    get_current_year_date_range,
)
from custom_components.air_cloud.const import (
    DOMAIN,
    API,
    URN_REFRESH_TOKEN,
    URN_WHO,
    URN_ENERGY_CONSUMPTION_SUMMARY,
    URN_ENERGY_ALL_RACS,
)
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy


class EnergyConsumptionTests(AirCloudHTTPCase):
    def test_current_month_date_range(self):
        start_date, end_date = get_current_month_date_range()
        now = datetime.now()
        expected_start = now.strftime("%Y-%m-01")
        _, last_day = calendar.monthrange(now.year, now.month)
        expected_end = f"{now.year:04d}-{now.month:02d}-{last_day:02d}"

        self.assertEqual(start_date, expected_start)
        self.assertEqual(end_date, expected_end)
        self.assertEqual(len(start_date.split("-")), 3)
        self.assertEqual(len(end_date.split("-")), 3)

    def test_current_year_date_range(self):
        start_date, end_date = get_current_year_date_range()
        now = datetime.now()
        expected_start = f"{now.year:04d}-01-01"
        expected_end = f"{now.year:04d}-12-31"

        self.assertEqual(start_date, expected_start)
        self.assertEqual(end_date, expected_end)

    async def test_load_energy_consumption_summary_sends_current_month(self):
        self.set_token_pair(stale=False)
        self.queue(
            URN_ENERGY_CONSUMPTION_SUMMARY,
            data={
                "allRacsData": {
                    "cost": 15.5,
                    "energyConsumed": 120.0,
                    "currency": "EUR",
                },
                "individualRacsData": [
                    {
                        "vendorThingId": "test-rac-1",
                        "racName": "Living Room",
                        "racId": 123,
                        "cost": 10.0,
                        "energyConsumed": 80.0,
                    }
                ],
            },
        )

        res = await self.api.load_energy_consumption_summary(155725)
        self.assertIn("individualRacsData", res)
        self.assertEqual(len(res["individualRacsData"]), 1)
        self.assertEqual(res["individualRacsData"][0]["energyConsumed"], 80.0)

        requests = self.requests_for(URN_ENERGY_CONSUMPTION_SUMMARY)
        self.assertEqual(len(requests), 1)
        req = requests[0]
        self.assertEqual(req["query"]["familyId"], "155725")

        start_date, end_date = get_current_month_date_range()
        self.assertEqual(req["json"]["from"], start_date)
        self.assertEqual(req["json"]["to"], end_date)
        self.assertNotEqual(req["json"]["from"], "2000-01-01")
        self.assertNotEqual(req["json"]["to"], "2099-12-31")

    async def test_load_energy_consumption_summary_custom_dates(self):
        self.set_token_pair(stale=False)
        self.queue(URN_ENERGY_CONSUMPTION_SUMMARY, data={"individualRacsData": []})

        await self.api.load_energy_consumption_summary(
            155725, from_date="2026-03-01", to_date="2026-03-31"
        )
        req = self.requests_for(URN_ENERGY_CONSUMPTION_SUMMARY)[0]
        self.assertEqual(req["json"]["from"], "2026-03-01")
        self.assertEqual(req["json"]["to"], "2026-03-31")

    async def test_load_energy_consumption_summary_rate_limiting(self):
        self.set_token_pair(stale=False)
        self.queue(
            URN_ENERGY_CONSUMPTION_SUMMARY,
            status=429,
            data={"error": "too many requests"},
        )

        res = await self.api.load_energy_consumption_summary(155725)
        self.assertEqual(res, {})
        self.assertIn(155725, self.api._energy_summary_rate_limited_until)

        # Subsequent call before rate limit expires returns cached/empty without HTTP request
        res2 = await self.api.load_energy_consumption_summary(155725)
        self.assertEqual(res2, {})
        self.assertEqual(len(self.requests_for(URN_ENERGY_CONSUMPTION_SUMMARY)), 1)

    async def test_load_energy_all_racs(self):
        self.set_token_pair(stale=False)
        self.queue(
            URN_ENERGY_ALL_RACS,
            data={
                "allRacList": [
                    {
                        "racId": 123,
                        "racName": "Salon",
                        "isSelected": True,
                        "isEnergyConsumptionSupported": True,
                    }
                ]
            },
        )

        racs = await self.api.load_energy_all_racs(155725)
        self.assertEqual(len(racs), 1)
        self.assertEqual(racs[0]["racId"], 123)
        self.assertTrue(racs[0]["isSelected"])

        req = self.requests_for(URN_ENERGY_ALL_RACS)[0]
        self.assertEqual(req["query"]["familyId"], "155725")

    async def test_sensor_build_entities_from_summary(self):
        self.set_token_pair(stale=False)
        self.queue(URN_WHO, data=[{"familyId": 155725}])
        # Monthly summary response
        self.queue(
            URN_ENERGY_CONSUMPTION_SUMMARY,
            data={
                "allRacsData": {"currency": "USD"},
                "individualRacsData": [
                    {
                        "vendorThingId": "test-rac-1",
                        "racName": "Etage",
                        "energyConsumed": 42.5,
                        "cost": 6.8,
                    }
                ],
            },
        )
        # Yearly summary response
        self.queue(
            URN_ENERGY_CONSUMPTION_SUMMARY,
            data={
                "allRacsData": {"currency": "USD"},
                "individualRacsData": [
                    {
                        "vendorThingId": "test-rac-1",
                        "racName": "Etage",
                        "energyConsumed": 350.0,
                        "cost": 55.0,
                    }
                ],
            },
        )

        hass = type("Hass", (), {"data": {DOMAIN: {API: self.api}}})()
        entities = await sensor_module._build_entities(hass)

        self.assertEqual(len(entities), 2)
        # Monthly sensor
        monthly_sensor = entities[0]
        self.assertEqual(monthly_sensor._vendor_id, "test-rac-1")
        self.assertEqual(monthly_sensor._attr_name, "Etage Energy Consumption")
        self.assertEqual(monthly_sensor._attr_unique_id, "test-rac-1_energy")
        self.assertEqual(monthly_sensor.native_value, 42.5)
        self.assertEqual(monthly_sensor.device_class, SensorDeviceClass.ENERGY)
        self.assertEqual(monthly_sensor.state_class, SensorStateClass.TOTAL_INCREASING)
        self.assertEqual(monthly_sensor.native_unit_of_measurement, UnitOfEnergy.KILO_WATT_HOUR)
        self.assertEqual(monthly_sensor.device_info["identifiers"], {(DOMAIN, "test-rac-1")})
        self.assertEqual(monthly_sensor.extra_state_attributes["family_id"], 155725)
        self.assertEqual(monthly_sensor.extra_state_attributes["period"], "monthly")
        self.assertEqual(monthly_sensor.extra_state_attributes["cost"], 6.8)
        self.assertEqual(monthly_sensor.extra_state_attributes["currency"], "USD")

        # Yearly sensor
        yearly_sensor = entities[1]
        self.assertEqual(yearly_sensor._vendor_id, "test-rac-1")
        self.assertEqual(yearly_sensor._attr_name, "Etage Yearly Energy Consumption")
        self.assertEqual(yearly_sensor._attr_unique_id, "test-rac-1_yearly_energy")
        self.assertEqual(yearly_sensor.native_value, 350.0)
        self.assertEqual(yearly_sensor.device_class, SensorDeviceClass.ENERGY)
        self.assertEqual(yearly_sensor.state_class, SensorStateClass.TOTAL_INCREASING)
        self.assertEqual(yearly_sensor.native_unit_of_measurement, UnitOfEnergy.KILO_WATT_HOUR)
        self.assertEqual(yearly_sensor.device_info["identifiers"], {(DOMAIN, "test-rac-1")})
        self.assertEqual(yearly_sensor.extra_state_attributes["family_id"], 155725)
        self.assertEqual(yearly_sensor.extra_state_attributes["period"], "yearly")
        self.assertEqual(yearly_sensor.extra_state_attributes["cost"], 55.0)
        self.assertEqual(yearly_sensor.extra_state_attributes["currency"], "USD")

    async def test_sensor_build_entities_null_safety(self):
        self.set_token_pair(stale=False)
        self.queue(URN_WHO, data=[{"familyId": 155725}])
        self.queue(
            URN_ENERGY_CONSUMPTION_SUMMARY,
            data={"allRacsData": None, "individualRacsData": None},
        )
        self.queue(
            URN_ENERGY_CONSUMPTION_SUMMARY,
            data={"allRacsData": None, "individualRacsData": None},
        )
        self.queue(URN_ENERGY_ALL_RACS, data={"allRacList": []})

        hass = type("Hass", (), {"data": {DOMAIN: {API: self.api}}})()
        # Should not raise TypeError: 'NoneType' object is not iterable
        entities = await sensor_module._build_entities(hass)
        self.assertEqual(entities, [])

    async def test_sensor_fallback_when_summary_empty(self):
        self.set_token_pair(stale=False)
        self.queue(URN_WHO, data=[{"familyId": 155725}])
        self.queue(URN_ENERGY_CONSUMPTION_SUMMARY, data={"individualRacsData": []})
        self.queue(URN_ENERGY_CONSUMPTION_SUMMARY, data={"individualRacsData": []})
        self.queue(
            URN_ENERGY_ALL_RACS,
            data={
                "allRacList": [
                    {
                        "racId": 123,
                        "racName": "Salon",
                        "isSelected": True,
                        "isEnergyConsumptionSupported": True,
                    }
                ]
            },
        )
        self.api._device_cache[123] = {
            "id": 123,
            "vendorThingId": "test-rac-fallback",
            "name": "Salon",
        }
        self.api._device_family[123] = 155725
        self.api._update_timestamps[155725] = 9999999999.0

        hass = type("Hass", (), {"data": {DOMAIN: {API: self.api}}})()
        entities = await sensor_module._build_entities(hass)

        self.assertEqual(len(entities), 2)
        m_sensor = entities[0]
        self.assertEqual(m_sensor._vendor_id, "test-rac-fallback")
        self.assertEqual(m_sensor._attr_name, "Salon Energy Consumption")
        self.assertEqual(m_sensor._attr_unique_id, "test-rac-fallback_energy")
        self.assertIsNone(m_sensor.native_value)

        y_sensor = entities[1]
        self.assertEqual(y_sensor._vendor_id, "test-rac-fallback")
        self.assertEqual(y_sensor._attr_name, "Salon Yearly Energy Consumption")
        self.assertEqual(y_sensor._attr_unique_id, "test-rac-fallback_yearly_energy")
        self.assertIsNone(y_sensor.native_value)

    async def test_sensor_async_update(self):
        self.set_token_pair(stale=False)
        rac_data = {
            "vendorThingId": "test-rac-1",
            "racName": "Living Room",
            "energyConsumed": 10.0,
            "cost": 1.5,
        }
        sensor = sensor_module.AirCloudEnergySensor(self.api, rac_data, 155725)
        self.assertEqual(sensor.native_value, 10.0)

        # Update returns new energy consumed
        self.queue(
            URN_ENERGY_CONSUMPTION_SUMMARY,
            data={
                "allRacsData": {"currency": "EUR"},
                "individualRacsData": [
                    {
                        "vendorThingId": "test-rac-1",
                        "racName": "Living Room",
                        "energyConsumed": 25.5,
                        "cost": 3.8,
                    }
                ],
            },
        )

        await sensor.async_update()
        self.assertEqual(sensor.native_value, 25.5)
        self.assertEqual(sensor.extra_state_attributes["cost"], 3.8)
        self.assertEqual(sensor.extra_state_attributes["currency"], "EUR")

    async def test_sensor_async_update_yearly(self):
        self.set_token_pair(stale=False)
        rac_data = {
            "vendorThingId": "test-rac-1",
            "racName": "Living Room",
            "energyConsumed": 100.0,
            "cost": 15.0,
        }
        sensor = sensor_module.AirCloudEnergySensor(
            self.api, rac_data, 155725, period="yearly"
        )
        self.assertEqual(sensor.native_value, 100.0)
        self.assertEqual(sensor._attr_unique_id, "test-rac-1_yearly_energy")
        self.assertEqual(sensor._attr_name, "Living Room Yearly Energy Consumption")

        self.queue(
            URN_ENERGY_CONSUMPTION_SUMMARY,
            data={
                "allRacsData": {"currency": "EUR"},
                "individualRacsData": [
                    {
                        "vendorThingId": "test-rac-1",
                        "racName": "Living Room",
                        "energyConsumed": 250.0,
                        "cost": 35.0,
                    }
                ],
            },
        )

        await sensor.async_update()
        self.assertEqual(sensor.native_value, 250.0)
        self.assertEqual(sensor.extra_state_attributes["cost"], 35.0)
        self.assertEqual(sensor.extra_state_attributes["period"], "yearly")

        requests = self.requests_for(URN_ENERGY_CONSUMPTION_SUMMARY)
        self.assertEqual(len(requests), 1)
        start_year, end_year = get_current_year_date_range()
        self.assertEqual(requests[0]["json"]["from"], start_year)
        self.assertEqual(requests[0]["json"]["to"], end_year)
