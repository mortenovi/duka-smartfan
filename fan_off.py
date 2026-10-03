"""
Switch the fan off.

This also stops a running boost and clears its countdown - switching power
off is the only way to end a boost early.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fan_protocol as fan

answer = fan.write(0x01, 0)
print("Fan off" if answer else "No answer from the fan")
