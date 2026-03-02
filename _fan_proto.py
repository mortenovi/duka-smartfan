"""
Duka SmartFan / Blauberg UDP protocol implementation.
Based on Blauberg Freshbox 100 WiFi Connection Guide.

Packet format:
  0xFD 0xFD | TYPE(0x02) | SIZE_ID(0x10) | ID(16) | SIZE_PWD | PWD | FUNC | DATA | ChksumL ChksumH

FUNC codes:
  0x01 = read   (DATA = list of param numbers)
  0x02 = write  (DATA = param, value pairs — no response)
  0x03 = write  (DATA = param, value pairs — with response)
  0x06 = controller response

DATA special commands (in response):
  0xFD [param]             = parameter not supported
  0xFE [size] [param] [...] = parameter value is [size] bytes (little-endian)
  0xFF [high_byte]         = change high byte for subsequent param numbers

Key parameters:
  0x01  R/W  Unit on/off           (0=off, 1=on)
  0x02  R/W  Speed mode            (1-5)
  0x04  R    Fan RPM               (2 bytes, little-endian) — proprietary
  0x06  R    Boost status          (0=off, 1=on) — READ ONLY
  0x07  R/W  Timer on/off          (0=off, 1=on)
  0x09  R/W  Timer minutes         (0-59)
  0x0A  R/W  Timer hours           (0-23)
  0x14  R/W  Boost switch control  (0=off, 1=on)
  0x2E  R    Humidity %            — proprietary
  0x31  R    Temperature C         — proprietary
  0x66  R/W  Boost duration        (0-60 min)
"""

import socket
import struct
import json
import os

_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
with open(_config_path) as _f:
    _config = json.load(_f)

DEVICE_ID = _config['device_id']
PASSWORD   = _config['password']
FAN_IP     = _config['fan_ip']
PORT       = 4000

# ---------- Packet ----------

def build_packet(func, data: bytes) -> bytes:
    id_bytes  = DEVICE_ID.encode('ascii')
    pwd_bytes = PASSWORD.encode('ascii')
    pkt = bytearray()
    pkt += b'\xFD\xFD\x02'
    pkt += bytes([len(id_bytes)]) + id_bytes
    pkt += bytes([len(pwd_bytes)]) + pwd_bytes
    pkt += bytes([func]) + data
    chksum = sum(pkt[2:]) & 0xFFFF
    pkt += struct.pack('<H', chksum)
    return bytes(pkt)

def _send_raw(data: bytes, func: int) -> bytes | None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3)
    pkt = build_packet(func, data)
    sock.sendto(pkt, (FAN_IP, PORT))
    try:
        resp, _ = sock.recvfrom(1024)
        return resp
    except:
        return None
    finally:
        sock.close()

# ---------- Data block parser ----------

def parse_data(raw: bytes) -> dict:
    """
    Parse DATA block from controller response (FUNC=0x06).
    Returns {param_number: value, ...}
    Unsupported params are stored as None.
    """
    result = {}
    i = 0
    high_byte = 0x00

    while i < len(raw):
        cmd = raw[i]

        if cmd == 0xFF:           # change high byte
            i += 1
            if i < len(raw):
                high_byte = raw[i]
            i += 1

        elif cmd == 0xFD:         # param not supported
            i += 1
            if i < len(raw):
                param = (high_byte << 8) | raw[i]
                result[param] = None
            i += 1

        elif cmd == 0xFE:         # multi-byte value follows
            i += 1
            if i >= len(raw): break
            size = raw[i]
            i += 1
            if i >= len(raw): break
            param = (high_byte << 8) | raw[i]
            i += 1
            val = 0
            for j in range(size):
                if i + j < len(raw):
                    val |= (raw[i + j] << (8 * j))
            result[param] = val
            i += size

        elif cmd == 0xFC:         # change FUNC — skip next byte
            i += 2

        else:                     # normal 1-byte param + value
            param = (high_byte << 8) | cmd
            i += 1
            if i < len(raw):
                result[param] = raw[i]
            i += 1

    return result

def _data_block(resp: bytes) -> bytes:
    """Extract DATA block from full response packet."""
    if not resp or len(resp) < 24:
        return b''
    # Header: FD FD TYPE(1) SIZE_ID(1) ID(16) SIZE_PWD(1) PWD(var) FUNC(1)
    id_size  = resp[3]
    pwd_size = resp[4 + id_size]
    data_start = 4 + id_size + 1 + pwd_size + 1   # +1 for SIZE_PWD, +1 for FUNC
    return resp[data_start:-2]                      # strip 2-byte checksum

# ---------- Public API ----------

def read(*params) -> dict:
    """
    Read one or more parameters.
    read(0x01, 0x06, 0x04) → {0x01: 1, 0x06: 0, 0x04: 960, ...}
    """
    data = bytes(params)
    resp = _send_raw(data, func=0x01)
    if not resp:
        return {}
    return parse_data(_data_block(resp))

def write(param: int, value: int) -> dict:
    """
    Write a single 1-byte parameter (with response).
    Returns parsed response dict.
    """
    resp = _send_raw(bytes([param, value]), func=0x03)
    if not resp:
        return {}
    return parse_data(_data_block(resp))

def write_multi(**params) -> dict:
    """
    Write multiple 1-byte parameters in one packet (with response).
    write_multi(**{0x66: 15, 0x14: 1})
    """
    data = bytearray()
    for param, value in params.items():
        data += bytes([param, value])
    resp = _send_raw(bytes(data), func=0x03)
    if not resp:
        return {}
    return parse_data(_data_block(resp))
