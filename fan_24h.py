"""
Switch 24 hour mode on or off: python fan_24h.py on|off

On  = constant background ventilation at low speed (930 rpm on this unit).
Off = the fan stops spinning, but power stays on unless we also clear it,
      so both parameters are written. See PROTOCOL.md.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fan_protocol as fan

if len(sys.argv) != 2 or sys.argv[1] not in ("on", "off"):
    print("Usage: python fan_24h.py on|off")
    sys.exit(2)

if sys.argv[1] == "on":
    fan.write(0x03, 1)
    answer = fan.write(0x01, 1)
    print("24 hour mode on" if answer else "No answer from the fan")
else:
    fan.write(0x03, 0)
    answer = fan.write(0x01, 0)
    print("24 hour mode off, fan stopped" if answer else "No answer from the fan")
