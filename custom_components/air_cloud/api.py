import aiohttp
import asyncio
import json
import logging
import uuid
from datetime import datetime
from aiohttp import WSMsgType

from .const import HOST_API, URN_AUTH, URN_WHO, URN_WSS, URN_CONTROL, URN_REFRESH_TOKEN

_LOGGER = logging.getLogger(__name__)


class AirCloudApi:
    def __init__(self, login, password):
        self._login = login
        self._password = password
        self._last_token_update = datetime.now()
        self._last_data_update = datetime.now()
        self._token = None
        self._family_id = None
        self._data = None
        self._ref_token = None
        self._session = aiohttp.ClientSession()

    async def validate_credentials(self):
        try:
            await self.__authenticate()
            return True
        except Exception as e:
            logging.error("Failed to validate credentials: %s", str(e))
            return False

    async def __authenticate(self):
        authorization = {"email": self._login, "password": self._password}
        async with self._session.post(HOST_API + URN_AUTH, json=authorization) as response:
            await self.__update_token_data(await response.json())
        self._last_token_update = datetime.now()
        if self._family_id is None:
            await self.__load_family_id()

    async def __refresh_token(self, forced=False):
        now_datetime = datetime.now()
        td = now_datetime - self._last_token_update
        td_minutes = divmod(td.total_seconds(), 60)

        if self._token is None or forced:
            await self.__authenticate()
        elif td_minutes[1] > 5:
            async with self._session.post(HOST_API + URN_REFRESH_TOKEN,
                                          headers={"Authorization": "Bearer " + self._ref_token,
                                                    "isRefreshToken": "true"}) as response:
                await self.__update_token_data(await response.json())
            self._last_token_update = now_datetime

    async def __update_token_data(self, response):
        self._token = response["token"]
        self._ref_token = response["refreshToken"]

    async def __load_family_id(self):
        async with self._session.get(HOST_API + URN_WHO, headers=self.__create_headers()) as response:
            self._family_id = (await response.json())["familyId"]

    async def load_climate_data(self):
        await self.__refresh_token()
        async with self._session.ws_connect(URN_WSS, timeout=60) as ws:
            connection_string = "CONNECT\naccept-version:1.1,1.2\nheart-beat:10000,10000\nAuthorization:Bearer {}\n\n\0\nSUBSCRIBE\nid:{}\ndestination:/notification/{}/{}\nack:auto\n\n\0"
            connection_string = connection_string.format(self._token, str(uuid.uuid4()), str(self._family_id), str(self._family_id))
            await ws.send_str(connection_string)

            try:
                attempt = 0
                max_attempts = 10
                while attempt < max_attempts:
                    attempt += 1
                    msg = await asyncio.wait_for(ws.receive(), timeout=10)
                    if msg.type == WSMsgType.TEXT:
                        if msg.data.startswith("CONNECTED") and "user-name:" not in msg.data:
                            _LOGGER.warning("Websocket connection failed. Re-authenticating.")
                            await ws.close()
                            await self.__refresh_token(forced=True)
                            await ws.send_str(connection_string)
                            attempt = 0
                        elif msg.data.startswith("MESSAGE") and "{" in msg.data:
                            response = msg.data
                            break
                    elif msg.type == WSMsgType.CLOSED:
                        _LOGGER.warning("WebSocket connection is closed.")
                        return None
                else:
                    _LOGGER.warning("Unable to find '{' symbol after {} attempts".format(max_attempts))
                    await ws.close()
                    return None
            except asyncio.TimeoutError:
                _LOGGER.warning("WebSocket connection timed out while receiving data")
                await ws.close()
                return None

        _LOGGER.debug("AirCloud climate data: " + str(response))
        message = "{" + response.partition("{")[2].replace("\0", "")
        struct = json.loads(message)
        return struct["data"]

    async def execute_command(self, id, power, idu_temperature, mode, fan_speed, fan_swing, humidity):
        await self.__refresh_token()
        command = {"power": power, "iduTemperature": idu_temperature, "mode": mode, "fanSpeed": fan_speed,
                   "fanSwing": fan_swing, "humidity": humidity}
        async with self._session.put(HOST_API + URN_CONTROL + "/" + str(id) + "?familyId=" + str(self._family_id),
                                     headers=self.__create_headers(), json=command) as response:
            _LOGGER.debug("AirCloud command request: " + str(command))
            _LOGGER.debug("AirCloud command response: " + str(await response.text()))

    def __create_headers(self):
        return {"Authorization": "Bearer " + self._token}

    async def close_session(self):
        await self._session.close()
