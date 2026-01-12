"""The sp108e_ws2815 integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PLATFORMS: list[str] = ["light"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the sp108e_ws2815 component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up sp108e_ws2815 from a config entry."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data.setdefault("entities", {})          # for your service access if you keep it
    domain_data.setdefault("hosts", {})[entry.entry_id] = entry.data.get("host")

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        domain_data = hass.data.get(DOMAIN, {})
        domain_data.get("hosts", {}).pop(entry.entry_id, None)
        domain_data.get("entities", {}).pop(entry.entry_id, None)
    return unload_ok
