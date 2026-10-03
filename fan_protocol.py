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
  0x06  R    boost countdown         seconds left, 3 bytes, counts down by 1/s
  0x07  R    boost running           0 = no, 1 = yes
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
  0x02 0x05                        answer with a value, meaning unknown
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

_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
with open(_config_path) as _f:
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


def describe(state: dict | None) -> str:
    """
    Name the state the fan is in. See PROTOCOL.md.

    Note that the fan starts itself: the humidity sensor, and the
    temperature sensor if you enable it, run the fan without setting the
    boost countdown or the boost flag. Never recognise boost by speed
    alone - a sensor can drive the fan at the same 1440 rpm.
    """
    if state is None:
        return "no answer"
    if not state["power"]:
        return "off"
    if state["countdown"] > 0 or state["boost"]:
        return "boost"
    if state["rpm"] == 0:
        return "idle (powered, not spinning)"
    if state.get("sensor_demand") or not state["mode_24h"]:
        return "sensor driven"
    return "24 hour mode"
