from enum import IntEnum

class CommandFlag(IntEnum):
  """
  All messages to the device must be wrapped in a start and end flag

  Mostly for internal use, prefer to use the functions on WifiLedShopLight instead.
  """
  START = 0x38
  END = 0x83

class Command(IntEnum):
  """
  Commands that can be sent to the device.
  
  Mostly for internal use, prefer to use the functions on WifiLedShopLight instead.

  To be used with WifiLedShopLight.send_command()
  """
  TOGGLE = 0xAA
  SET_COLOR = 0x22
  SET_BRIGHTNESS = 0x2A
  SET_SPEED = 0x03
  SET_PRESET = 0x2C
  SET_CUSTOM = 0x02
  SET_LIGHTS_PER_SEGMENT = 0x2D
  SET_SEGMENT_COUNT = 0x2E
  SYNC = 0x10

class StatePosition(IntEnum):
  """
  State is returned from the device as a byte array. 
  
  This provides the position of each piece of useful data within the state bytearray.
  """
  IS_ON = 1
  COLOR_R = 10
  COLOR_G = 11
  COLOR_B = 12
  MODE = 2
  SPEED = 3
  BRIGHTNESS = 4

class MonoEffect(IntEnum):
  """
  Preset effects that are for a single, user customizable color

  To be used with WifiLedShopLight.set_preset()
  """
  SOLID = 211,
  BREATHING = 206,
  METEOR = 205,
  FLOW = 208,
  WAVE = 209,
  FLASH = 210,
  STACK = 207,
  CATCHUP = 212,

class CustomEffect(IntEnum):
  """
  Sets the brightness of the light (0 to 255)

  To be used with WifiLedShopLight.set_custom()
  """
  CUSTOM_1 = 1,
  CUSTOM_2 = 2,
  CUSTOM_3 = 3,
  CUSTOM_4 = 4,
  CUSTOM_5 = 5,
  CUSTOM_6 = 6,
  CUSTOM_7 = 7,
  CUSTOM_8 = 8,
  CUSTOM_9 = 9,
  CUSTOM_10 = 10,
  CUSTOM_11 = 11,
  CUSTOM_12 = 12,
