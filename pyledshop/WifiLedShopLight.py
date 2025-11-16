import socket
import logging
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
from time import sleep

_LOGGER = logging.getLogger(__name__)


class WifiLedShopLight(LightEntity):
    """A Wifi LED Shop Light."""

    def __init__(self, ip, name, config, port=8189, timeout=1, retries=5):
        self._ip = ip
        self._default_effect = config.get("effect", "Solid (custom color)")
        self._default_speed = config.get("speed", 255)
        self._port = port
        self._timeout = timeout
        self._retries = retries
        self._state = WifiLedShopLightState()
        self._sock = None

        self._attr_name = name
        self._attr_unique_id = self.send_command(Command.GET_ID, []).decode("utf-8")
        self._attr_supported_color_modes = {ColorMode.RGB}
        self._attr_color_mode = ColorMode.RGB
        self._attr_supported_features = LightEntityFeature.EFFECT

        self.update()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._sock.close()

    def set_color(self, r=0, g=0, b=0):
        r, g, b = clamp(r), clamp(g), clamp(b)
        self._state.color = (r, g, b)
        self.send_command(Command.SET_COLOR, [r, g, b])

    def set_brightness(self, brightness=0):
        brightness = clamp(brightness)
        self._state.brightness = brightness
        self.send_command(Command.SET_BRIGHTNESS, [brightness])

    def set_white(self, white=0):
        white = clamp(white)
        self._state.white = white
        self.send_command(Command.SET_WHITE, [white])

    def set_speed(self, speed=0):
        speed = clamp(speed)
        self._state.speed = speed
        self.send_command(Command.SET_SPEED, [speed])

    def set_effect(self, effect):
        both = {**MONO_EFFECTS, **PRESET_EFFECTS}
        if effect not in both:
            return
        preset = clamp(both[effect])
        self._state.mode = preset
        self.send_command(Command.SET_PRESET, [preset])

    def set_custom(self, custom):
        custom = clamp(custom, 1, 12)
        self._state.mode = custom
        self.send_command(Command.SET_CUSTOM, [custom])

    def toggle(self):
        initial_state = self._state.is_on
        self.send_command(Command.TOGGLE, [])
        self.update()
        while initial_state == self._state.is_on:
            sleep(0.5)
            self.toggle()

    def turn_on(self, **kwargs):
        # Apply defaults if not overridden
        if ATTR_EFFECT not in kwargs:
            self.set_effect(self._default_effect)
        if "speed" not in kwargs:
            self.set_speed(self._default_speed)

        for k, v in kwargs.items():
            if k == ATTR_BRIGHTNESS:
                self.set_brightness(v)
            elif k == "rgb_color":
                self.set_color(*v)
            elif k == ATTR_HS_COLOR:
                r, g, b = color_util.color_hs_to_RGB(*v)
                self.set_color(r, g, b)
            elif k == ATTR_WHITE:
                self.set_white(v)
            elif k == ATTR_EFFECT:
                self.set_effect(v)
            elif k == "speed":
                self.set_speed(v)
            else:
                print(f"unknown control key: {k}")

        if not self._state.is_on:
            self.toggle()



    def turn_off(self, **kwargs):
        if self._state.is_on:
            self.toggle()

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
        while True:
            try:
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._sock.settimeout(self._timeout)
                self._sock.connect((self._ip, self._port))
                self._sock.sendall(bytes(raw_data))
                if command in [Command.GET_ID, Command.SYNC]:
                    result = self._sock.recv(1024)
                self._sock.shutdown(socket.SHUT_RDWR)
                self._sock.close()
                self._sock = None
                return result
            except (socket.timeout, BrokenPipeError, ConnectionRefusedError, OSError) as e:
                if attempts < self._retries:
                    attempts += 1
                    if self._sock:
                        try:
                            self._sock.close()
                        except:
                            pass
                        self._sock = None
                else:
                    if self._sock:
                        try:
                            self._sock.close()
                        except:
                            pass
                        self._sock = None
                    raise

    def update(self):
        """Update device state by syncing with the device."""
        try:
            response = self.send_command(Command.SYNC, [])
            if response:
                self._state.update_from_sync(bytearray(response))
                _LOGGER.debug("Successfully updated device state for %s", self._ip)
            else:
                _LOGGER.warning("Empty response from device %s", self._ip)
        except Exception as e:
            _LOGGER.error("Failed to update device %s: %s", self._ip, str(e))
            raise

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
