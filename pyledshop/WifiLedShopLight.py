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
    ATTR_BRIGHTNESS_PCT,
    ATTR_BRIGHTNESS_STEP,
    ATTR_BRIGHTNESS_STEP_PCT,
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
        self._brightness_task = None  # For debouncing brightness changes
        self._command_lock = asyncio.Lock()  # Prevent concurrent commands
        self._desired_brightness = None  # Source of truth for brightness
        self._desired_state = None  # Source of truth for on/off state
        self._desired_color = None  # Source of truth for color
        self._desired_effect = None  # Source of truth for effect

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
        target = (r, g, b)

        # Send the color command once
        self.send_command(Command.SET_COLOR, [r, g, b])
        self._desired_color = target
        self._state.color = target

        # Best-effort verification: read back state once and, if the color
        # does not match what we requested, resend the command a second time.
        try:
            response = self.send_command(Command.SYNC, [])
            if response:
                verify_state = WifiLedShopLightState()
                verify_state.update_from_sync(bytearray(response))
                if verify_state.color != target:
                    _LOGGER.debug(
                        "Color verification mismatch (got %s, expected %s); resending",
                        verify_state.color,
                        target,
                    )
                    self.send_command(Command.SET_COLOR, [r, g, b])
                    self._desired_color = target
                    self._state.color = target
        except Exception as e:
            # If verification fails (timeout, etc.), don't break the flow –
            # we already sent the color command once.
            _LOGGER.debug("Color verification failed: %s", e)

    def set_brightness(self, brightness=0):
        brightness = clamp(brightness)
        self.send_command(Command.SET_BRIGHTNESS, [brightness])
        # Set as source of truth - this is what we want
        self._desired_brightness = brightness
        # Update state optimistically for immediate feedback
        self._state.brightness = brightness

    def set_white(self, white=0):
        white = clamp(white)
        self.send_command(Command.SET_WHITE, [white])
        # Don't update state optimistically - let sync handle it

    def set_speed(self, speed=0):
        speed = clamp(speed)
        self.send_command(Command.SET_SPEED, [speed])
        # Don't update state optimistically - let sync handle it

    def set_effect(self, effect, brightness=None):
        both = {**MONO_EFFECTS, **PRESET_EFFECTS}
        if effect not in both:
            _LOGGER.warning("Unknown effect: %s", effect)
            return
        preset = both[effect]
        # Don't clamp preset values - they can be 0-212
        # MonoEffect values are 205-212, PRESET_EFFECTS are 0-195
        self.send_command(Command.SET_PRESET, [preset])
        # Set as source of truth - this is what we want
        self._desired_effect = effect
        # Update state optimistically for immediate feedback
        self._state.mode = preset
        # If brightness is provided with effect, set it too
        if brightness is not None:
            self.set_brightness(brightness)

    def set_custom(self, custom):
        custom = clamp(custom, 1, 12)
        self._state.mode = custom
        self.send_command(Command.SET_CUSTOM, [custom])

    def _toggle_sync(self, desired_state=None):
        """Toggle the light state (synchronous).
        
        Args:
            desired_state: If provided, toggle until this state is reached.
                          None means just toggle once.
        """
        if desired_state is not None:
            # Toggle until we reach desired state
            max_attempts = 3
            for attempt in range(max_attempts):
                self.send_command(Command.TOGGLE, [])
                # Small delay to let device process
                sleep(0.1)
                # Check if we need to toggle again
                if attempt < max_attempts - 1:
                    # Sync to check actual state
                    try:
                        response = self.send_command(Command.SYNC, [])
                        if response:
                            actual_state = bytearray(response)[1]  # IS_ON position
                            if bool(actual_state) == desired_state:
                                break
                    except:
                        pass
        else:
            # Just toggle once
            self.send_command(Command.TOGGLE, [])
        
        # Update desired state as source of truth
        if desired_state is not None:
            self._desired_state = desired_state
            self._state.is_on = desired_state
        else:
            # Toggle desired state
            self._desired_state = not self._state.is_on if self._desired_state is None else not self._desired_state
            self._state.is_on = self._desired_state

    async def _sync_state(self):
        """Force sync state from device."""
        await self.async_update()

    async def async_turn_on(self, **kwargs):
        """Turn on the light with optional parameters (async)."""
        if self._hass is None:
            return
        
        async with self._command_lock:
            # Check current state (use desired state if available, otherwise sync)
            if self._desired_state is None:
                await self._sync_state()
            was_off = not (
                self._desired_state if self._desired_state is not None else self._state.is_on
            )
            
            # Set desired state as source of truth
            self._desired_state = True
            
            # Process all provided parameters
            # Handle brightness separately (including *_pct and *_step variants)
            current_brightness = (
                self._desired_brightness
                if self._desired_brightness is not None
                else self._state.brightness
            )

            brightness_value = None
            if ATTR_BRIGHTNESS in kwargs and kwargs[ATTR_BRIGHTNESS] is not None:
                brightness_value = kwargs[ATTR_BRIGHTNESS]
            elif ATTR_BRIGHTNESS_PCT in kwargs and kwargs[ATTR_BRIGHTNESS_PCT] is not None:
                brightness_value = int(255 * kwargs[ATTR_BRIGHTNESS_PCT] / 100)
            elif ATTR_BRIGHTNESS_STEP in kwargs and kwargs[ATTR_BRIGHTNESS_STEP] is not None:
                brightness_value = clamp(current_brightness + kwargs[ATTR_BRIGHTNESS_STEP])
            elif (
                ATTR_BRIGHTNESS_STEP_PCT in kwargs
                and kwargs[ATTR_BRIGHTNESS_STEP_PCT] is not None
            ):
                delta = int(255 * kwargs[ATTR_BRIGHTNESS_STEP_PCT] / 100)
                brightness_value = clamp(current_brightness + delta)

            # Remove all brightness-related keys from other params
            other_params = {
                k: v
                for k, v in kwargs.items()
                if k
                not in (
                    ATTR_BRIGHTNESS,
                    ATTR_BRIGHTNESS_PCT,
                    ATTR_BRIGHTNESS_STEP,
                    ATTR_BRIGHTNESS_STEP_PCT,
                )
            }

            # If brightness is the only parameter, use debouncing (slider dragging)
            # Otherwise apply immediately (click or combined with other params)
            use_brightness_debounce = (
                brightness_value is not None and len(other_params) == 0 and not was_off
            )

            # Decide which effect to apply:
            # - If an explicit effect was provided, use it
            # - Else, if an RGB/HS color was provided, force Solid (custom color)
            # - Else, if we just turned the light on, use the configured default effect
            has_rgb = "rgb_color" in other_params or ATTR_HS_COLOR in other_params
            explicit_effect = other_params.pop(ATTR_EFFECT, None)

            effect_to_apply = None
            if explicit_effect is not None:
                effect_to_apply = explicit_effect
            elif has_rgb:
                effect_to_apply = "Solid (custom color)"
            elif was_off:
                effect_to_apply = self._default_effect

            if effect_to_apply is not None:
                effect_brightness = (
                    brightness_value
                    if (brightness_value is not None and not use_brightness_debounce)
                    else None
                )
                await self._hass.async_add_executor_job(
                    self.set_effect, effect_to_apply, effect_brightness
                )
                self.async_write_ha_state()

            # Process non-brightness, non-effect parameters immediately
            for k, v in other_params.items():
                if k == "rgb_color":
                    await self._hass.async_add_executor_job(self.set_color, *v)
                    self.async_write_ha_state()
                elif k == ATTR_HS_COLOR:
                    r, g, b = color_util.color_hs_to_RGB(*v)
                    await self._hass.async_add_executor_job(self.set_color, r, g, b)
                    self.async_write_ha_state()
                elif k == ATTR_WHITE:
                    await self._hass.async_add_executor_job(self.set_white, v)
                    self.async_write_ha_state()
                elif k == "speed":
                    await self._hass.async_add_executor_job(self.set_speed, v)
                    self.async_write_ha_state()
                else:
                    _LOGGER.debug("Unknown control key: %s", k)
            
            # If we turned the light on from off and no explicit speed was provided,
            # apply the configured default speed.
            if was_off and "speed" not in kwargs:
                await self._hass.async_add_executor_job(
                    self.set_speed, self._default_speed
                )
                self.async_write_ha_state()

            # Handle brightness
            if brightness_value is not None:
                if use_brightness_debounce:
                    # Cancel any pending brightness operation
                    if self._brightness_task and not self._brightness_task.done():
                        self._brightness_task.cancel()
                        try:
                            await self._brightness_task
                        except asyncio.CancelledError:
                            pass
                    
                    # Optimistic update for immediate UI feedback
                    self._state.brightness = brightness_value
                    self.async_write_ha_state()
                    
                    # Debounce brightness changes (for slider dragging)
                    async def set_brightness_debounced():
                        try:
                            await asyncio.sleep(0.2)  # 200ms debounce
                            await self._hass.async_add_executor_job(self.set_brightness, brightness_value)
                            # Update UI after debounced command
                            self.async_write_ha_state()
                        except asyncio.CancelledError:
                            pass
                    
                    self._brightness_task = asyncio.create_task(set_brightness_debounced())
                else:
                    # Apply immediately (click or combined with other params)
                    await self._hass.async_add_executor_job(self.set_brightness, brightness_value)
                    self.async_write_ha_state()
            
            # Finally, if the light was off when we started, toggle it on *after*
            # effect/color/speed/brightness have been applied so the new state
            # is what shows when the strip turns on.
            if was_off:
                await self._hass.async_add_executor_job(self._toggle_sync, True)
                self.async_write_ha_state()
            else:
                # Already on, just ensure state matches desired on-state
                self._state.is_on = True
                self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn off the light (async)."""
        if self._hass is None:
            return
        
        async with self._command_lock:
            # Check current state (use desired state if available, otherwise sync)
            if self._desired_state is None:
                await self._sync_state()
            is_on = self._desired_state if self._desired_state is not None else self._state.is_on
            
            # Set desired state as source of truth
            self._desired_state = False
            
            # Turn off if it's on - use toggle with desired state
            if is_on:
                await self._hass.async_add_executor_job(self._toggle_sync, False)
                self.async_write_ha_state()
            else:
                # Already off, but update state to reflect desired state
                self._state.is_on = False
                self.async_write_ha_state()

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
                    # Update state from device
                    self._state.update_from_sync(bytearray(response))
                    
                    # Use desired values as source of truth (don't let sync override)
                    if self._desired_state is not None:
                        self._state.is_on = self._desired_state
                    
                    if self._desired_brightness is not None:
                        self._state.brightness = self._desired_brightness
                    
                    if self._desired_color is not None:
                        self._state.color = self._desired_color
                    
                    if self._desired_effect is not None:
                        # Update mode from desired effect
                        both = {**MONO_EFFECTS, **PRESET_EFFECTS}
                        if self._desired_effect in both:
                            self._state.mode = both[self._desired_effect]
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
        both = {**MONO_EFFECTS, **PRESET_EFFECTS}
        current_effect = next((k for k, v in both.items() if v == self._state.mode), None)
        return {
            "brightness": self._state.brightness,
            "effect": current_effect,
            "speed": self._state.speed,
            "default_effect": self._default_effect,
            "current_rgb": f"rgb({r}, {g}, {b})",
            "white_value": self._state.white
        }

