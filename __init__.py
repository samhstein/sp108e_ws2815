"""The sp108e_ws2815 integration."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import asyncio
from .options_flow import OptionsFlowHandler

from .const import DOMAIN

PLATFORMS = ["light"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the sp108e_ws2815 component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up sp108e_ws2815 from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data.get('host')
    
    # Store entities by entry_id for service access
    if "entities" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["entities"] = {}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def async_get_options_flow(config_entry):
    return OptionsFlowHandler(config_entry)
