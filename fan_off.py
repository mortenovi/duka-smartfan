"""
Switch the fan off. This also ends a running boost and clears its countdown.

Note that off is not the same as quiet: a sensor can switch the fan on again
by itself. Use fan_button_hold.py to pause the sensors as well.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fan_protocol as fan

print("Fan off" if fan.power(False) else "No answer from the fan")
