import requests
import uuid
import json
import logging

from datetime import datetime
from websocket import create_connection
from .const import API_HOST, TOKEN_URN, WHO_URN, WSS_URL, CONTROL_URN

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

    def __refresh_token(self):
        now_datetime = datetime.now()
        td = now_datetime - self._last_token_update
        td_minutes = divmod(td.total_seconds(), 60)

        if self._token is None or td_minutes[1] > 5:
            authorization = {"email": self._login, "password": self._password}
            response = requests.post(API_HOST + TOKEN_URN, json = authorization)
            self._token = response.json()["token"]
            if self._family_id is None:
                self.__load_family_id()
        
            self._last_token_update = now_datetime

    def __load_family_id(self):
        response = requests.get(API_HOST + WHO_URN, headers =  self.__create_headers())
        self._family_id = response.json()["familyId"]

    def load_climate_data(self):
        self.__refresh_token()
        ws = create_connection("wss://notification-global-prod.aircloudhome.com/rac-notifications/websocket")
        ws.send("CONNECT\naccept-version:1.1,1.2\nheart-beat:10000,10000\nAuthorization:Bearer " + self._token + "\n\n\0\nSUBSCRIBE\nid:" + str(uuid.uuid4()) + "\ndestination:/notification/" + str(self._family_id) + "/" + str(self._family_id) + "\nack:auto\n\n\0")

        response = None
        while response is None or "{" not in response:
            response = ws.recv()
        ws.close()

        _LOGGER.debug("AirCloud climate data: " + str(response))
        message = "{" + response.partition("{")[2].replace("\0", "")
        struct = json.loads(message)

        return struct["data"]
    
    def execute_command(self, id, power, idu_temperature, mode, fan_speed, fan_swing, humidity):
        self.__refresh_token()
        command = {"power": power, "iduTemperature": idu_temperature, "mode": mode, "fanSpeed": fan_speed, "fanSwing": fan_swing, "humidity": humidity}
        response = requests.put(API_HOST + CONTROL_URN + "/" + str(id) + "?familyId=" + str(self._family_id), headers=self.__create_headers(), json=command)
        _LOGGER.debug("AirCloud command request: " + str(command))
        _LOGGER.debug("AirCloud command response: " + str(response.content))
     
    def __create_headers(self):
       return {"Authorization": "Bearer " + self._token}
    