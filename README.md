# SP108E WS2815 LED Controller Integration for Home Assistant

This is a custom Home Assistant integration for controlling SP108E-based LED strip controllers like the [ALITOVE SP108E](https://www.amazon.com/gp/product/B07DDB6JHJ/ref=ppx_yo_dt_b_asin_title_o03_s01?ie=UTF8&psc=1) over Wi-Fi.

Tested with:

- ✅ SP108E controller in STA mode
- ✅ BTF-LIGHTING WS2815 (Upgraded WS2812B) LED strip: [Amazon link](https://www.amazon.com/gp/product/B07LG6J39V)

---

## ✨ Features

- On/Off
- Brightness control
- RGB + HS color support
- Mono-color effects (e.g. solid, breathing, wave, etc.)
- 100+ preset effects (color chase, fire, rainbow, etc.)
- Default effect and speed configuration via the UI
- Supports multiple controllers
- **Automatic device discovery and reconnection** (v0.6.0+)
- **Real-time availability tracking** (v0.6.0+)

---

## 🆕 What's New in v0.6.0

### Automatic Device Detection & Reconnection

The integration now automatically detects when your SP108E device comes back online:

- **No more manual restarts**: When you power on a previously offline device, it will automatically become available in Home Assistant within 30 seconds
- **Smart polling**: The integration polls your device every 30 seconds to check availability
- **Real-time status**: Devices show as "Available" or "Unavailable" based on actual connectivity
- **Improved error handling**: Better logging and error recovery for network issues

This solves the common issue where devices wouldn't appear until Home Assistant was restarted.

---

## 🧠 Built With

- Based on [example_light](https://github.com/home-assistant/example-custom-config/tree/master/custom_components/example_light)
- LED command logic powered by [kylezimmerman/pyledshop](https://github.com/kylezimmerman/pyledshop)
- Modern Home Assistant config flow (`config_flow` and `options_flow`) included

---

## 🛠 Installation

### Manual

1. Copy or clone this repository into:

<config_dir>/custom_components/sp108e_ws2815/

2. Restart Home Assistant

3. Go to **Settings → Devices & Services → + Add Integration** → Search for **SP108E WS2815**

### HACS (Recommended)

1. In HACS, go to **Integrations → + Explore & Add Repositories**
2. Click **"⋮" → Custom repositories**
3. Add your GitHub repo URL
4. Select **Category: Integration**
5. Install and restart Home Assistant

---

## ⚙️ Configuration

This integration supports setting the following:

- `host`: IP address of the controller (required)
- `name`: Friendly name (required)
- `default effect`: Any of the mono or preset effects
- `default speed`: 0–255

Once configured, you can change the default effect and speed later via:

**Settings → Devices & Services → Your Controller → ⋮ → Configure**

---

## 🔄 Upgrading

If upgrading from a version using `configuration.yaml`, remove the old config first. This integration now supports UI-based setup only.

---

## 🙏 Thanks

Built on the shoulders of:

- [@kylezimmerman](https://github.com/kylezimmerman) for `pyledshop`
- The Home Assistant community and custom integration ecosystem

---

## 💬 Feedback

Feel free to open an issue or pull request if you find bugs or have ideas!
