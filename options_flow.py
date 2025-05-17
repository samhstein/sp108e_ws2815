import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .pyledshop.effects import MONO_EFFECTS

OPTIONS_SCHEMA = vol.Schema({
    vol.Optional("effect", default="Solid (custom color)"): vol.In(list(MONO_EFFECTS)),
    vol.Optional("speed", default=255): vol.All(vol.Coerce(int), vol.Clamp(min=0, max=255)),
})

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=OPTIONS_SCHEMA,
        )

@callback
def async_get_options_flow(config_entry):
    return OptionsFlowHandler(config_entry)
