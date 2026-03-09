import aiohttp
import asyncio
import json
import logging
import uuid
from datetime import datetime
from aiohttp import WSMsgType

from .const import (
    HOST_API,
    URN_AUTH,
    URN_CONTROL,
    URN_ENERGY_CONSUMPTION_SUMMARY,
    URN_RAC_CONFIGURATION,
    URN_REFRESH_TOKEN,
    URN_WHO,
    URN_WSS,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)


class AirCloudApi:
    def __init__(self, login, password):
        self._login = login
        self._password = password
        self._last_token_update = datetime.now()
        self._last_data_update = datetime.now()
        self._token = None
        self._data = None
        self._ref_token = None
        self._session = aiohttp.ClientSession()

    async def validate_credentials(self):
        try:
            await self.__authenticate()
            return True
        except Exception as e:
            _LOGGER.error("Failed to validate credentials: %s", str(e))
            return False

    async def __authenticate(self):
        authorization = {"email": self._login, "password": self._password}

        async with self._session.post(
            HOST_API + URN_AUTH,
            json=authorization,
            headers={"User-Agent": USER_AGENT},
        ) as response:
            response_text = await response.text()
            _LOGGER.debug(
                "air_cloud.api: auth status=%s body=%s",
                response.status,
                response_text[:500],
            )
            response.raise_for_status()
            await self.__update_token_data(json.loads(response_text))

        self._last_token_update = datetime.now()

    async def __refresh_token(self, forced=False):
        now_datetime = datetime.now()
        td = now_datetime - self._last_token_update
        td_minutes = divmod(td.total_seconds(), 60)

        if self._token is None or forced:
            await self.__authenticate()
        elif td_minutes[1] > 5:
            async with self._session.post(
                HOST_API + URN_REFRESH_TOKEN,
                headers={
                    "Authorization": f"Bearer {self._ref_token}",
                    "isRefreshToken": "true",
                    "User-Agent": USER_AGENT,
                },
            ) as response:
                response_text = await response.text()
                _LOGGER.debug(
                    "air_cloud.api: refresh status=%s body=%s",
                    response.status,
                    response_text[:500],
                )
                response.raise_for_status()
                await self.__update_token_data(json.loads(response_text))
            self._last_token_update = now_datetime

    async def __update_token_data(self, response):
        self._token = response["token"]
        self._ref_token = response["refreshToken"]

    async def load_family_ids(self):
        await self.__refresh_token()
        async with self._session.get(
            HOST_API + URN_WHO,
            headers=self.__create_headers(),
        ) as response:
            response_text = await response.text()
            _LOGGER.debug(
                "air_cloud.api: who status=%s body=%s",
                response.status,
                response_text[:1000],
            )
            response.raise_for_status()
            response_data = json.loads(response_text)
            return [item["familyId"] for item in response_data]

    async def load_energy_consumption_summary(self, family_id):
        await self.__refresh_token()
        async with self._session.post(
            f"{HOST_API}{URN_ENERGY_CONSUMPTION_SUMMARY}?familyId={family_id}",
            headers=self.__create_headers(),
            json={"from": "2000-01-01", "to": "2099-12-31"},
        ) as response:
            response_text = await response.text()
            _LOGGER.debug(
                "air_cloud.api: energy status=%s family_id=%s body=%s",
                response.status,
                family_id,
                response_text[:1000],
            )
            response.raise_for_status()
            return json.loads(response_text)

    async def load_rac_configuration(self, cloud_ids):
        await self.__refresh_token()
        async with self._session.post(
            HOST_API + URN_RAC_CONFIGURATION,
            headers=self.__create_headers(),
            json=cloud_ids,
        ) as response:
            response_text = await response.text()
            _LOGGER.debug(
                "air_cloud.api: rac config status=%s cloud_ids=%s body=%s",
                response.status,
                cloud_ids,
                response_text[:1000],
            )
            response.raise_for_status()
            return json.loads(response_text)

    async def load_climate_data(self, family_id):
        if self._session.closed:
            _LOGGER.debug("air_cloud.api: sessão fechada em load_climate_data")
            return []

        await self.__refresh_token()

        async with self._session.ws_connect(
            URN_WSS, timeout=60, headers={"User-Agent": USER_AGENT}
        ) as ws:
            connection_string = (
                "CONNECT\naccept-version:1.1,1.2\nheart-beat:10000,10000\n"
                "Authorization:Bearer {}\n\n\0\n"
                "SUBSCRIBE\nid:{}\ndestination:/notification/{}/{}\nack:auto\n\n\0"
            ).format(
                self._token,
                str(uuid.uuid4()),
                str(family_id),
                str(family_id),
            )

            await ws.send_str(connection_string)

            try:
                attempt = 0
                max_attempts = 10
                response = None

                while attempt < max_attempts:
                    attempt += 1
                    msg = await asyncio.wait_for(ws.receive(), timeout=10)

                    if msg.type == WSMsgType.TEXT:
                        if msg.data.startswith("CONNECTED") and "user-name:" not in msg.data:
                            await ws.close()

                            await self.__refresh_token(forced=True)
                            ws = await self._session.ws_connect(
                                URN_WSS,
                                timeout=60,
                                headers={"User-Agent": USER_AGENT},
                            )
                            connection_string = (
                                "CONNECT\naccept-version:1.1,1.2\nheart-beat:10000,10000\n"
                                "Authorization:Bearer {}\n\n\0\n"
                                "SUBSCRIBE\nid:{}\ndestination:/notification/{}/{}\nack:auto\n\n\0"
                            ).format(
                                self._token,
                                str(uuid.uuid4()),
                                str(family_id),
                                str(family_id),
                            )
                            await ws.send_str(connection_string)
                            attempt = 0
                            continue

                        elif msg.data.startswith("MESSAGE") and "{" in msg.data:
                            response = msg.data
                            break

                    elif msg.type == WSMsgType.CLOSED:
                        return None

                else:
                    await ws.close()
                    return None

            except asyncio.TimeoutError:
                await ws.close()
                return None

        if not response:
            return None

        _LOGGER.debug("AirCloud climate data: %s", response)
        message = "{" + response.partition("{")[2].replace("\0", "")
        struct = json.loads(message)
        return struct["data"]

    async def execute_command(self, id, family_id, power, temperature, mode, fan_speed, fan_swing, humidity):
        if self._session.closed:
            _LOGGER.debug("air_cloud.api: sessão fechada em execute_command")
            return

        await self.__refresh_token()

        if mode == "AUTO":
            command = {
                "power": power,
                "relativeTemperature": temperature,
                "mode": mode,
                "fanSpeed": fan_speed,
                "fanSwing": fan_swing,
            }
        else:
            command = {
                "power": power,
                "iduTemperature": temperature,
                "mode": mode,
                "fanSpeed": fan_speed,
                "fanSwing": fan_swing,
            }

        url = f"{HOST_API}{URN_CONTROL}/{id}?familyId={family_id}"

        _LOGGER.debug("air_cloud.api: PUT %s payload=%s", url, command)

        async with self._session.put(
            url,
            headers=self.__create_headers(),
            json=command,
        ) as response:
            response_text = await response.text()
            _LOGGER.debug(
                "air_cloud.api: command status=%s body=%s",
                response.status,
                response_text[:1000],
            )
            response.raise_for_status()

    def __create_headers(self):
        return {
            "Authorization": f"Bearer {self._token}",
            "User-Agent": USER_AGENT,
        }

    async def close_session(self):
        await self._session.close()