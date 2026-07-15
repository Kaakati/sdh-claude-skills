#!/usr/bin/env python3
"""Development helper: capture a REAL hook event to a fixture file.

Hooks written blind and tested in a live session are how you get defects. The loop that
works (The Governed Agent, Ch. 9):

  1. Capture a real event — register THIS hook on the event you care about, trigger the
     tool once, and you have a real fixture instead of a guess at the schema.
  2. Develop against the fixture, not against the session. Piping a captured event into
     your hook is a sub-second loop; "edit, start a session, trigger the tool, squint at
     the output" is a minute-long loop you will run fifty times.

## Use it

Add to your project's `.claude/settings.json` (temporarily — this is a dev tool, not a gate):

    {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
      {"type": "command", "command": "bash hooks/run-python.sh hooks/capture-event.py"}]}]}}

Trigger the tool once, then look in `hooks/tests/fixtures/`:

    $ ls hooks/tests/fixtures/
    PreToolUse-Bash-1784092811.json

Now develop at speed — no session required:

    $ python hooks/my-new-gate.py < hooks/tests/fixtures/PreToolUse-Bash-1784092811.json; echo "exit: $?"

This is also the single most useful diagnostic when a hook misbehaves (Ch. 25): running the
hook by hand separates "the hook has a bug" from "the hook isn't being invoked". If the
hand-run produces the right decision, the bug is in registration or matching — not the script.

Always exits 0 and emits nothing, so it never disturbs the session it is observing.
"""

import json
import os
import sys
import time

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "fixtures")


def main():
    raw = sys.stdin.read()

    # Name the fixture after what it actually is, so a directory of them is readable.
    event, tool = "event", ""
    try:
        data = json.loads(raw)
        event = data.get("hook_event_name") or data.get("hookEventName") or "event"
        tool = data.get("tool_name", "")
    except Exception:
        pass  # a malformed event is still worth capturing — that's often the bug

    name = "-".join(p for p in (event, tool, str(int(time.time()))) if p) + ".json"
    os.makedirs(FIXTURE_DIR, exist_ok=True)
    with open(os.path.join(FIXTURE_DIR, name), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(raw)


if __name__ == "__main__":
    # Never disturb the session it observes: capture failures are silent-by-design here
    # (this is a dev tool, not a gate — the "silent failure" rule in Ch. 9 is about gates
    # masquerading as green; a capture helper has no such claim to make).
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
