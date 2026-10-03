"""
Read everything the fan will tell you and print it.

Read-only: this never changes anything on the unit. Run it before and
after a command to see what that command actually did.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fan_protocol as fan

# The parameters this model answers. See fan_protocol.py for what is known
# about each of them.
PARAMS = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x0A, 0x0F,
          0x14, 0x16, 0x17, 0x18, 0x1A, 0x1B, 0x23, 0x2E, 0x31]

NAMES = {
    0x01: "power (0/1)",
    0x03: "24 hour mode (0/1)",
    0x04: "fan speed (rpm)",
    0x06: "boost countdown (s)",
    0x07: "boost running (0/1)",
    0x2E: "humidity (%)",
    0x31: "temperature (C)",
}


def main() -> int:
    state = fan.read_state()
    if state is None:
        print("No answer from the fan")
        return 1

    print(f"=== Duka Smartfan {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
    print(f"  State: {fan.describe(state)}")

    # Read one at a time: the unit does not answer long requests.
    for param in PARAMS:
        value = fan.read(param).get(param)
        name = NAMES.get(param, f"parameter 0x{param:02X}")
        print(f"  0x{param:02X}  {name:<22} {'-' if value is None else value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
