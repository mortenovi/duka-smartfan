"""
Print the fan's whole state as JSON, for Home Assistant or anything else
that would rather parse than read.

    python ha_fan_state.py

    {"available": true, "state": "mode_24h", "state_text": "24 hour mode",
     "power": 1, "mode_24h": 1, "rpm": 930, "countdown_seconds": 0,
     "boost": 0, "sensor_demand": 0, "humidity": 74, "temperature": 26,
     "humidity_sensor": 1, "read_at": "2026-10-03T17:12:04"}

When the fan does not answer, the output is {"available": false, "state":
"no_answer"} and the exit code is still 0. Nothing is guessed: silence is not
the same as a fan that is switched off.

The exit code is 0 because the script did its job - it reported. The failure
belongs to the fan, and it is in the JSON. A Home Assistant command line
sensor throws the whole output away when the command exits non-zero, which
would hide exactly the reading that matters, and leave the last successful
one standing as if it were current.

**Build on `state`, not on `state_text`.** The key is stable; the wording
may be improved.

One reading is one round trip per parameter, because this unit does not
answer a request that asks for several at once. That is eight packets for
the output above, so poll every 30 seconds or so rather than every second.

Home Assistant, in configuration.yaml:

    command_line:
      - sensor:
          name: Smartfan
          command: "python /config/scripts/duka-smartfan/ha_fan_state.py"
          value_template: "{{ value_json.state }}"
          # The sensor's own state tells you whether the fan answered:
          # no_answer means it did not. Do not build availability on the
          # last reading's attributes - they stay behind when a reading fails.
          json_attributes:
            - state_text
            - power
            - mode_24h
            - rpm
            - countdown_seconds
            - boost
            - sensor_demand
            - humidity
            - temperature
            - humidity_sensor
          scan_interval: 30
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fan_protocol as fan


def main() -> int:
    state = fan.read_state()
    if state is None:
        print(json.dumps({"available": False, "state": "no_answer",
                          "state_text": fan.describe(None),
                          "read_at": time.strftime("%Y-%m-%dT%H:%M:%S")}))
        return 0

    out = {
        "available": True,
        "state": fan.state_key(state),
        "state_text": fan.describe(state),
        "power": state["power"],
        "mode_24h": state["mode_24h"],
        "rpm": state["rpm"],
        "countdown_seconds": state["countdown"],
        "boost": state["boost"],
        "sensor_demand": state["sensor_demand"],
        "humidity": fan.read(0x2E).get(0x2E),
        "temperature": fan.read(0x31).get(0x31),
        "humidity_sensor": fan.read(0x0F).get(0x0F),
        "read_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
