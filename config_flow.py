"""Config flow for sp108e_ws2815 integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN
from .pyledshop import WifiLedShopLight

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required("host"): str,
    vol.Required("name"): str,
    vol.Optional("effect", default="Solid (custom color)"): str,
    vol.Optional("speed", default=255): vol.All(vol.Coerce(int), vol.Clamp(min=0, max=255)),
})


async def validate_input(hass: core.HomeAssistant, data: dict) -> dict:
    """Validate the user input allows us to connect to the controller."""
    try:
        light = await hass.async_add_executor_job(WifiLedShopLight, data["host"], data["name"])
        await hass.async_add_executor_job(light.update)
    except Exception as e:
        _LOGGER.exception("Failed to connect to SP108E controller at %s", data["host"])
        raise CannotConnect from e

    return {
        "title": data["name"],
        "effect": data["effect"],
        "speed": data["speed"],
    }



class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for sp108e_ws2815."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:
            _LOGGER.exception("Unexpected exception during config flow")
            errors["base"] = "unknown"
        else:
            entry_data = {
                "host": user_input["host"],
                "name": user_input["name"],
                "effect": user_input.get("effect", "Solid (custom color)"),
                "speed": user_input.get("speed", 255),
            }
            return self.async_create_entry(title=info["title"], data=entry_data)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate invalid authentication."""
