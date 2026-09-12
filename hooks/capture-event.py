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

## What a fixture holds

The event byte for byte: stdin is read as bytes, so an event is not re-encoded through the
console codepage on its way to disk. That includes whatever the tool was about to write, so a
fixture can hold a real credential. `hooks/tests/fixtures/` is gitignored, the file is created
owner-only on POSIX, and a fixture is never overwritten: parallel tool calls land in the same
second, and the second capture used to replace the first silently.

Always exits 0 and emits nothing, so it never disturbs the session it is observing.
"""

import json
import os
import sys
import time

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "fixtures")


def fixture_stem(raw):
    """`<event>-<tool>-<epoch>`, so a directory of fixtures is readable."""
    event, tool = "event", ""
    try:
        data = json.loads(raw.decode("utf-8", "replace"))
        event = data.get("hook_event_name") or data.get("hookEventName") or "event"
        tool = data.get("tool_name", "")
    except Exception:
        pass  # a malformed event is still worth capturing — that's often the bug
    safe = ["".join(c if c.isalnum() or c in "_-" else "_" for c in str(p)) for p in (event, tool)]
    return "-".join(p for p in safe + [str(int(time.time()))] if p)


def write_fixture(stem, raw):
    """Create a new fixture file (never replacing one); return its path."""
    os.makedirs(FIXTURE_DIR, exist_ok=True)
    for attempt in range(1000):
        path = os.path.join(FIXTURE_DIR, f"{stem}-{attempt}.json" if attempt else f"{stem}.json")
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
        except FileExistsError:
            continue
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
        return path
    return None


def main():
    raw = sys.stdin.buffer.read()
    write_fixture(fixture_stem(raw), raw)


if __name__ == "__main__":
    # Never disturb the session it observes: capture failures are silent-by-design here
    # (this is a dev tool, not a gate — the "silent failure" rule in Ch. 9 is about gates
    # masquerading as green; a capture helper has no such claim to make).
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
