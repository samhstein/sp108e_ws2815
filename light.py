from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .pyledshop import WifiLedShopLight


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up SP108E WS2815 light from a config entry."""
    host = entry.data["host"]
    name = entry.data["name"]

    # Construct in executor to avoid blocking the event loop
    light = await hass.async_add_executor_job(WifiLedShopLight, host, name)

    async_add_entities([light])
