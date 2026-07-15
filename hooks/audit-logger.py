#!/usr/bin/env python3
"""PostToolUse hook: Audit logger for compliance.
Logs all tool executions to .claude/audit/audit.log in JSON-lines format."""

import json
import sys
import os
from datetime import datetime, timezone

def main():
    data = json.load(sys.stdin)

    tool_name = data.get("tool_name", "unknown")
    tool_input = data.get("tool_input", {})
    session_id = data.get("session_id", "unknown")

    # Extract relevant info based on tool type
    details = {}
    if tool_name in ("Edit", "Write"):
        details["file_path"] = tool_input.get("file_path", "")
        details["action"] = "edit" if tool_name == "Edit" else "write"
    elif tool_name == "Bash":
        details["command"] = tool_input.get("command", "")[:500]  # Truncate long commands
    elif tool_name == "Read":
        details["file_path"] = tool_input.get("file_path", "")
        details["action"] = "read"
    else:
        details["raw_input"] = str(tool_input)[:200]

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "tool": tool_name,
        "details": details,
    }

    # Create the directory AND append, inside one guard. Both steps can fail (a
    # read-only checkout, a `.claude` that is a file, a full disk) and neither may
    # crash the hook.
    #
    # Fail OPEN — a logging failure must never block the tool. But never SILENTLY:
    # the audit trail is the artifact you reconstruct an incident from, so a silent
    # write failure leaves invisible holes AND false confidence that the trail is
    # complete. That is strictly worse than having no trail. Say so, every time.
    try:
        audit_dir = os.path.join(os.getcwd(), ".claude", "audit")
        os.makedirs(audit_dir, exist_ok=True)
        log_file = os.path.join(audit_dir, "audit.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as exc:
        print(
            f"HOOK ERROR: audit-logger could not write the audit trail — "
            f"{type(exc).__name__}: {exc}. THIS ACTION WAS NOT RECORDED; the audit "
            f"trail now has a gap."
        )

    sys.exit(0)

if __name__ == "__main__":
    # Guard the entry too: a malformed event (json.load) must not produce a raw
    # traceback. Fail open, report one line.
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print(
            f"HOOK ERROR: audit-logger failed to run — {type(exc).__name__}: {exc}. "
            f"This action was NOT recorded; the audit trail now has a gap."
        )
        sys.exit(0)
