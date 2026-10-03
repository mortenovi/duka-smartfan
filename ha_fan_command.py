"""
One command, named rather than spelled in bytes, for Home Assistant.

    python ha_fan_command.py boost_on

Commands:

    boost_on         start a boost
    boost_off        end a boost, leaving the ventilation under it running
    off              switch the fan off, which also ends a boost
    h24_on           constant background ventilation, and power with it
    h24_off          stop the background ventilation, leaving power on
    humidity_auto    hand the fan back to its own humidity control
    humidity_manual  humidity control against the threshold set in the app
    humidity_off     stop the fan deciding for itself to ventilate

Prints one line and exits 0 on success, 1 when the fan does not answer, and
2 when the command is not one of the above.

Two of these need a word of warning, and it belongs in whatever calls them:

* `off` does not keep the fan off. A sensor can switch it on again, and has
  been measured doing so from a standstill. For quiet, use `humidity_off`.
* `boost_off` does not stop a fan that a sensor is running. Nothing stops
  that except taking the power away, which stops the ventilation with it.
  `fan_button_press.py` shows one way to handle both cases from one button.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fan_protocol as fan

COMMANDS = {
    "boost_on": (lambda: fan.boost(True), "Boost on"),
    "boost_off": (lambda: fan.boost(False), "Boost off"),
    "off": (lambda: fan.power(False), "Fan off"),
    "h24_on": (lambda: fan.mode_24h(True), "24 hour mode on"),
    "h24_off": (lambda: fan.mode_24h(False), "24 hour mode off"),
    "humidity_auto": (lambda: fan.humidity_sensor(1), "Humidity sensor on, auto"),
    "humidity_manual": (lambda: fan.humidity_sensor(2), "Humidity sensor on, manual"),
    "humidity_off": (lambda: fan.humidity_sensor(0), "Humidity sensor off"),
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print("Usage: python ha_fan_command.py " + " | ".join(COMMANDS))
        return 2

    action, said = COMMANDS[sys.argv[1]]
    if not action():
        print("No answer from the fan")
        return 1
    print(said)
    return 0


if __name__ == "__main__":
    sys.exit(main())
