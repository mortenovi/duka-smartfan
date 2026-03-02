import socket
import struct
import time
import json
import os

_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
with open(_config_path) as _f:
    _config = json.load(_f)

DEVICE_ID = _config['device_id']
PASSWORD = _config['password']
FAN_IP = _config['fan_ip']

def build_packet(device_id, password, func, data):
    id_bytes = device_id.encode('ascii')
    pwd_bytes = password.encode('ascii')
    packet = bytearray()
    packet += b'\xFD\xFD'
    packet += b'\x02'
    packet += bytes([len(id_bytes)])
    packet += id_bytes
    packet += bytes([len(pwd_bytes)])
    packet += pwd_bytes
    packet += bytes([func])
    packet += data
    chksum = sum(packet[2:]) & 0xFFFF
    packet += struct.pack('<H', chksum)
    return bytes(packet)

def send(data, func=0x03):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3)
    packet = build_packet(DEVICE_ID, PASSWORD, func, bytes(data))
    sock.sendto(packet, (FAN_IP, 4000))
    try:
        resp, _ = sock.recvfrom(1024)
        return resp
    except:
        return None
    finally:
        sock.close()

def fan_on():
    send([0x01, 0x01])
    print("Fan ON")

def fan_off():
    send([0x01, 0x00])
    print("Fan OFF")

def boost_on():
    fan_on()
    time.sleep(1)
    send([0x14, 0x01])
    print("Boost ON")

def boost_off():
    send([0x14, 0x00])
    print("Boost OFF")

def get_status():
    resp = send([0x01, 0x02, 0x06], func=0x01)
    print(f"Status response: {resp.hex() if resp else 'no response'}")

fan_off()
