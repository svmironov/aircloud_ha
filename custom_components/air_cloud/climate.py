from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    FAN_AUTO,
    SWING_BOTH,
    SWING_HORIZONTAL,
    SWING_OFF,
    SWING_VERTICAL,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature

from .api import (
    DEFAULT_FAN_SPEED,
    DEFAULT_FAN_SWING,
    DEFAULT_MODE,
    DEFAULT_POWER,
    FAN_SPEED_ORDER,
    NO_HUMIDITY_VALUE,
    _fan_sort_key,
    _get_sys_type,
    build_mode_settings_map,
    get_supported_swing_values,
)
from .const import (
    API,
    CONF_TEMP_ADJUST,
    CONF_TEMP_STEP,
    DOMAIN,
    SYS_TYPE_G_RAC,
)

_LOGGER = logging.getLogger(__name__)

RAW_TO_HVAC: dict[str, HVACMode] = {
    "COOLING": HVACMode.COOL,
    "HEATING": HVACMode.HEAT,
    "DRY":     HVACMode.DRY,
    "FAN":     HVACMode.FAN_ONLY,
    "AUTO":    HVACMode.AUTO,
}
HVAC_TO_RAW: dict[HVACMode, str] = {v: k for k, v in RAW_TO_HVAC.items()}

RAW_TO_FAN: dict[str, str] = {
    "AUTO": FAN_AUTO,
    "LV1":  "Silent",
    "LV2":  "Low",
    "LV3":  "Medium",
    "LV4":  "High",
    "LV5":  "Turbo",
    "LV6":  "Turbo+",
    "LVA":  "Low-Auto",
    "NOWIND": "No Wind",
}
FAN_TO_RAW: dict[str, str] = {v: k for k, v in RAW_TO_FAN.items()}

RAW_TO_SWING: dict[str, str] = {
    "OFF":        SWING_OFF,
    "VERTICAL":   SWING_VERTICAL,
    "HORIZONTAL": SWING_HORIZONTAL,
    "BOTH":       SWING_BOTH,
}
SWING_TO_RAW: dict[str, str] = {v: k for k, v in RAW_TO_SWING.items()}

async def _build_entities(hass) -> list["AirCloudClimateEntity"]:
    api = hass.data[DOMAIN][API]
    entities: list[AirCloudClimateEntity] = []
    family_ids = await api.load_family_ids()
    all_devices: list[tuple[dict, int]] = []
    cloud_ids: list[str] = []
    for family_id in family_ids:
        devices = await api.load_climate_data(family_id)
        for device in devices:
            all_devices.append((device, family_id))
            cid = device.get("cloudId")
            if cid:
                cloud_ids.append(cid)
    if cloud_ids:
        await api.load_rac_configuration(cloud_ids)
    for device, family_id in all_devices:
        rac_config = api.get_cached_rac_config(device.get("cloudId"))
        entities.append(AirCloudClimateEntity(api, device, hass, family_id, rac_config))
    return entities

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    entities = await _build_entities(hass)
    if entities:
        async_add_entities(entities, update_before_add=False)

async def async_setup_entry(hass, config_entry, async_add_entities):
    entities = await _build_entities(hass)
    if entities:
        async_add_entities(entities, update_before_add=False)

class AirCloudClimateEntity(ClimateEntity):

    _attr_has_entity_name = True
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
        self,
        api,
        device: dict[str, Any],
        hass,
        family_id: int,
        rac_config: dict[str, Any] | None,
    ) -> None:
        self._api = api
        self._hass = hass
        self._family_id = family_id
        self._device_id: int = device["id"]
        self._vendor_id: str = device["vendorThingId"]
        self._cloud_id: str | None = device.get("cloudId")
        self._rac_config = rac_config
        self._mode_settings: dict[str, Any] = build_mode_settings_map(rac_config)
        self._supported_raw_swings: list[str] = get_supported_swing_values(rac_config)

        self._attr_unique_id = self._vendor_id
        self._attr_name: str = device["name"]

        self._available = True
        self._power = DEFAULT_POWER
        self._mode = DEFAULT_MODE
        self._fan_speed = DEFAULT_FAN_SPEED
        self._fan_swing = DEFAULT_FAN_SWING
        self._target_temp: float = 24.0
        self._room_temp: float | None = None
        self._raw_humidity: Any = NO_HUMIDITY_VALUE
        self._sys_type: int | None = None
        self._command_in_flight = False

        self._apply_snapshot(device)

        self._attr_hvac_modes = self._build_hvac_modes()
        self._attr_fan_modes = self._build_fan_modes()
        self._attr_swing_modes = self._build_swing_modes()

    def _build_hvac_modes(self) -> list[HVACMode]:
        modes = [HVACMode.OFF]
        raw_modes = list(self._mode_settings) or [self._mode]
        for raw in RAW_TO_HVAC:
            if raw in raw_modes and RAW_TO_HVAC[raw] not in modes:
                modes.append(RAW_TO_HVAC[raw])
        return modes

    def _build_fan_modes(self) -> list[str]:
        all_speeds: set[str] = set()
        for settings in self._mode_settings.values():
            all_speeds.update(settings.get("enabled_fan_speeds") or [])
        if not all_speeds:
            all_speeds = {self._fan_speed}
        ordered = [
            RAW_TO_FAN[s]
            for s in FAN_SPEED_ORDER
            if s in all_speeds and s in RAW_TO_FAN
        ]
        return ordered or [FAN_AUTO]

    def _build_swing_modes(self) -> list[str]:
        modes = [SWING_OFF]
        for raw in ("VERTICAL", "HORIZONTAL", "BOTH"):
            if raw in self._supported_raw_swings and RAW_TO_SWING.get(raw) not in modes:
                modes.append(RAW_TO_SWING[raw])
        return modes

    def _apply_snapshot(self, snapshot: dict[str, Any]) -> None:
        self._available = bool(
            snapshot.get("online", snapshot.get("isOnline", True))
        )
        self._power = str(snapshot.get("power", self._power)).upper()
        self._mode = str(snapshot.get("mode", self._mode)).upper()
        self._fan_speed = str(snapshot.get("fanSpeed", self._fan_speed)).upper()
        self._fan_swing = str(snapshot.get("fanSwing", self._fan_swing)).upper()
        self._sys_type = _get_sys_type(snapshot)

        settings = self._mode_settings_for(self._mode)
        is_relative = settings.get("temperature_setting", "ABSOLUTE") == "RELATIVE"
        ref_temp = float(settings.get("reference_temperature", 0.0))

        if is_relative and snapshot.get("relativeTemperature") not in (None, ""):
            raw_t = float(snapshot.get("relativeTemperature", 0.0))
            self._target_temp = self._clamp_temp(raw_t + ref_temp, self._mode)
        elif snapshot.get("iduTemperature") not in (None, ""):
            raw_t = float(snapshot.get("iduTemperature", 24.0))
            self._target_temp = self._clamp_temp(raw_t, self._mode)
        else:
            self._target_temp = self._default_temp(self._mode)

        room_raw = snapshot.get("roomTemperature")
        if room_raw is not None:
            adjust = float(
                self._hass.data.get(DOMAIN, {})
                .get(CONF_TEMP_ADJUST, {})
                .get(self._device_id, 0.0)
            )
            self._room_temp = float(room_raw) + adjust
        else:
            self._room_temp = None

        self._raw_humidity = snapshot.get("humidity", NO_HUMIDITY_VALUE)

    def _mode_settings_for(self, mode: str | None = None) -> dict[str, Any]:
        key = str(mode or self._mode or DEFAULT_MODE).upper()
        return self._mode_settings.get(key) or {}

    def _default_temp(self, mode: str) -> float:
        s = self._mode_settings_for(mode)
        ref = float(s.get("reference_temperature", 0.0))
        default = float(s.get("default_temperature", 24.0))
        return default + ref

    def _clamp_temp(self, value: float, mode: str) -> float:
        s = self._mode_settings_for(mode)
        ref = float(s.get("reference_temperature", 0.0))
        lo = float(s.get("min_temperature", 16.0)) + ref
        hi = float(s.get("max_temperature", 32.0)) + ref
        if lo >= hi:
            return value
        return max(lo, min(hi, value))

    def _normalize_fan_speed(self, raw_speed: str | None, mode: str) -> str:
        s = self._mode_settings_for(mode)
        enabled: list[str] = s.get("enabled_fan_speeds") or []
        candidate = str(raw_speed or self._fan_speed or DEFAULT_FAN_SPEED).upper()
        if not enabled or not s.get("fan_enabled", True):
            return candidate
        if candidate in enabled:
            return candidate
        default = s.get("default_fan_speed", DEFAULT_FAN_SPEED)
        return default if default in enabled else sorted(enabled, key=_fan_sort_key)[0]

    def _normalize_fan_swing(self, raw_swing: str | None) -> str:
        candidate = str(raw_swing or self._fan_swing or DEFAULT_FAN_SWING).upper()
        if candidate == "AUTO" and self._sys_type == SYS_TYPE_G_RAC:
            candidate = DEFAULT_FAN_SWING
        if not self._supported_raw_swings:
            return candidate
        if candidate in self._supported_raw_swings:
            return candidate
        current = str(self._fan_swing or DEFAULT_FAN_SWING).upper()
        if current == "AUTO" and self._sys_type == SYS_TYPE_G_RAC:
            current = DEFAULT_FAN_SWING
        return current if current in self._supported_raw_swings else DEFAULT_FAN_SWING

    def _command_humidity(self, mode: str) -> int:
        s = self._mode_settings_for(mode)
        default = int(s.get("default_humidity", 0))
        if not s.get("humidity_enabled", False):
            return default

        raw = self._raw_humidity
        try:
            val = int(float(raw)) if raw not in (None, "", NO_HUMIDITY_VALUE) else NO_HUMIDITY_VALUE
        except (TypeError, ValueError):
            val = NO_HUMIDITY_VALUE

        if val >= NO_HUMIDITY_VALUE:
            return default

        min_h = s.get("min_humidity")
        max_h = s.get("max_humidity")
        if min_h is not None and max_h is not None and min_h <= max_h:
            if not (min_h <= val <= max_h):
                return default
        return val

    async def _send_command(
        self,
        *,
        power: str | None = None,
        mode: str | None = None,
        target_temp: float | None = None,
        fan_speed: str | None = None,
        fan_swing: str | None = None,
    ) -> None:
        desired_mode = str(mode or self._mode or DEFAULT_MODE).upper()
        desired_power = (
            "ON" if str(power or self._power or DEFAULT_POWER).upper() == "ON" else "OFF"
        )
        desired_temp = self._clamp_temp(
            target_temp if target_temp is not None else self._target_temp,
            desired_mode,
        )
        desired_fan = self._normalize_fan_speed(fan_speed, desired_mode)
        desired_swing = self._normalize_fan_swing(fan_swing)
        desired_humidity = self._command_humidity(desired_mode)

        _LOGGER.debug(
            "AirCloud: sending command device=%s power=%s mode=%s temp=%.1f fan=%s swing=%s hum=%s",
            self._device_id, desired_power, desired_mode, desired_temp,
            desired_fan, desired_swing, desired_humidity,
        )

        self._command_in_flight = True
        try:
            await self._api.execute_command(
                self._device_id,
                self._family_id,
                desired_power,
                desired_temp,
                desired_mode,
                desired_fan,
                desired_swing,
                desired_humidity,
            )
        except Exception as exc: 
            _LOGGER.error("AirCloud: command failed: %s", exc)
        finally:
            self._command_in_flight = False

        self._power = desired_power
        self._mode = desired_mode
        self._target_temp = desired_temp
        self._fan_speed = desired_fan
        self._fan_swing = desired_swing
        self.async_write_ha_state()

        await asyncio.sleep(2)
        devices = await self._api.load_climate_data(self._family_id, force=True)
        for device in devices:
            if device.get("id") == self._device_id:
                self._apply_snapshot(device)
                break
        self.async_write_ha_state()

    @property
    def unique_id(self) -> str:
        return self._attr_unique_id

    @property
    def name(self) -> str:
        return self._attr_name

    @property
    def device_info(self) -> dict:
        return {
            "identifiers": {(DOMAIN, self._vendor_id)},
            "name": self._attr_name,
            "manufacturer": "Hitachi",
            "model": "AirCloud Climate",
        }

    @property
    def available(self) -> bool:
        return self._available

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "family_id": self._family_id,
            "air_cloud_id": self._device_id,
            "cloud_id": self._cloud_id,
            "sys_type": self._sys_type,
        }

    @property
    def supported_features(self) -> ClimateEntityFeature:
        features = ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        if not self._mode_settings or any(
            s.get("temperature_enabled", True) for s in self._mode_settings.values()
        ):
            features |= ClimateEntityFeature.TARGET_TEMPERATURE
        if len(self._attr_fan_modes or []) > 1:
            features |= ClimateEntityFeature.FAN_MODE
        if len(self._attr_swing_modes or []) > 1:
            features |= ClimateEntityFeature.SWING_MODE
        return features

    @property
    def temperature_unit(self) -> str:
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self) -> float | None:
        return self._room_temp

    @property
    def target_temperature(self) -> float:
        return self._target_temp

    @property
    def target_temperature_step(self) -> float:
        return float(
            self._hass.data.get(DOMAIN, {})
            .get(CONF_TEMP_STEP, {})
            .get(self._device_id, 0.5)
        )

    @property
    def min_temp(self) -> float:
        s = self._mode_settings_for(self._mode)
        ref = float(s.get("reference_temperature", 0.0))
        return float(s.get("min_temperature", 16.0)) + ref

    @property
    def max_temp(self) -> float:
        s = self._mode_settings_for(self._mode)
        ref = float(s.get("reference_temperature", 0.0))
        return float(s.get("max_temperature", 32.0)) + ref

    @property
    def hvac_mode(self) -> HVACMode:
        if self._power == "OFF":
            return HVACMode.OFF
        return RAW_TO_HVAC.get(self._mode, HVACMode.OFF)

    @property
    def hvac_modes(self) -> list[HVACMode]:
        return self._attr_hvac_modes

    @property
    def fan_mode(self) -> str:
        return RAW_TO_FAN.get(self._fan_speed, FAN_AUTO)

    @property
    def fan_modes(self) -> list[str]:
        return self._attr_fan_modes

    @property
    def swing_mode(self) -> str:
        return RAW_TO_SWING.get(self._fan_swing, SWING_OFF)

    @property
    def swing_modes(self) -> list[str]:
        return self._attr_swing_modes

    async def async_turn_on(self) -> None:
        await self._send_command(power="ON")

    async def async_turn_off(self) -> None:
        await self._send_command(power="OFF")

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self._send_command(power="OFF")
            return
        raw_mode = HVAC_TO_RAW.get(hvac_mode, self._mode)
        mode_changed = raw_mode != self._mode
        await self._send_command(
            power="ON",
            mode=raw_mode,
            target_temp=self._default_temp(raw_mode) if mode_changed else None,
            fan_speed=(
                self._mode_settings_for(raw_mode).get("default_fan_speed")
                if mode_changed else None
            ),
        )

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        raw = FAN_TO_RAW.get(fan_mode, DEFAULT_FAN_SPEED)
        await self._send_command(fan_speed=raw)

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        raw = SWING_TO_RAW.get(swing_mode, DEFAULT_FAN_SWING)
        await self._send_command(fan_swing=raw)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        hvac_mode = kwargs.get("hvac_mode")
        if hvac_mode == HVACMode.OFF:
            await self._send_command(power="OFF", target_temp=float(temp))
            return
        desired_mode = (
            HVAC_TO_RAW.get(hvac_mode, self._mode)
            if hvac_mode is not None
            else self._mode
        )
        desired_power = "ON" if hvac_mode is not None and hvac_mode != HVACMode.OFF else self._power
        await self._send_command(power=desired_power, mode=desired_mode, target_temp=float(temp))

    async def async_update(self) -> None:
        if self._command_in_flight:
            return
        devices = await self._api.load_climate_data(self._family_id)
        for device in devices:
            if device.get("id") == self._device_id:
                self._apply_snapshot(device)
                break
