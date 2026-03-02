# Duka Smartfan WiFi — Python Control Scripts

Control your **Duka Smartfan WiFi** ventilation fan from a local network — no app required.

Works with Home Assistant (or any system that can run a Python script).

---

## What it does

Sends UDP commands directly to the fan on your local network, bypassing the official Duka app entirely.

### `fan_boost_toggle.py` — the main script

A single-button toggle designed for a Hue button or Home Assistant automation:

- Fan is **running** → turns it **off**
- Fan is **off** → activates **boost** mode for a configurable number of minutes

### `_fan_proto.py` — protocol library

Low-level UDP protocol implementation. Used by `fan_boost_toggle.py`.

Supports reading and writing all known fan parameters (power, speed, boost, timer, RPM, humidity, temperature).

---

## Requirements

- Python 3.x (no external packages — standard library only)
- Duka Smartfan WiFi on the same local network
- Fan's local IP address (assign a static IP in your router for reliability)
- Device ID and password (see below)

---

## Finding your Device ID and Password

The device ID and password are configured in the Duka/Blauberg app when you first set up the fan.

- **Device ID**: shown in the app under device settings (typically a 16-character string)
- **Password**: the password you set during setup (default is often `11111111`)
- **IP address**: find it in your router's device list, or use a network scanner like `nmap`

---

## Installation

1. Clone or download this repository
2. Copy `config.example.json` to `config.json`
3. Fill in your values:

```json
{
  "device_id": "YOUR_DEVICE_ID",
  "password": "YOUR_PASSWORD",
  "fan_ip": "192.168.x.x"
}
```

> `config.json` is listed in `.gitignore` and will never be committed to Git.

---

## Usage

```bash
python fan_boost_toggle.py
```

Run it once to toggle:
- If the fan is running → it turns off
- If the fan is off → boost activates for `BOOST_MINUTES` (default: 15)

To change boost duration, edit the top of `fan_boost_toggle.py`:

```python
BOOST_MINUTES = 15  # change to any value between 1 and 60
```

---

## Home Assistant integration

Add a shell command to `configuration.yaml`:

```yaml
shell_command:
  fan_toggle: python /config/scripts/duka-smartfan/fan_boost_toggle.py
```

Then call it from an automation or script:

```yaml
action:
  - service: shell_command.fan_toggle
```

> Place all files (`fan_boost_toggle.py`, `_fan_proto.py`, `config.json`) in the same folder on your Home Assistant host.

---

## How it works

The fan communicates over **UDP on port 4000** using a binary protocol documented in the Blauberg Freshbox WiFi Connection Guide.

```
[0xFD 0xFD] [type] [id_len] [device_id] [pwd_len] [password] [func] [data] [checksum]
```

Function codes used:
- `0x01` — read parameters
- `0x03` — write parameters (with response)

The toggle script reads the current power state and RPM before deciding what to do — so it always makes the right call even if the fan state is unknown.

---

## Tested on

- Duka Smartfan WiFi (Blauberg-based firmware)
- Home Assistant OS on Home Assistant Green

If you've tested it on other models or firmware versions, feel free to open an issue or PR.

---

## License

MIT
