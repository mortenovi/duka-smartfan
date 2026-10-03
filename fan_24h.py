"""
Switch 24 hour mode on or off: python fan_24h.py on|off

On  = constant background ventilation at low speed, and power on with it.
Off = the rotor stops within ten seconds, and the fan rests with power on.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fan_protocol as fan

if len(sys.argv) != 2 or sys.argv[1] not in ("on", "off"):
    print("Usage: python fan_24h.py on|off")
    sys.exit(2)

ok = fan.mode_24h(sys.argv[1] == "on")
print(("24 hour mode on" if sys.argv[1] == "on" else "24 hour mode off")
      if ok else "No answer from the fan")
