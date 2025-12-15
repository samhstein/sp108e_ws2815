import socket
import logging
import asyncio
from time import sleep
from .effects import MONO_EFFECTS, PRESET_EFFECTS
from .constants import Command, CommandFlag
from .utils import clamp
from .WifiLedShopLightState import WifiLedShopLightState

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_HS_COLOR,
    ATTR_WHITE,
    ATTR_EFFECT,
    ColorMode,
    LightEntityFeature,
    LightEntity,
)
import homeassistant.util.color as color_util

_LOGGER = logging.getLogger(__name__)


class WifiLedShopLight(LightEntity):
    """A Wifi LED Shop Light."""

    def __init__(self, ip, name, config, port=8189, timeout=3, retries=5):
        self._ip = ip
        self._default_effect = config.get("effect", "Solid (custom color)")
        self._default_speed = config.get("speed", 255)
        self._port = port
        self._timeout = timeout
        self._retries = retries
        self._state = WifiLedShopLightState()
        self._sock = None
        self._hass = None  # Will be set by async_added_to_hass
        self._update_lock = asyncio.Lock()

        self._attr_name = name
        self._attr_supported_color_modes = {ColorMode.RGB}
        self._attr_color_mode = ColorMode.RGB
        self._attr_supported_features = LightEntityFeature.EFFECT

        # Try to get unique_id, but fall back to IP-based ID if connection fails
        try:
            id_response = self.send_command(Command.GET_ID, [])
            if id_response:
                self._attr_unique_id = id_response.decode("utf-8")
            else:
                self._attr_unique_id = f"sp108e_{ip}_{port}"
        except Exception:
            # If we can't get the ID, use a fallback based on IP and port
            self._attr_unique_id = f"sp108e_{ip}_{port}"

        # Don't update during init - let async_added_to_hass handle it

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._sock.close()

    def set_color(self, r=0, g=0, b=0):
        r, g, b = clamp(r), clamp(g), clamp(b)
        self.send_command(Command.SET_COLOR, [r, g, b])
        # Update state after successful command
        self._state.color = (r, g, b)

    def set_brightness(self, brightness=0):
        brightness = clamp(brightness)
        self.send_command(Command.SET_BRIGHTNESS, [brightness])
        self._state.brightness = brightness

    def set_white(self, white=0):
        white = clamp(white)
        self.send_command(Command.SET_WHITE, [white])
        self._state.white = white

    def set_speed(self, speed=0):
        speed = clamp(speed)
        self.send_command(Command.SET_SPEED, [speed])
        self._state.speed = speed

    def set_effect(self, effect):
        both = {**MONO_EFFECTS, **PRESET_EFFECTS}
        if effect not in both:
            _LOGGER.warning("Unknown effect: %s", effect)
            return
        preset = both[effect]
        # Don't clamp preset values - they can be 0-212
        # MonoEffect values are 205-212, PRESET_EFFECTS are 0-195
        self.send_command(Command.SET_PRESET, [preset])
        self._state.mode = preset

    def set_custom(self, custom):
        custom = clamp(custom, 1, 12)
        self._state.mode = custom
        self.send_command(Command.SET_CUSTOM, [custom])

    def _toggle_sync(self):
        """Toggle the light state (synchronous)."""
        self.send_command(Command.TOGGLE, [])
        # Invert state optimistically - will be corrected by next update
        self._state.is_on = not self._state.is_on

    async def async_turn_on(self, **kwargs):
        """Turn on the light with optional parameters (async)."""
        if self._hass is None:
            return
        
        # Only apply defaults if turning on from off state
        # If already on and just changing color/effect, don't override
        was_off = not self._state.is_on
        
        # If turning on from off, apply defaults first
        if was_off:
            if ATTR_EFFECT not in kwargs:
                await self._hass.async_add_executor_job(
                    self.set_effect, self._default_effect
                )
            if "speed" not in kwargs:
                await self._hass.async_add_executor_job(
                    self.set_speed, self._default_speed
                )
        
        # Process all provided parameters
        for k, v in kwargs.items():
            if k == ATTR_BRIGHTNESS:
                await self._hass.async_add_executor_job(self.set_brightness, v)
            elif k == "rgb_color":
                await self._hass.async_add_executor_job(self.set_color, *v)
            elif k == ATTR_HS_COLOR:
                r, g, b = color_util.color_hs_to_RGB(*v)
                await self._hass.async_add_executor_job(self.set_color, r, g, b)
            elif k == ATTR_WHITE:
                await self._hass.async_add_executor_job(self.set_white, v)
            elif k == ATTR_EFFECT:
                await self._hass.async_add_executor_job(self.set_effect, v)
            elif k == "speed":
                await self._hass.async_add_executor_job(self.set_speed, v)
            else:
                _LOGGER.debug("Unknown control key: %s", k)

        # Turn on if it was off
        if was_off:
            await self._hass.async_add_executor_job(self._toggle_sync)
        
        # Schedule an update to get the actual state
        await self.async_update()

    async def async_turn_off(self, **kwargs):
        """Turn off the light (async)."""
        if self._hass is None:
            return
        if self._state.is_on:
            await self._hass.async_add_executor_job(self._toggle_sync)
            # Schedule an update to get the actual state
            await self.async_update()

    def set_segments(self, segments):
        self.send_command(Command.SET_SEGMENT_COUNT, [segments])

    def set_lights_per_segment(self, lights_per_segment):
        data = list(lights_per_segment.to_bytes(2, byteorder='little'))
        self.send_command(Command.SET_LIGHTS_PER_SEGMENT, data)

    def set_calculated_segments(self, total_lights, segments):
        self.set_segments(segments)
        self.set_lights_per_segment(int(total_lights / segments))

    def send_command(self, command, data=[]):
        result = None
        min_data_len = 3
        padded_data = data + [0] * (min_data_len - len(data))
        raw_data = [CommandFlag.START, *padded_data, command, CommandFlag.END]
        attempts = 0
        last_exception = None
        
        while attempts <= self._retries:
            try:
                _LOGGER.debug("Attempting to connect to %s:%s (attempt %d/%d)", 
                             self._ip, self._port, attempts + 1, self._retries + 1)
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._sock.settimeout(self._timeout)
                self._sock.connect((self._ip, self._port))
                _LOGGER.debug("Connected to %s:%s, sending command %s", 
                             self._ip, self._port, command)
                self._sock.sendall(bytes(raw_data))
                if command in [Command.GET_ID, Command.SYNC]:
                    result = self._sock.recv(1024)
                    _LOGGER.debug("Received %d bytes from device", len(result) if result else 0)
                self._sock.shutdown(socket.SHUT_RDWR)
                self._sock.close()
                self._sock = None
                return result
            except (socket.timeout, BrokenPipeError, ConnectionRefusedError, 
                    ConnectionResetError, OSError, socket.gaierror, socket.herror) as e:
                last_exception = e
                _LOGGER.warning("Connection attempt %d/%d failed: %s", 
                               attempts + 1, self._retries + 1, str(e))
                if self._sock:
                    try:
                        self._sock.close()
                    except:
                        pass
                    self._sock = None
                
                if attempts < self._retries:
                    attempts += 1
                    sleep(0.1 * attempts)  # Exponential backoff
                else:
                    # Raise a more informative error
                    error_msg = f"Failed to connect to {self._ip}:{self._port} after {self._retries + 1} attempts. "
                    if isinstance(e, ConnectionRefusedError):
                        error_msg += f"Connection refused - check if device is powered on and port {self._port} is open."
                    elif isinstance(e, socket.timeout):
                        error_msg += "Connection timeout - check network connectivity and firewall settings."
                    elif isinstance(e, (socket.gaierror, socket.herror)):
                        error_msg += f"DNS/Host resolution error: {str(e)} - verify the IP address is correct."
                    elif isinstance(e, OSError):
                        error_msg += f"Network error: {str(e)}"
                    else:
                        error_msg += f"Error: {str(e)}"
                    _LOGGER.error(error_msg)
                    raise ConnectionError(error_msg) from e

    def update(self):
        """Update state from device (synchronous)."""
        response = self.send_command(Command.SYNC, [])
        if response:
            self._state.update_from_sync(bytearray(response))

    async def async_update(self):
        """Update state from device (async for Home Assistant)."""
        if self._hass is None:
            return
        async with self._update_lock:
            try:
                response = await self._hass.async_add_executor_job(
                    self.send_command, Command.SYNC, []
                )
                if response:
                    self._state.update_from_sync(bytearray(response))
            except Exception as e:
                _LOGGER.warning("Failed to update state: %s", e)

    async def async_added_to_hass(self):
        """Called when entity is added to Home Assistant."""
        self._hass = self.hass
        # Do initial update
        await self.async_update()

    def __repr__(self):
        return f"""WifiLedShopLight @ {self._ip}:{self._port}
  state: {self._state}
  unique_id: {self._attr_unique_id}
"""

    @property
    def is_on(self):
        return self._state.is_on

    @property
    def brightness(self):
        return self._state.brightness

    @property
    def white_value(self):
        return self._state.white

    @property
    def hs_color(self):
        r, g, b = self._state.color
        return color_util.color_RGB_to_hs(r, g, b)

    @property
    def effect_list(self):
        return list({**MONO_EFFECTS, **PRESET_EFFECTS})

    @property
    def effect(self):
        both = {**MONO_EFFECTS, **PRESET_EFFECTS}
        return next((k for k, v in both.items() if v == self._state.mode), None)

    @property
    def device_info(self):
        return {
            "identifiers": {("wifi-led-strip-controller", self._attr_unique_id)},
            "manufacturer": "BTF-LIGHTING",
            "name": self._attr_name,
            "model": "sp108e",
        }
  
    @property
    def extra_state_attributes(self):
        r, g, b = self._state.color
        return {
            "speed": self._state.speed,
            "default_effect": self._default_effect,
            "current_rgb": f"rgb({r}, {g}, {b})"
        }
