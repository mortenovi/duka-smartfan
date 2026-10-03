"""
Stop a running boost without switching the fan off.

The ventilation underneath keeps running: with 24 hour mode on the fan drops
back to its low speed. A sensor-driven run is not a boost and does not stop
here - see fan_button_press.py for that.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fan_protocol as fan

print("Boost off" if fan.boost(False) else "No answer from the fan")
