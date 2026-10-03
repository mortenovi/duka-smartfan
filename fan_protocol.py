"""
UDP protocol for the Duka Smartfan WiFi (Blauberg-based firmware).

Packet layout:
  0xFD 0xFD | TYPE(0x02) | SIZE_ID | ID | SIZE_PWD | PWD | FUNC | DATA | ChksumL ChksumH

FUNC codes (verified against the unit):
  0x01 = read   (DATA = list of parameter numbers)
  0x02 = write  (DATA = parameter/value pairs, no response)
  0x03 = write  (DATA = parameter/value pairs, with response)
  0x06 = response from the unit

Special codes inside a response DATA block:
  0xFD [param]              = parameter not supported by this model
  0xFE [size] [param] [...] = value is [size] bytes, low byte first
  0xFF [high_byte]          = change the high byte for the parameters that follow

PARAMETERS ON THIS UNIT (unit type 0xB9 = 6, firmware 2.1)

Measured on 27 September and 3 October 2026 by reading the whole range
0x01-0xB9 and by changing one setting at a time in the Duka app while
reading the unit directly.

  0x01  R/W  power                   0 = off, 1 = on
  0x03  R/W  24 hour mode            0 = off, 1 = on
  0x04  R    fan speed               rpm, 2 bytes
  0x05  R/W  boost switch            1 starts a boost, 0 ends it. THIS is the
                                     one that controls boost - power must be
                                     on first
  0x06  R    boost countdown         seconds left, 3 bytes, counts down by 1/s
  0x07  R    boost running           0 = no, 1 = yes. Status only: writing it
                                     does nothing
  0x2E  R    humidity                percent
  0x31  R    temperature             degrees Celsius
  0x0F  R/W  humidity sensor         0 = off, 1 = on in auto, 2 = on in manual
  0x11  R/W  temperature sensor      0 = off, 1 = on
  0x0A  R    a sensor is asking for ventilation right now, 0 or 1
             (seen with the temperature sensor; not confirmed for the others)
  0x16  R/W  temperature threshold in degrees, 18-36 per the manual
  0x14  R/W  humidity threshold in percent, 40-80. Only used when the
             humidity sensor is in manual mode. Values outside 40-80 are
             ignored, which is why a boost packet carrying 0x14 looked
             harmless - send a value inside the range and it silently
             changes the owner's humidity setting
  0x08  R    1 while the humidity sensor is in manual mode
  0x02                             answers with a value, meaning unknown
  0x17 0x18 0x1A 0x1B 0x23         settings, meaning unknown
  0x1F 0x20 0x21                   3-byte counters, probably run/filter time

The unit answers 0xFD (not supported) to, among others:
  0x66  boost duration in the Blauberg Freshbox protocol
  0xB7  ventilation direction in the Duka One protocol
  0x25  humidity in the Duka One protocol  (here it is 0x2E)
  0x4A  fan speed in the Duka One protocol (here it is 0x04)

So the parameter tables published for the Blauberg Vento Expert and for
the Duka One S6W do NOT apply to this unit. Only write values that have
been verified on the device. See PROTOCOL.md for the state model.
"""

import json
import os
import socket
import struct

def _find_config() -> str:
    """
    Where config.json is, in the order we look:

      1. the path in DUKA_SMARTFAN_CONFIG, if it is set
      2. config.json in the current directory
      3. config.json beside this file

    The third is the one that works when you clone the repository and run a
    script from it. The first two are for when this module is installed as a
    dependency, where "beside this file" is somewhere inside site-packages.
    """
    tried = []
    from_env = os.environ.get("DUKA_SMARTFAN_CONFIG")
    if from_env:
        tried.append(from_env)
        if os.path.isfile(from_env):
            return from_env
    for candidate in (os.path.abspath("config.json"),
                      os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "config.json")):
        if candidate in tried:
            continue
        tried.append(candidate)
        if os.path.isfile(candidate):
            return candidate
    raise FileNotFoundError(
        "No config.json with the fan's device id, password and ip address. "
        "Looked in: " + ", ".join(tried) + ". Copy config.example.json, fill "
        "it in, and either put it in the working directory or point "
        "DUKA_SMARTFAN_CONFIG at it."
    )


with open(_find_config()) as _f:
    _config = json.load(_f)

DEVICE_ID = _config["device_id"]
PASSWORD = _config["password"]
FAN_IP = _config["fan_ip"]
PORT = 4000
TIMEOUT_SECONDS = 3

# ---------- packet ----------


def build_packet(func: int, data: bytes) -> bytes:
    id_bytes = DEVICE_ID.encode("ascii")
    pwd_bytes = PASSWORD.encode("ascii")
    pkt = bytearray()
    pkt += b"\xFD\xFD\x02"
    pkt += bytes([len(id_bytes)]) + id_bytes
    pkt += bytes([len(pwd_bytes)]) + pwd_bytes
    pkt += bytes([func]) + data
    checksum = sum(pkt[2:]) & 0xFFFF
    pkt += struct.pack("<H", checksum)
    return bytes(pkt)


def send_raw(data: bytes, func: int) -> bytes | None:
    """Send one packet and return the raw answer, or None on timeout."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT_SECONDS)
    try:
        sock.sendto(build_packet(func, data), (FAN_IP, PORT))
        answer, _ = sock.recvfrom(1024)
        return answer
    except socket.timeout:
        return None
    except OSError:
        return None
    finally:
        sock.close()


# ---------- parsing ----------


def parse_data(raw: bytes) -> dict:
    """
    Parse the DATA block of a response.
    Returns {parameter: value}. Unsupported parameters get None.
    """
    result = {}
    i = 0
    high_byte = 0x00

    while i < len(raw):
        cmd = raw[i]

        if cmd == 0xFF:  # change high byte
            i += 1
            if i < len(raw):
                high_byte = raw[i]
            i += 1

        elif cmd == 0xFD:  # parameter not supported
            i += 1
            if i < len(raw):
                result[(high_byte << 8) | raw[i]] = None
            i += 1

        elif cmd == 0xFE:  # multi-byte value
            i += 1
            if i >= len(raw):
                break
            size = raw[i]
            i += 1
            if i >= len(raw):
                break
            param = (high_byte << 8) | raw[i]
            i += 1
            value = 0
            for j in range(size):
                if i + j < len(raw):
                    value |= raw[i + j] << (8 * j)
            result[param] = value
            i += size

        elif cmd == 0xFC:  # change FUNC, skip the next byte
            i += 2

        else:  # plain one-byte parameter and value
            param = (high_byte << 8) | cmd
            i += 1
            if i < len(raw):
                result[param] = raw[i]
            i += 1

    return result


def data_block(answer: bytes) -> bytes:
    """Cut the DATA block out of a full response packet."""
    if not answer or len(answer) < 24:
        return b""
    # FD FD | TYPE(1) | SIZE_ID(1) | ID | SIZE_PWD(1) | PWD | FUNC(1)
    id_size = answer[3]
    pwd_size = answer[4 + id_size]
    start = 4 + id_size + 1 + pwd_size + 1
    return answer[start:-2]  # drop the two checksum bytes


# ---------- public api ----------


def read(*params) -> dict:
    """
    Read one or more parameters: read(0x01, 0x04) -> {1: 1, 4: 930}.

    Returns an empty dict when the fan does not answer. Use read_state()
    when the difference between "no answer" and "switched off" matters.
    """
    answer = send_raw(bytes(params), func=0x01)
    if not answer:
        return {}
    return parse_data(data_block(answer))


def write(param: int, value: int) -> dict:
    """Write one single-byte parameter and return the parsed answer."""
    answer = send_raw(bytes([param, value]), func=0x03)
    if not answer:
        return {}
    return parse_data(data_block(answer))


def read_state() -> dict | None:
    """
    Read the parameters that describe what the fan is doing.

    Returns None when the fan does not answer at all, so a network hiccup
    is never mistaken for a fan that is switched off.

    Note: the unit does not answer a request that asks for many parameters
    at once, so they are read one at a time.
    """
    out = {}
    for param in (0x01, 0x03, 0x04, 0x06, 0x07, 0x0A):
        answer = send_raw(bytes([param]), func=0x01)
        if not answer:
            return None
        out.update(parse_data(data_block(answer)))
    return {
        "power": out.get(0x01, 0),
        "mode_24h": out.get(0x03, 0),
        "rpm": out.get(0x04) or 0,
        "countdown": out.get(0x06) or 0,
        "boost": out.get(0x07, 0),
        "sensor_demand": out.get(0x0A, 0),
    }


# Stable keys for the states, and the words for a person. Build on the keys:
# the wording is free to improve, the keys are not.
STATE_TEXT = {
    "no_answer": "no answer",
    "off": "off",
    "idle": "idle (powered, not spinning)",
    "mode_24h": "24 hour mode",
    "boost": "boost",
    "sensor": "sensor driven",
}


def state_key(state: dict | None) -> str:
    """
    Which state the fan is in, as a key that will not change. See PROTOCOL.md.

    Note that the fan starts itself: the humidity sensor, and the temperature
    sensor if you enable it, run the fan without setting the boost countdown
    or the boost flag. Never recognise boost by speed alone - a sensor drives
    the fan at the same speed a boost does.
    """
    if state is None:
        return "no_answer"
    if not state["power"]:
        return "off"
    if state["countdown"] > 0 or state["boost"]:
        return "boost"
    if state["rpm"] == 0:
        return "idle"
    if state.get("sensor_demand") or not state["mode_24h"]:
        return "sensor"
    return "mode_24h"


def describe(state: dict | None) -> str:
    """The state in words, for a person to read. Code should use state_key()."""
    return STATE_TEXT[state_key(state)]

# ---------- actions ----------
#
# Everything the fan can be told to do, in the words of what it does rather
# than the bytes it takes. The bytes are in PACKETS.md.


def power(on: bool) -> bool:
    """Switch the fan on or off. On its own this does not make it spin."""
    return bool(write(0x01, 1 if on else 0))


def boost(on: bool) -> bool:
    """
    Start or stop a boost.

    Starting sends power on and the boost switch in one packet, because the
    boost switch does nothing on a fan without power. Stopping writes the
    boost switch only, so the ventilation underneath keeps running.
    """
    if on:
        return bool(send_raw(bytes([0x01, 0x01, 0x05, 0x01]), func=0x03))
    return bool(send_raw(bytes([0x05, 0x00]), func=0x03))


def mode_24h(on: bool) -> bool:
    """
    Switch 24 hour mode, the constant low-speed background ventilation.

    Switching it on also switches power on, because the setting alone does
    nothing. Switching it off leaves power alone: the rotor stops within ten
    seconds and the fan rests, ready for the next command or sensor.
    """
    ok = bool(write(0x03, 1 if on else 0))
    if on:
        ok = bool(write(0x01, 1)) and ok
    return ok


def humidity_sensor(mode: int) -> bool:
    """0 switches the humidity sensor off, 1 is auto, 2 is manual."""
    if mode not in (0, 1, 2):
        raise ValueError("humidity_sensor takes 0, 1 or 2")
    return bool(write(0x0F, mode))


def temperature_sensor(on: bool) -> bool:
    """Switch the temperature sensor on or off."""
    return bool(write(0x11, 1 if on else 0))


def humidity_threshold(percent: int) -> bool:
    """
    Set the humidity threshold used in manual mode. 40 to 80 percent.

    The fan ignores anything outside that range without saying so.
    """
    if not 40 <= percent <= 80:
        raise ValueError("the fan only accepts 40 to 80 percent")
    return bool(write(0x14, percent))


def temperature_threshold(degrees: int) -> bool:
    """Set the temperature threshold. The manual allows 18 to 36 degrees."""
    if not 18 <= degrees <= 36:
        raise ValueError("the fan only accepts 18 to 36 degrees")
    return bool(write(0x16, degrees))
