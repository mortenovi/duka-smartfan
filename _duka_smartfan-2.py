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

def fan_off():
    """Turn the fan completely off."""
    resp = send([0x01, 0x00])
    print("Fan OFF")
    return resp

def fan_on(speed=2):
    """Turn the fan on at a given speed (1-5)."""
    resp = send([0x01, 0x01, 0x02, speed])
    print(f"Fan ON at speed {speed}")
    return resp

def boost_start(minutes=15):
    """Turn fan on and start boost mode for the given number of minutes (1-60)."""
    send([0x01, 0x01])  # turn on
    time.sleep(1)
    resp = send([0x14, minutes])
    print(f"Boost ON ({minutes} minutes)")
    return resp

def boost_stop():
    """Stop boost mode but keep fan running."""
    resp = send([0x14, 0x00])
    print("Boost OFF")
    return resp

def get_status():
    """Read current fan status."""
    resp = send([0x01, 0x02, 0x06, 0x14], func=0x01)
    if resp:
        print(f"Status (raw): {resp.hex()}")
    else:
        print("No response")
    return resp

# --- Main: change the line below to control the fan ---
boost_start(15)   # Start 15-minute boost
# fan_off()       # Turn fan completely off
# boost_stop()    # Stop boost, keep fan running
# fan_on(speed=2) # Turn on at speed 2
# get_status()    # Read current status