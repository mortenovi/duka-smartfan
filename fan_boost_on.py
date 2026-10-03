"""Start boost (15 minutes). One packet, so the fan beeps once."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fan_protocol as fan
from fan_boost_toggle import BOOST_MINUTES, BOOST_PACKET

answer = fan.send_raw(BOOST_PACKET, func=0x03)
print(f"Boost on ({BOOST_MINUTES} min)" if answer else "No answer from the fan")
