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
  * Boost is switched with 0x05, and only with 0x05. Writing 0 to the boost
    status 0x07, to the countdown 0x06 or to 0x14 does nothing - those are
    status values the unit sets itself, and 0x14 is the humidity threshold.
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

# Boost is switched with 0x05, measured byte by byte on 3 Oct 2026.
# Everything the old packet carried besides this was noise: 0x02 did
# nothing, 0x07 and 0x06 are status and countdown that the unit sets
# itself, and 0x14 is the humidity threshold.
# Power has to be on first: 05=01 on a fan with no power does nothing.
BOOST_ON = bytes([
    0x01, 0x01,   # power on
    0x05, 0x01,   # boost on
])

BOOST_OFF = bytes([
    0x05, 0x00,   # boost off, without cutting power
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
        fan.send_raw(BOOST_OFF, func=0x03)
        print("Boost off")
    else:
        fan.send_raw(BOOST_ON, func=0x03)
        print(f"Boost on ({BOOST_MINUTES} min)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
