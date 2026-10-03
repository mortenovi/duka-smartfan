# What the fan actually does

Everything here was measured on a Duka Smartfan WiFi (unit type 6, firmware 2.1) on 27 September and 3 October 2026. Nothing is taken from a datasheet, because the published parameter tables do not fit this unit.

The method was simple and anyone can repeat it: read the unit directly while changing one thing at a time in the Duka app, and compare. The app's own numbers matched the readings exactly in the same second, which is what makes the mapping below trustworthy.

## The states

The fan is always in exactly one of these. Power, speed and the boost countdown are enough to tell them apart.

| State | Power `0x01` | Speed `0x04` | Countdown `0x06` | What it is |
|-------|------|------|------|------------|
| Off | 0 | 0 | 0 | Nothing running |
| Idle | 1 | 0 | 0 | Powered but with no job to do. This is the unit's normal resting state |
| 24 hour mode | 1 | 930 | 0 | Constant background ventilation at low speed |
| Boost | 1 | 1440 | counts down | Full speed for 15 minutes |
| Sensor driven | 1 | up to 1440 | 0 | A sensor is asking for ventilation. The fan started this itself |
| No answer | — | — | — | Three seconds of silence. Not the same as off |

**The rule behind the table:** the fan spins when power is on **and** either 24 hour mode is on, a boost is running, or a sensor is asking for ventilation. Power on with neither gives you a powered fan standing still.

This matters more than it sounds. A button that decides from "is the fan spinning" will switch the fan off when 24 hour mode is on, instead of giving you boost.

## Boost

Boost lasts **15 minutes** on this unit. Writing 15 to parameter `0x14` does not set that; `0x14` cannot be written at all and stays at 40 whatever you send. The duration is the unit's own.

**Boost can only be stopped by switching power off.** Writing 0 to the boost status `0x07`, to the countdown `0x06`, to `0x14`, or sending a speed change were all tried mid-boost and the countdown simply kept running. `0x01 = 0` stops it instantly and clears the countdown, so a stopped boost can never restart the fan later.

**Where the fan lands when boost ends depends on 24 hour mode:**

- 24 hour mode on: speed drops from 1440 to 930 and the fan keeps running.
- 24 hour mode off: the rotor stops, but **power stays on** — the fan ends up idle, not off. This is also what happens when boost was started from a fan that was completely off.

## The fan starts itself

The unit has its own sensors, and they run the fan without anyone pressing anything. In the Duka app they live under Settings - Sensors: humidity, temperature, motion and external switch, each with its own switch, and humidity has an `Auto` mode described as intelligent humidity control.

On the unit measured here, humidity was on in `Auto` and the rest were off. Two measurements:

- The fan was left switched off at 11:17 and was running at 930 rpm at 11:57 with nobody touching it. Humidity was 76 percent.
- Switching the temperature sensor on while the room was 26 degrees against its 24 degree threshold took the fan to 1440 rpm immediately, with the countdown at zero and the boost flag clear. Parameter `0x0A` went to 1 and back to 0 when the sensor was switched off again, so it looks like "a sensor wants ventilation right now".

**Sensor-driven running looks like boost but is not boost.** Same speed, no countdown, no boost flag. Recognise boost by the countdown `0x06` and the flag `0x07`, never by speed.

Two consequences for anything built on this library: the fan's state can change while your automation is not looking, and a sensor can be the reason the fan is running. Read the state before you act on it, which is what `read_state()` is for.

The sensor switches are `0x0F` for humidity and `0x11` for temperature, both verified by flipping them in the app and reading the unit. The threshold the app showed for temperature, 24 degrees, matches `0x16`. How long the fan keeps running after a sensor is satisfied has not been measured yet.

## 24 hour mode

Parameter `0x03`, and it is a setting, not an action:

- `0x03 = 1` on its own changes nothing visible. The fan stayed still for over a minute. Power has to be on as well.
- `0x03 = 0` stops the rotor within ten seconds, but leaves power on. To switch the fan fully off, write `0x01 = 0` too.
- It can be changed in the middle of a boost without disturbing it. Speed and countdown carried on unchanged.

Because of this, anything that starts boost must leave `0x03` alone. A boost packet that includes `03=1` switches the setting back on every time, and the owner never finds out why their fan keeps ventilating.

## Parameters

| Parameter | Access | Meaning |
|-----------|--------|---------|
| `0x01` | read/write | Power, 0 or 1 |
| `0x03` | read/write | 24 hour mode, 0 or 1 |
| `0x04` | read | Fan speed in rpm, 2 bytes |
| `0x06` | read | Boost countdown in seconds, 3 bytes, counts down by one per second |
| `0x07` | read | Boost running, 0 or 1 |
| `0x2E` | read | Humidity in percent |
| `0x31` | read | Temperature in degrees Celsius |
| `0x0F` | read/write | Humidity sensor on/off |
| `0x11` | read/write | Temperature sensor on/off |
| `0x0A` | read | A sensor is asking for ventilation right now, 0 or 1. Seen with the temperature sensor |
| `0x16` | read/write | Temperature threshold in degrees, probably. The app showed 24 and so does this |
| `0x14` | read | Reads 40, cannot be written, purpose unknown |
| `0x02` `0x05` `0x08` | read | Answer with a value, meaning unknown |
| `0x17` `0x18` `0x1A` `0x1B` `0x23` | read | Settings, meaning unknown |
| `0x1F` `0x20` `0x21` | read | 3-byte counters, probably run time and filter time |

One practical detail: the unit does not answer a request that asks for many parameters at once. Read them one at a time.

## Where the published tables are wrong for this unit

This unit answers `0xFD`, meaning "no such parameter", to several numbers that the vendor documentation defines:

| Parameter | Published meaning | On this unit |
|-----------|-------------------|--------------|
| `0x66` | Boost duration, 0-60 minutes | Not supported |
| `0xB7` | Ventilation direction | Not supported |
| `0x25` | Current humidity | Not supported — humidity is `0x2E` |
| `0x4A` | Fan speed | Not supported — speed is `0x04` |
| `0x14` | Relay sensor activation, 0/1/2 | Reads 40, cannot be written |
| `0x03` | Not defined at all | 24 hour mode |

The packet format and the function codes in the Blauberg smart home guide are correct and this library follows them. It is only the parameter numbers that differ. If you have a different unit, read the whole range yourself before trusting any table, including this one.

Sources for the format: Blauberg's smart home connection guide for the Vento Expert A30/50 W V.2, and the `dukaonesdk` Python package for the Duka One S6W.
