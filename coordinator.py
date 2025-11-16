"""DataUpdateCoordinator for SP108E WS2815."""
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .pyledshop import WifiLedShopLight

_LOGGER = logging.getLogger(__name__)

# Polling interval - check device status every 30 seconds
UPDATE_INTERVAL = timedelta(seconds=30)


class SP108ECoordinator(DataUpdateCoordinator):
    """Class to manage fetching SP108E data."""

    def __init__(
        self,
        hass: HomeAssistant,
        light: WifiLedShopLight,
    ) -> None:
        """Initialize coordinator."""
        self.light = light

        super().__init__(
            hass,
            _LOGGER,
            name="SP108E WS2815",
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self):
        """Fetch data from SP108E device."""
        try:
            # Run the blocking update() method in executor
            await self.hass.async_add_executor_job(self.light.update)
            return True
        except Exception as err:
            # Device is offline or unreachable
            raise UpdateFailed(f"Error communicating with device: {err}") from err
