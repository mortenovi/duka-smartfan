"""
Switch the fan off when a window is opened, for a home automation.

Written for a Velux window in a bathroom: the window cover goes from closed
to open, the automation runs this, and the fan stops instead of pulling air
past an open window. Any sensor that can say "a window just opened" will do.

    python fan_off_when_window_opens.py

  Rotor is turning  -> switch the power off
  Rotor is still    -> do nothing
  No answer         -> do nothing, and say so

The last line is the point of using read_state(): a lost answer must never
look like a fan that has already stopped. That is exactly the moment the
window was opened and the fan should be switched off.

Two things the next reader should know before calling this a half measure:

* It switches off ONCE and nothing more. The humidity sensor sits on Auto
  and can start the fan again a few minutes later - measured from a
  standstill, see PROTOCOL.md. In a bathroom, which is humid precisely when
  someone opens the window, that will happen. It is a deliberate choice by
  the owner of the fan this was written for: switch off once, and let the
  fan decide for itself afterwards.
* The reliable way to keep the fan quiet while the window is open is
  `humidity_off`, which takes the sensor out of the decision, and switching
  it back on when the window closes. That is a different automation with a
  different risk: forget to switch the sensor back on, and the bathroom has
  no automatic ventilation at all.

It never starts the fan, and it never touches 24 hour mode.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fan_protocol as fan


def main() -> int:
    state = fan.read_state()
    if state is None:
        print("No answer from the fan - doing nothing")
        return 1

    # rpm is the only honest sign that the rotor is turning: power alone can
    # be on with the rotor still, and the fan also starts itself on its own
    # sensors, with no boost countdown and no boost flag to show for it.
    if state["rpm"] > 0:
        fan.power(False)
        print(f"Fan off (was running at {state['rpm']} rpm, "
              f"state {fan.state_key(state)})")
    else:
        print(f"Rotor already still (state {fan.state_key(state)}) "
              "- doing nothing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
