"""The sp108e_ws2815 integration."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import asyncio
from .options_flow import OptionsFlowHandler

from .const import DOMAIN
from .coordinator import SP108ECoordinator
from .pyledshop import WifiLedShopLight

PLATFORMS = ["light"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the sp108e_ws2815 component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up sp108e_ws2815 from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Get configuration
    host = entry.data["host"]
    name = entry.data["name"]
    config = {**entry.data, **entry.options}

    # Create the light device instance
    light = await hass.async_add_executor_job(WifiLedShopLight, host, name, config)

    # Create coordinator for automatic polling
    coordinator = SP108ECoordinator(hass, light)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator and light for access by platform
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "light": light,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for options changes
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

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


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_get_options_flow(config_entry):
    return OptionsFlowHandler(config_entry)
