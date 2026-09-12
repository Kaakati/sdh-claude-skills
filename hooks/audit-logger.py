#!/usr/bin/env python3
"""Audit trail: one JSON line per tool call, for compliance.

Registered on PostToolUse and PostToolUseFailure for every tool (matcher `*`), and on
PermissionDenied (auto-mode classifier denials). PostToolUse alone fires only after a SUCCESSFUL
call, so the old `Bash|Edit|Write` registration recorded no failed call, no denial, and no
NotebookEdit, MCP, WebFetch, Agent or Skill call at all. A hook's own deny or ask never reaches
this script (the call never runs); `_hooklib._decision` appends those records from inside the
gate, without a second process.

Three properties an audit trail needs, and this one lacked:
  * Anchored to the project (`hooklib.audit_dir`), not the handler's cwd, which follows a `cd`
    or a worktree. A worktree teammate's log used to be deleted with its worktree.
  * Redacted before it is written (`hooklib.redact`). The first 500 characters of every shell
    command went to plaintext, tokens included, in a directory only this plugin's own .gitignore
    ignored. The audit dir now carries its own ignore-everything .gitignore. The whole command is
    redacted, then cut: redaction is linear, so a long command cannot run this past its timeout.
  * A gap is announced where someone reads it: systemMessage for the user, additionalContext for
    the model. A bare print on PostToolUse lands in the debug log, the invisible failure this
    trail exists to prevent.

A shell command is recorded as `command` for Bash, PowerShell and Monitor alike (the PowerShell tool
is on by default on Windows); a Monitor call that opens a WebSocket has no command and is recorded
as `raw_input`.

Fail OPEN — a logging failure must never block the tool. Never SILENTLY: a silent write failure
leaves invisible holes AND false confidence that the trail is complete, which is strictly worse
than having no trail. Say so, every time.
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import _hooklib as hooklib
except Exception as _exc:  # redaction lives there: without it, record nothing and say so
    hooklib = None
    _IMPORT_ERROR = _exc

FILE_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit", "Read")
SHELL_TOOLS = ("Bash", "PowerShell", "Monitor")
CONTEXT_EVENTS = ("PostToolUse", "PostToolUseFailure")


def report_gap(event, reason):
    """One JSON object: the user sees it (systemMessage), and so does the model where it can."""
    line = (f"HOOK ERROR: audit-logger {reason}. THIS ACTION WAS NOT RECORDED; "
            "the audit trail now has a gap.")
    name = (event.get("hook_event_name") if isinstance(event, dict) else None) or "PostToolUse"
    context_event = name if name in CONTEXT_EVENTS else None
    try:
        hooklib.emit(line, context_event, system_message=line)
    except Exception:  # _hooklib is the thing that failed: do not depend on it to say so
        payload = {"systemMessage": line}
        if context_event:
            payload["hookSpecificOutput"] = {"hookEventName": context_event, "additionalContext": line}
        print(json.dumps(payload))


def _first_line(value):
    lines = hooklib.redact(str(value or "")).strip().splitlines()
    return lines[0][:200] if lines else "(no detail)"


def outcome_for(event):
    name = event.get("hook_event_name") or "PostToolUse"
    if name == "PostToolUseFailure":
        return "error: " + _first_line(event.get("error"))
    if name == "PermissionDenied":
        return "denied: " + _first_line(event.get("reason"))
    return "ok"


def details_for(event):
    tool, data = hooklib.tool_name(event), hooklib.tool_input(event)
    if tool in SHELL_TOOLS and (tool != "Monitor" or data.get("command")):
        return {"command": hooklib.redact(str(data.get("command", "")))[:500]}
    if tool in FILE_TOOLS:
        return {"file_path": hooklib.get_file_path(event), "action": tool.lower()}
    return {"raw_input": hooklib.redact(json.dumps(data, sort_keys=True))[:200]}


def build_entry(event):
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": event.get("session_id", "unknown"),
        "event": event.get("hook_event_name") or "PostToolUse",
        "tool": hooklib.tool_name(event) or "unknown",
        "tool_use_id": event.get("tool_use_id"),
        "outcome": outcome_for(event),
        "target": hooklib.get_file_path(event),
        "details": details_for(event),
    }


def main():
    if hooklib is None:
        report_gap(None, f"could not load _hooklib ({type(_IMPORT_ERROR).__name__}: {_IMPORT_ERROR})")
        sys.exit(0)
    event, error = hooklib.load_event_strict()
    if error:
        report_gap(event, f"received an event it could not read ({error})")
        sys.exit(0)
    failure = hooklib.append_audit(event, build_entry(event))
    if failure:
        report_gap(event, f"could not write the audit trail — {failure}")
    sys.exit(0)


if __name__ == "__main__":
    # Guard the entry too: nothing here may produce a raw traceback. Fail open, report one line.
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        report_gap(None, f"failed to run — {type(exc).__name__}: {exc}")
        sys.exit(0)
