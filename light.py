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
    config = { **entry.data, **entry.options }

    # Construct in executor to avoid blocking the event loop
    light = await hass.async_add_executor_job(WifiLedShopLight, host, name, config)

    async_add_entities([light])
    
    # Store entity for service access
    if "entities" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["entities"] = {}
    hass.data[DOMAIN]["entities"][entry.entry_id] = light
