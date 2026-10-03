# Duka Smartfan WiFi — local control from Python

Control a **Duka Smartfan WiFi** ventilation fan over your own network. No cloud, no app, no account. Works with Home Assistant, a smart button, a cron job, or anything else that can run a Python script.

Standard library only, no dependencies.

```bash
python fan_snapshot.py
```

```
=== Duka Smartfan 2026-10-03 11:15:07 ===
  State: 24 hour mode
  0x01  power (0/1)            1
  0x03  24 hour mode (0/1)     1
  0x04  fan speed (rpm)        930
  0x06  boost countdown (s)    0
  0x07  boost running (0/1)    0
  0x2E  humidity (%)           74
  0x31  temperature (C)        26
```

## What is here

| File | What it does |
|------|--------------|
| `fan_protocol.py` | The protocol: packets, reading, writing, and `read_state()` |
| `fan_snapshot.py` | Print everything the fan will tell you. Changes nothing |
| `fan_boost_toggle.py` | One button: boost on, boost off. Written for a smart button |
| `fan_boost_on.py` | Start boost |
| `fan_off.py` | Switch the fan off, which also ends a running boost |
| `fan_24h.py` | Switch 24 hour mode on or off |
| `PROTOCOL.md` | **What the fan actually does**, measured rather than quoted |
| `PACKETS.md` | The wire format byte by byte, and what each byte in the packets found online really does |
| `states.svg` | The same thing as a diagram |

## Getting started

1. Clone this repository.
2. Copy `config.example.json` to `config.json` and fill in your own values:

```json
{
  "device_id": "YOUR_DEVICE_ID",
  "password": "YOUR_PASSWORD",
  "fan_ip": "192.168.x.x"
}
```

- **Device id**: shown in the Duka or Blauberg app under device settings, typically 16 characters.
- **Password**: the one set during setup. The factory default is often `11111111`.
- **Ip address**: from your router's device list. Give the fan a fixed address, or your scripts will stop working the day it changes.

`config.json` is in `.gitignore` and is the only file that holds your credentials.

3. Run `python fan_snapshot.py`. If it prints the fan's state, you are done.

## Using it from Python

```python
import fan_protocol as fan

state = fan.read_state()        # None when the fan does not answer
print(fan.describe(state))      # "24 hour mode", "boost", "idle", "off"

fan.write(0x03, 1)              # 24 hour mode on
fan.write(0x01, 1)              # power on - both are needed
```

`read_state()` returns `None` rather than zeros when the fan is silent. That distinction matters: a dropped packet must not look like a fan that is switched off, or your automation will start the fan when it meant to leave it alone.

## Home Assistant

Add a shell command in `configuration.yaml`:

```yaml
shell_command:
  fan_toggle: python /config/scripts/duka-smartfan/fan_boost_toggle.py
```

and call it from an automation:

```yaml
action:
  - service: shell_command.fan_toggle
```

Put `fan_protocol.py`, `fan_boost_toggle.py` and your `config.json` in the same folder on the Home Assistant host.

If a smart button triggers the automation, make the automation listen to **one** event from the button and set `mode: single`. Many buttons send both a press and a release, and that is two runs of the script. `fan_boost_toggle.py` ignores a second run within five seconds for exactly this reason, but it is better not to send it twice in the first place.

## Four things worth knowing before you build on this

**The fan spins when power is on and either 24 hour mode is on or a boost is running.** A toggle that asks "is the fan spinning" will switch the fan off when 24 hour mode is on, instead of giving you boost. Decide from the boost countdown instead.

**Boost is switched with one parameter, `0x05`.** Writing `05=1` starts it when power is on, and `05=0` ends it without stopping the ventilation. Writing to the boost status or the countdown does nothing — the unit owns those. Boost lasts 15 minutes, and the duration is set in the app, not over the protocol.

⛔ If you copied a boost packet from somewhere, check it for `0x14`. Scripts in circulation send `14=15` believing it sets the boost duration. `0x14` is the humidity threshold in percent and accepts 40 to 80, so 15 is ignored - but a value inside the range would change the owner's humidity setting on every press.

**The fan starts itself.** The humidity sensor is on by default and runs the fan without anyone pressing anything, and it does so without setting the boost countdown or the boost flag. So never recognise boost by speed alone, and never assume your automation is the only thing touching the fan. `read_state()` reports `sensor_demand` for this.

**The published parameter tables do not fit this unit.** Humidity is `0x2E`, not `0x25`. Speed is `0x04`, not `0x4A`. `0x66` and `0xB7` do not exist here, and `0x03`, which is 24 hour mode, is not in any table. `PROTOCOL.md` has the measurements.

## How it works

The fan speaks a binary protocol over UDP on port 4000:

```
[0xFD 0xFD] [type] [id_len] [device_id] [pwd_len] [password] [func] [data] [checksum]
```

Function `0x01` reads parameters and `0x03` writes them with a response. The format comes from Blauberg's smart home connection guide and is the same across their units. The parameter numbers are not.

## Tested on

Duka Smartfan WiFi, unit type 6, firmware 2.1, with Home Assistant OS and a Philips Hue smart button.

If you have another model or another firmware, read the whole parameter range first and check what your unit answers before trusting the table in `PROTOCOL.md`. Issues and pull requests with other units' findings are welcome.

## License

MIT
