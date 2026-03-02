"""
Toggle Duka SmartFan boost mode.

- Fan running  → turn OFF
- Fan stopped  → activate boost

Designed for a Hue smart button / Home Assistant automation.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _fan_proto as fan

BOOST_MINUTES = 15

# Read current state
s = fan.read(0x01, 0x04)
power = s.get(0x01, 0)
rpm   = s.get(0x04) or 0

if power and rpm > 0:
    # Fan is running → turn off
    fan.write(0x01, 0)
    print("Fan OFF")
else:
    # Fan is off → activate boost (single packet, one beep)
    data = bytes([
        0x01, 0x01,
        0x02, 0x01,
        0x03, 0x01,
        0x05, 0x01,
        0x07, 0x02,
        0x06, 0x01,
        0x14, BOOST_MINUTES,
    ])
    fan._send_raw(data, func=0x03)
    print(f"Boost ON ({BOOST_MINUTES} min)")
