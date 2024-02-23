import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD


DOMAIN = "air_cloud"
API = "api"
PLATFORM_CLIMATE = "climate"
CONF_TEMP_ADJUST = "temp_adjust"
HOST_API = "https://api-global-prod.aircloudhome.com/"
URN_AUTH = "iam/auth/sign-in"
URN_REFRESH_TOKEN = "iam/auth/refresh-token"
URN_WHO = "iam/user/v2/who-am-i"
URN_CONTROL = "rac/basic-idu-control/general-control-command"
URN_WSS = "wss://notification-global-prod.aircloudhome.com/rac-notifications/websocket"
SERVICE_EXEC_COMMAND = "exec_command"
ARG_ID = "id"
ARG_POWER = "power"
ARG_TARGET_TEMP = "target_temp"
ARG_MODE = "mode"
ARG_FAN_SPEED = "fan_speed"
ARG_FAN_SWING = "fan_swing"
ARG_HUMIDITY = "humidity"


SERVICE_EXEC_COMMAND_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(ARG_ID): cv.positive_int,
        vol.Required(ARG_POWER): cv.string,
        vol.Required(ARG_TARGET_TEMP): cv.positive_float,
        vol.Required(ARG_MODE): cv.string,
        vol.Required(ARG_FAN_SPEED): cv.string,
        vol.Required(ARG_FAN_SWING): cv.string,
        vol.Required(ARG_HUMIDITY): cv.positive_int,
    }
)

CONFIG_FLOW_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_TEMP_ADJUST): vol.Coerce(float),
    }
)