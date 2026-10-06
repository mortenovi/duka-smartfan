"""
One button, two scripts, and a way for them to agree.

A wall button that has a short press and a long press sends several events
for one press, and a home automation system runs an automation for each of
them. Measured on a Philips Hue button: a genuine long press also produces
the short press event, within the same second.

So both scripts run. Left alone, the short press script sees the fan the
long press script has just stopped, decides it is not running, and starts a
boost - which is the opposite of what the person at the wall asked for.

They cannot sort this out by each remembering its own last run: the problem
is precisely that neither knows about the other. So they share one note.

The rules:

* A long press claims the button the moment it starts, and stands down only
  for another long press within DEBOUNCE_SECONDS, which is a duplicate event.
* A short press waits HOLD_GRACE_SECONDS before acting, then stands down if
  a long press has claimed the button in the meantime - whichever of the two
  the automation happened to start first.

The cost is that a short press is a second slower to take effect. The gain
is that a long press does what it says, every time.
"""

import json
import os
import time

DEBOUNCE_SECONDS = 5

# Long enough for the long press event to arrive and claim the button after
# the short press event did. Measured arrival: within the same second.
HOLD_GRACE_SECONDS = 1.3

_NOTE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".last_button")


def claim(action: str) -> None:
    """Write down that this action is happening now. Never fails loudly."""
    try:
        tmp = _NOTE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"action": action, "at": time.time()}, f)
        os.replace(tmp, _NOTE)
    except OSError:
        pass


def claimed(within: float, action: str | None = None) -> bool:
    """
    Did a run happen less than `within` seconds ago?

    With `action`, only that kind counts. Returns False when the note cannot
    be read: being unable to see a claim must not stop the button working.
    """
    try:
        with open(_NOTE, encoding="utf-8") as f:
            note = json.load(f)
        if action is not None and note.get("action") != action:
            return False
        return time.time() - float(note["at"]) < within
    except (OSError, ValueError, KeyError):
        return False
