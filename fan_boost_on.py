"""Start boost. The fan beeps once and runs for the time set in the app."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fan_protocol as fan

print("Boost on" if fan.boost(True) else "No answer from the fan")
