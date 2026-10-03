"""
Toggle boost on and off. Written for a single button.

  Boost running -> stop boost, and resume 24 hour mode if it was on
  No boost      -> start boost

This is a BOOST toggle only. It never changes 24 hour mode, and it never
decides anything from whether the fan happens to be spinning.

Three rules that came out of measuring the unit (see PROTOCOL.md):

  * The fan spins when power is on AND (24 hour mode is on OR boost runs).
    A toggle that reads "is it spinning" therefore switches the fan off
    when 24 hour mode is on, instead of giving you boost.
  * Boost can only be stopped by switching power off. Writing 0 to the
    boost status, the countdown or parameter 0x14 does nothing.
  * One press of a smart button can reach a home automation system as
    several events. Without the debounce below, the second run undoes
    the first.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fan_protocol as fan

BOOST_MINUTES = 15
DEBOUNCE_SECONDS = 5

_LAST_RUN = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".last_toggle")

# One packet, so the fan beeps once. Note what is NOT in it: 0x03, the
# 24 hour mode flag. Sending it here switches that setting back on behind
# the user's back every time boost is started.
BOOST_PACKET = bytes([
    0x01, 0x01,           # power on
    0x02, 0x01,           # speed 1
    0x05, 0x01,           # aux
    0x07, 0x02,           # boost mode
    0x06, 0x01,           # boost on
])


def too_soon() -> bool:
    """True when the previous run was less than DEBOUNCE_SECONDS ago."""
    now = time.time()
    try:
        with open(_LAST_RUN) as f:
            if now - float(f.read().strip()) < DEBOUNCE_SECONDS:
                return True
    except (OSError, ValueError):
        pass
    try:
        with open(_LAST_RUN, "w") as f:
            f.write(str(now))
    except OSError:
        pass
    return False


def main() -> int:
    if too_soon():
        print(f"Ignored: another press less than {DEBOUNCE_SECONDS} seconds ago")
        return 0

    state = fan.read_state()
    if state is None:
        # Doing nothing is safer than assuming the fan is off and starting
        # boost because the network dropped a packet.
        print("No answer from the fan - doing nothing")
        return 1

    if state["countdown"] > 0 or state["boost"]:
        fan.write(0x01, 0)
        if state["mode_24h"]:
            time.sleep(2)
            fan.write(0x01, 1)
            print("Boost off - back to 24 hour mode")
        else:
            print("Boost off")
    else:
        fan.send_raw(BOOST_PACKET, func=0x03)
        print(f"Boost on ({BOOST_MINUTES} min)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
