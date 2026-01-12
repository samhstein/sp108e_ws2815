import voluptuous as vol
from homeassistant import config_entries

from .pyledshop.effects import MONO_EFFECTS, PRESET_EFFECTS

ALL_EFFECTS = list({**MONO_EFFECTS, **PRESET_EFFECTS}.keys())

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry  # <-- use a private attr

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self._config_entry.data, **self._config_entry.options}

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "effect",
                        default=current.get("effect", "Solid (custom color)"),
                    ): vol.In(ALL_EFFECTS),
                    vol.Optional(
                        "speed",
                        default=current.get("speed", 255),
                    ): vol.All(vol.Coerce(int), vol.Clamp(min=0, max=255)),
                }
            ),
        )
