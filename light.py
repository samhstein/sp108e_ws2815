from .pyledshop import WifiLedShopLight
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import HomeAssistantType


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry, async_add_entities):
    host = entry.data.get('host')
    name = entry.data.get('name')
    entity = WifiLedShopLight(host, name)
    async_add_entities([entity])
    return True
