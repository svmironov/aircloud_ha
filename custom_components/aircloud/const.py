import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD


DOMAIN = 'air_cloud'
API = 'api'
PLATFORM_CLIMATE = "climate"
API_HOST = 'https://api-global-prod.aircloudhome.com/'
TOKEN_URN = 'iam/auth/sign-in'
WHO_URN = 'iam/user/v2/who-am-i'
CONTROL_URN = 'rac/basic-idu-control/general-control-command'
WSS_URL = 'wss://notification-global-prod.aircloudhome.com/rac-notifications/websocket'

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_EMAIL): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

CONFIG_FLOW_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)