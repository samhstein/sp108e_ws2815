def clamp(value, min=0, max=255):
  """
  Clamps a value to be within the specified range

  Since led shop uses bytes for most data, the defaults are 0-255
  """
  if value > max:
    return max
  elif value < min:
    return min
  else:
    return value
