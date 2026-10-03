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

Boost lasted **15 minutes** on this unit, every time it was measured. The duration is set in the app under Settings - Timers, not over the protocol as far as we can tell.

⛔ Do not put `0x14` in a boost packet. Scripts in circulation send `14=15` as a "boost duration". `0x14` is the **humidity threshold in percent**, and it accepts 40 to 80. A value of 15 is out of range and quietly ignored, which is why nobody noticed - but a boost packet carrying `14=60` would change the owner's humidity setting on every single press.

**Boost is switched with `0x05`, and only with `0x05`.** Writing `05=1` starts it, as long as power is already on; writing `05=0` ends it and the fan drops straight back to 24 hour mode without the ventilation stopping. Writing 0 to the boost status `0x07`, to the countdown `0x06` or to `0x14` does nothing at all — those are values the unit owns. Cutting power with `01=0` also ends a boost and clears the countdown, but it stops the ventilation with it.

`PACKETS.md` has the whole packet byte by byte, including what each byte of the boost packet found in older scripts actually does.

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

The sensor switches are `0x0F` for humidity and `0x11` for temperature, both verified by flipping them in the app and reading the unit. `0x16` holds the temperature threshold and `0x14` the humidity threshold, both verified by changing them and reading back.

The humidity sensor has two modes. In **auto** the unit decides for itself when to ventilate - the manual calls it intelligent humidity control - and `0x0F` reads 1. In **manual** you set a threshold between 40 and 80 percent, `0x0F` reads 2 and `0x08` reads 1.

**The afterrun is shorter than the manual suggests.** With the temperature sensor on and the room above its threshold, raising the threshold above the room temperature ended the demand, and the fan dropped from 1440 to 930 rpm within 30 seconds. Switching the sensor off entirely dropped it within 20 seconds. The manual mentions an afterrun of 2 to 30 minutes, set in the app under Timers, but nothing like that was observed on the temperature path.

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
| `0x05` | read/write | Boost switch. 1 starts a boost, 0 ends it. Power must be on first |
| `0x07` | read | Boost running, 0 or 1. Status only, writing it does nothing |
| `0x2E` | read | Humidity in percent |
| `0x31` | read | Temperature in degrees Celsius |
| `0x0F` | read/write | Humidity sensor: 0 off, 1 on in auto mode, 2 on in manual mode |
| `0x11` | read/write | Temperature sensor on/off |
| `0x0A` | read | A sensor is asking for ventilation right now, 0 or 1. Seen with the temperature sensor |
| `0x16` | read/write | Temperature threshold in degrees. The manual allows 18 to 36. Verified by writing it and watching the sensor react |
| `0x14` | read/write | Humidity threshold in percent, 40 to 80. Only used when the humidity sensor is in manual mode. Values outside the range are ignored |
| `0x08` | read | 1 while the humidity sensor is in manual mode |
| `0x02` | read | Answers with a value, meaning unknown |
| `0x17` `0x18` `0x1A` `0x1B` `0x23` | read | Settings, meaning unknown |
| `0x1F` `0x20` `0x21` | read | 3-byte counters, probably run time and filter time |

One practical detail: the unit does not answer a request that asks for many parameters at once. Read them one at a time.

## What the manufacturer's manual adds

The Wi-Fi model's manual (dukaventilation.dk/smartfan-wi-fi-manual) names the unit's own programs, and they line up with what we measured:

| The manual's name | What it says | What we measured |
|---|---|---|
| Standby | Out of operation. Starts on 24 hour mode, on a signal from the temperature or humidity sensor, or on the external switch | Power on with nothing running, 0 rpm |
| 24 hour mode | Low speed, constant background ventilation. If a sensor or the external switch activates it, the fan switches to the Silent or Max program | 930 rpm |
| Silent | Starts on the LT and LI terminals. Speed set in the app | Not measured - this unit is driven over wifi |
| Max | Activated by the temperature or humidity sensor, or by Boost Mode | 1440 rpm, and the reason boost and sensor-driven running look identical |

So "boost" and "a sensor wants ventilation" are the same program, Max, reached two different ways. That is the root of the trap: they cannot differ in speed because they are the same thing.

The manual also lists three nominal speeds for the fan (24 hour, Silent, Max) and says the Silent and Max speeds are adjustable in the app, so the rpm figures above are this unit's settings and not fixed values.

Two features we have not explored: interval ventilation, which runs the fan every 12 hours if it has not been active for 24, and delayed start. Both can start the fan on their own, like the sensors.

## Working this out on your own unit

If your fan is a different model, none of the numbers above are safe to trust. The method is, and it needs nothing but the vendor app and a way to read the unit.

**Read the whole range first.** Ask for every parameter from `0x01` upward, one at a time, and write down which ones answer with a value and which answer `0xFD`. That alone tells you which published table, if any, describes your unit. Ours answered on numbers no table mentions and refused several that every table lists.

**Use the app as the oracle.** The vendor app knows what each setting means; the protocol does not. So change exactly one thing in the app, read the unit again, and see which number moved. That is how `0x03` turned out to be 24 hour mode, `0x0F` the humidity sensor, and `0x14` the humidity threshold — the last one by dragging a slider from 40 to 60 percent and watching the parameter follow.

**Prove the app and your reads see the same unit.** Compare live values that change on their own: humidity, temperature, speed, a running countdown. If those match to the second, the mapping you build is about the fan in front of you and not about a cached screen.

**To learn what a packet does, take it apart.** Send each pair of bytes on its own from a known state and read the unit before and after. Then send combinations. A packet that works tells you nothing about which of its bytes did the work.

**Log the unit over time.** Some of what it does, it does by itself. A reading every minute catches a sensor starting the fan, and tells you what the fan falls back to afterwards.

## Three conclusions that were wrong, and why

These were our own mistakes during this work. They are here because the reasoning that produced them looks sound while you are making it.

**"Boost can only be stopped by cutting power."** Writing 0 to the boost status, to the countdown, to `0x14` and a speed change were all tried mid-boost, and the countdown kept running through all four. Cutting power worked. Four negatives and one positive felt like a proof. It was not: `0x05` had never been tried, and `0x05` is the boost switch. A set of negative results is not evidence about the parameter you did not test.

**"`0x14` cannot be written."** Writing 15 and 0 to it changed nothing, so it was filed as read-only and unknown. It is the humidity threshold and it accepts 40 to 80; both test values were out of range and silently dropped. A parameter that refuses your value may be refusing the value, not the write.

**"`0x03` means the fan is running."** It read 1 while the fan ran and 0 while it stood still, twice. Then it read 1 on a fan that was switched off. It is 24 hour mode, which is usually on while the fan runs. Two confirming observations are cheap; the state that separates two hypotheses is the one worth measuring.

The thread running through all three: the unit answers every write with the new state, and it answers just as agreeably when the write did nothing at all.

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
