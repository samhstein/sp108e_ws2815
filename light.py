import logging
import voluptuous as vol
from .pyledshop import WifiLedShopLight

import homeassistant.helpers.config_validation as cv
# Import the device class from the component that you want to support
from homeassistant.components.light import PLATFORM_SCHEMA, LightEntity
from homeassistant.const import CONF_HOST, CONF_NAME

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_NAME): cv.string,
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    # Assign configuration variables.
    # The configuration check takes care they are present.
    host = config[CONF_HOST]
    name = config[CONF_NAME]
    # Add device
    add_entities([WifiLedShopLight(host, name)])
