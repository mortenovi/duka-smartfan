"""
Short press on a wall button: start the fan, or stop it.

  Fan running at full speed -> stop it
  Anything else             -> boost for 15 minutes

"Full speed" covers both a boost and a sensor running the fan, because the
person at the button cannot tell those apart and should not have to. Boost
is recognised by the countdown and the boost flag, never by speed: the fan
has only two speeds and a sensor uses the same one as a boost.

Stopping a sensor-driven run is not the same as stopping a boost. The boost
switch ends a boost, but a sensor that still wants ventilation simply keeps
the fan going, so power has to come off instead. If 24 hour mode was on it
is switched back on straight after, so the background ventilation continues.

A sensor is free to start the fan again right afterwards, and it may well do
so in a wet bathroom. Every press and its result is written to logs/button.log,
so whether that happens can be read off real presses rather than guessed at.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fan_protocol as fan

BOOST_MINUTES = 15

# One press of a Hue button reaches a home automation system as several
# events. Ignore a second run that follows this closely.
DEBOUNCE_SECONDS = 5

# Below this the fan is idling or ventilating quietly; above it, it is working.
FULL_SPEED_RPM = 1200

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAST_RUN = os.path.join(_HERE, ".last_press")
_LOG = os.path.join(_HERE, "logs", "button.log")


def too_soon() -> bool:
    now = time.time()
    try:
        with open(_LAST_RUN) as f:
            if now - float(f.read().strip()) < DEBOUNCE_SECONDS:
                return True
    except (OSError, ValueError):
        pass
    stamp(now)
    return False


def stamp(now: float) -> None:
    """Remember when a run happened, so duplicate events are ignored.

    Written both before and after the work: a button that sends several
    events sends them within a second, and a run that takes a few seconds
    must not leave a gap behind it where the next event slips through.
    """
    try:
        with open(_LAST_RUN, "w") as f:
            f.write(str(now))
    except OSError:
        pass


def log(line: str) -> None:
    try:
        os.makedirs(os.path.dirname(_LOG), exist_ok=True)
        with open(_LOG, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {line}\n")
    except OSError:
        pass


def short(state: dict | None) -> str:
    if state is None:
        return "no answer"
    return (f"{fan.describe(state)} power={state['power']} 24h={state['mode_24h']} "
            f"rpm={state['rpm']} countdown={state['countdown']} "
            f"boost={state['boost']} sensor={state['sensor_demand']}")


def working(state: dict) -> bool:
    """Is the fan doing more than ventilating quietly?"""
    return (state["countdown"] > 0 or state["boost"]
            or state["rpm"] >= FULL_SPEED_RPM)


def stop(state: dict) -> None:
    fan.boost(False)
    time.sleep(3)
    after = fan.read_state()

    if after and working(after):
        # Not a boost then - something else is driving the fan, and the only
        # way to stop that is to take the power away.
        fan.power(False)
        time.sleep(2)
        if state["mode_24h"]:
            fan.power(True)

    log(f"stop  -> {short(fan.read_state())}")
    print("Fan stopped")


def main() -> int:
    if too_soon():
        print(f"Ignored: another press less than {DEBOUNCE_SECONDS} seconds ago")
        return 0

    state = fan.read_state()
    if state is None:
        # Silence is not the same as a fan that is switched off. Guessing
        # here would start the fan on a dropped packet.
        log("press -> no answer from the fan, did nothing")
        print("No answer from the fan - doing nothing")
        return 1

    log(f"press -> {short(state)}")

    if working(state):
        stop(state)
    else:
        fan.boost(True)
        time.sleep(3)
        log(f"boost -> {short(fan.read_state())}")
        print(f"Boost on ({BOOST_MINUTES} min)")

    stamp(time.time())
    return 0


if __name__ == "__main__":
    sys.exit(main())
