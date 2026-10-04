"""
Long press on a wall button: quiet, or back to normal.

  python fan_button_hold.py          toggle - quiet if it is running, back if it is paused
  python fan_button_hold.py quiet    pause all ventilation
  python fan_button_hold.py resume   put everything back the way it was

"Quiet" switches off the humidity sensor, the temperature sensor, 24 hour
mode and the power, in that order. The sensors go first, because switching
the fan off while a sensor still wants ventilation only lasts until the
sensor says so again - the fan has been measured starting itself from a
standstill.

What the fan was doing is written to a file first, so resume puts back the
owner's own settings rather than someone's idea of a default.

A pause does not end by itself. A script runs and exits; it cannot wake up
in three hours. Whatever triggers the long press has to schedule the resume
as well - see the automation in README.md.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fan_protocol as fan

DEBOUNCE_SECONDS = 5

# A saved state older than this belongs to a pause that is long over.
PAUSE_MAX_AGE_SECONDS = 12 * 3600

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAST_RUN = os.path.join(_HERE, ".last_hold")
_SAVED = os.path.join(_HERE, ".paused_state")
_LOG = os.path.join(_HERE, "logs", "button.log")


def too_soon() -> bool:
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


def log(line: str) -> None:
    try:
        os.makedirs(os.path.dirname(_LOG), exist_ok=True)
        with open(_LOG, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {line}\n")
    except OSError:
        pass


def quiet() -> int:
    state = fan.read_state()
    if state is None:
        print("No answer from the fan - doing nothing")
        log("hold  -> no answer from the fan, did nothing")
        return 1

    # A pause is already running: the fan's current settings are the paused
    # ones, so saving them would overwrite the owner's real settings with
    # zeros and resume would put back a fan with its sensors off. Keep what
    # was saved and only apply the quiet settings again, which also ends a
    # stray boost. A save older than this is a leftover, not a running pause.
    paused = (os.path.exists(_SAVED)
              and time.time() - os.path.getmtime(_SAVED) < PAUSE_MAX_AGE_SECONDS)

    saved = {
        "humidity_sensor": fan.read(0x0F).get(0x0F, 1),
        "temperature_sensor": fan.read(0x11).get(0x11, 0),
        "mode_24h": state["mode_24h"],
        "power": state["power"],
        "at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if not paused:
        try:
            with open(_SAVED, "w", encoding="utf-8") as f:
                json.dump(saved, f)
        except OSError:
            print("Could not write the saved settings - not pausing")
            return 1

    fan.humidity_sensor(0)
    fan.temperature_sensor(False)
    fan.write(0x03, 0)
    fan.power(False)
    time.sleep(3)
    kept = "kept the earlier save" if paused else f"saved {saved}"
    log(f"quiet -> {kept} | now {fan.describe(fan.read_state())}")
    print("All ventilation paused")
    return 0


def resume() -> int:
    try:
        with open(_SAVED, encoding="utf-8") as f:
            saved = json.load(f)
    except (OSError, ValueError):
        # Nothing saved: put the fan back to something sensible rather than
        # leaving the bathroom with no ventilation at all.
        fan.humidity_sensor(1)
        fan.mode_24h(True)
        log("resume-> nothing saved, fell back to humidity auto and 24 hour mode")
        print("Nothing saved - humidity sensor on, 24 hour mode on")
        return 0

    fan.humidity_sensor(int(saved.get("humidity_sensor", 1)))
    fan.temperature_sensor(bool(saved.get("temperature_sensor", 0)))
    fan.write(0x03, 1 if saved.get("mode_24h") else 0)
    fan.power(bool(saved.get("power")) or bool(saved.get("mode_24h")))
    try:
        os.remove(_SAVED)
    except OSError:
        pass
    time.sleep(3)
    log(f"resume-> restored {saved} | now {fan.describe(fan.read_state())}")
    print("Ventilation back to normal")
    return 0


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg not in ("", "quiet", "resume"):
        print("Usage: python fan_button_hold.py [quiet|resume]")
        return 2

    # The resume comes from a timer, not from a finger, so it is never debounced.
    if arg != "resume" and too_soon():
        print(f"Ignored: another press less than {DEBOUNCE_SECONDS} seconds ago")
        return 0

    if arg == "quiet":
        return quiet()
    if arg == "resume":
        return resume()
    return resume() if os.path.exists(_SAVED) else quiet()


if __name__ == "__main__":
    sys.exit(main())
