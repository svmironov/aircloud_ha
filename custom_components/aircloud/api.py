import requests
import uuid
import json

from websocket import create_connection
from .const import API_HOST, TOKEN_URN, WHO_URN, WSS_URL, CONTROL_URN


class AirCloudApi:
    def __init__(self, login, password):
        self._login = login
        self._password = password
        self._family_id = None

    def __refresh_token(self):
        authorization = {'email': self._login, 'password': self._password}
        response = requests.post(API_HOST + TOKEN_URN, json = authorization)
        self._token = response.json()['token']
        if self._family_id is None:
            self.__load_family_id()

    def __load_family_id(self):
        response = requests.get(API_HOST + WHO_URN, headers =  self.__create_headers())
        self._family_id = response.json()['familyId']

    def load_climate_data(self):
        self.__refresh_token()
        ws = create_connection("wss://notification-global-prod.aircloudhome.com/rac-notifications/websocket")
        ws.send('CONNECT\naccept-version:1.1,1.2\nheart-beat:10000,10000\nAuthorization:Bearer '+ self._token +'\n\n\0\nSUBSCRIBE\nid:' + str(uuid.uuid4()) +'\ndestination:/notification/' + str(self._family_id) + '/' + str(self._family_id) + '\nack:auto\n\n\0')
        ws.recv()

        message = '{' + ws.recv().partition("{")[2].replace('\0', '')
        ws.close()
        struct = json.loads(message)
       
        return struct['data']
    
    def execute_command(self, id, power, iduTemperature, mode, fanSpeed, fanSwing):
        self.__refresh_token()
        command = {'id': id, 'power': power, 'iduTemperature': iduTemperature, 'mode': mode, 'fanSpeed': fanSpeed, 'fanSwing': fanSwing}
        requests.put(API_HOST + CONTROL_URN + '/' + str(id) + '?familyId=' + str(self._family_id), headers = self.__create_headers(), json = command)
     
    def __create_headers(self):
       return { 'Authorization' : 'Bearer ' + self._token}
    