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
| `fan_protocol.py` | The protocol: packets, reading, writing, `read_state()` and the actions below |
| `fan_snapshot.py` | Print everything the fan will tell you. Changes nothing |
| `fan_button_press.py` | **Short press on a wall button:** start the fan, or stop it |
| `fan_button_hold.py` | **Long press:** pause all ventilation, and put it back |
| `fan_boost_on.py` / `fan_boost_off.py` | Start and stop a boost |
| `fan_off.py` | Switch the fan off |
| `fan_24h.py` | Switch 24 hour mode on or off |
| `ha_fan_state.py` | The whole state as JSON, for a Home Assistant sensor or anything that parses |
| `ha_fan_command.py` | One named command per run, for a Home Assistant switch or script |
| `PROTOCOL.md` | **What the fan actually does**, measured rather than quoted |
| `PACKETS.md` | The wire format byte by byte, and what each byte in the packets found online really does |
| `states.svg` | The same as a diagram |

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

state = fan.read_state()          # None when the fan does not answer
print(fan.describe(state))        # "24 hour mode", "boost", "sensor driven", "idle", "off"

fan.boost(True)                   # start a boost
fan.boost(False)                  # end it, leaving the ventilation running
fan.mode_24h(True)                # constant background ventilation
fan.power(False)                  # switch the fan off
fan.humidity_sensor(0)            # 0 off, 1 auto, 2 manual
fan.temperature_sensor(False)
fan.humidity_threshold(60)        # percent, 40 to 80
fan.temperature_threshold(24)     # degrees, 18 to 36
```

`read_state()` returns `None` rather than zeros when the fan is silent. That distinction matters: a dropped packet must not look like a fan that is switched off, or your automation will start the fan when it meant to leave it alone.

## Home Assistant and a wall button

Two shell commands in `configuration.yaml`:

```yaml
shell_command:
  fan_press:  python /config/scripts/duka-smartfan/fan_button_press.py
  fan_quiet:  python /config/scripts/duka-smartfan/fan_button_hold.py quiet
  fan_resume: python /config/scripts/duka-smartfan/fan_button_hold.py resume
```

Put `fan_protocol.py`, both button scripts and your `config.json` in that folder.

**A Hue button sends several events for one press.** It is a stateless device: pressing it emits `initial_press` and then `short_release`, and holding it emits `initial_press`, a stream of `repeat`, and finally `long_release`. An automation that triggers on any event from the button therefore runs twice per press, and the second run undoes the first. Trigger on the release only:

```yaml
automation:
  - alias: Fan button - short press
    mode: single
    triggers:
      - trigger: event
        event_type: hue_event
        event_data:
          id: YOUR_BUTTON_ID        # see below
          type: short_release
    actions:
      - action: shell_command.fan_press

  - alias: Fan button - long press
    mode: single
    triggers:
      - trigger: event
        event_type: hue_event
        event_data:
          id: YOUR_BUTTON_ID
          type: long_release
    actions:
      - action: shell_command.fan_quiet
      - delay: "03:00:00"
        # The script cannot wake itself up. Home Assistant holds the timer.
      - action: shell_command.fan_resume
```

### Making the fan a real entity

Shell commands are enough for a button, but they are not entities: they do not show up in Assist, in dashboards or over Home Assistant's MCP server. For that, read the state as JSON and turn it into entities:

```yaml
command_line:
  - sensor:
      name: Smartfan
      command: "python /config/scripts/duka-smartfan/ha_fan_state.py"
      value_template: "{{ value_json.state }}"
      json_attributes: [state_text, power, mode_24h, rpm, countdown_seconds,
                        boost, sensor_demand, humidity, temperature, humidity_sensor]
      scan_interval: 30

shell_command:
  fan_command: "python /config/scripts/duka-smartfan/ha_fan_command.py {{ command }}"
```

One sensor, one reading, and template entities built on its attributes. Do not give each value its own command line sensor: every parameter is a separate round trip to the fan, because this unit does not answer a request for several at once.

The sensor's state is one of `off`, `idle`, `mode_24h`, `boost`, `sensor` or `no_answer`. Build templates on those keys rather than on `state_text`, which is wording meant for people to read.

To find your button's id and the exact event names: Developer tools, Events, listen to `hue_event`, then press the button short and then long. Use what you actually see — the names differ between the Hue bridge, ZHA and Zigbee2MQTT.

`mode: single` matters on the long press automation: it keeps a second long press from starting a second three hour timer. The scripts also ignore a second run within five seconds, so a duplicate event cannot undo the press that came before it.

## Four things worth knowing## Four things worth knowing before you build on this

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
