from .constants import (StatePosition, MonoEffect)

class WifiLedShopLightState:
  def __init__(self):
    self.is_on = False
    self.color = (255, 255, 255)
    self.brightness = 255
    self.mode = MonoEffect.SOLID
    self.speed = 255

  def __repr__(self):
      return f"""
        is_on: {self.is_on}
        color: {self.color}
        brightness: {self.brightness}
        mode: {self.mode}
        speed: {self.speed}
      """

  def update_from_sync(self, sync_data):
    self.is_on = sync_data[StatePosition.IS_ON] == 1
    self.color = (
      sync_data[StatePosition.COLOR_R],
      sync_data[StatePosition.COLOR_G],
      sync_data[StatePosition.COLOR_B]
    )
    self.mode = sync_data[StatePosition.MODE]
    self.speed = sync_data[StatePosition.SPEED]
    self.brightness = sync_data[StatePosition.BRIGHTNESS]
