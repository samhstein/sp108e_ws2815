# sp108e_ws2815

This integration is for the ALITOVE WS2812B WS2811 WS2801 LED WiFi Controller
https://www.amazon.com/gp/product/B07DDB6JHJ/ref=ppx_yo_dt_b_asin_title_o03_s01?ie=UTF8&psc=1

tested with two controllers so far using a BTF-LIGHTING WS2815 (Upgraded WS2812B) 16.4ft 300
Pixels Magic Dream Color Individually Addressable RGB LED Flexible Strip Light 5050 SMD Dual
Signal IP30 Non-Waterproof DC12V Black PCB
https://www.amazon.com/gp/product/B07LG6J39V/ref=ppx_yo_dt_b_asin_title_o03_s00?ie=UTF8&psc=1

on / off, color and brightness are supported, mono color effects are good,
presets with colors work but ymmv with rgb wiring...

built using https://github.com/home-assistant/example-custom-config/tree/master/custom_components/example_light
and https://github.com/kylezimmerman/pyledshop as a base.


### Installation

Copy or clone this into `<config_dir>/custom_components/sp108e_ws2815/`.

Add the following entry in your `configuration.yaml`:

```yaml
# led strip
light:
  - platform: sp108e_ws2815
    host: ip address, ie: 10.0.1.124
    name: 'your name here'
```
