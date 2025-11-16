"""Light platform for SP108E WS2815."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_HS_COLOR,
    ATTR_WHITE,
    ATTR_EFFECT,
    ColorMode,
    LightEntityFeature,
    LightEntity,
)

from .const import DOMAIN
from .coordinator import SP108ECoordinator
from .pyledshop import WifiLedShopLight


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up SP108E WS2815 light from a config entry."""
    # Get coordinator and light from hass.data
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    light = data["light"]

    # Create coordinator-based entity wrapper
    async_add_entities([SP108ELight(coordinator, light)])


class SP108ELight(CoordinatorEntity, LightEntity):
    """Representation of SP108E WS2815 light with coordinator support."""

    def __init__(self, coordinator: SP108ECoordinator, light: WifiLedShopLight) -> None:
        """Initialize the light."""
        super().__init__(coordinator)
        self._light = light

        # Copy attributes from the underlying light device
        self._attr_name = light._attr_name
        self._attr_unique_id = light._attr_unique_id
        self._attr_supported_color_modes = light._attr_supported_color_modes
        self._attr_color_mode = light._attr_color_mode
        self._attr_supported_features = light._attr_supported_features

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._light.is_on

    @property
    def brightness(self):
        """Return the brightness of the light."""
        return self._light.brightness

    @property
    def white_value(self):
        """Return the white value of the light."""
        return self._light.white_value

    @property
    def hs_color(self):
        """Return the hue and saturation color value."""
        return self._light.hs_color

    @property
    def effect_list(self):
        """Return the list of supported effects."""
        return self._light.effect_list

    @property
    def effect(self):
        """Return the current effect."""
        return self._light.effect

    @property
    def device_info(self):
        """Return device information."""
        return self._light.device_info

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        return self._light.extra_state_attributes

    async def async_turn_on(self, **kwargs):
        """Turn the light on."""
        await self.hass.async_add_executor_job(self._light.turn_on, **kwargs)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        await self.hass.async_add_executor_job(self._light.turn_off, **kwargs)
        await self.coordinator.async_request_refresh()
