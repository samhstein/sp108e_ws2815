from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .pyledshop import WifiLedShopLight
from .const import DOMAIN

import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up SP108E WS2815 light from a config entry."""
    host = entry.data["host"]
    name = entry.data["name"]
    config = {**entry.data, **entry.options}

    light = await hass.async_add_executor_job(WifiLedShopLight, host, name, config)

    async_add_entities([light], update_before_add=True)

    domain_data = hass.data.setdefault(DOMAIN, {})
    entities = domain_data.setdefault("entities", {})
    entities[entry.entry_id] = light
