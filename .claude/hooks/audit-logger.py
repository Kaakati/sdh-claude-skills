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

    # Ensure audit directory exists
    audit_dir = os.path.join(os.getcwd(), ".claude", "audit")
    os.makedirs(audit_dir, exist_ok=True)

    log_file = os.path.join(audit_dir, "audit.log")

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except (IOError, OSError):
        pass  # Don't block operations if logging fails

    sys.exit(0)

if __name__ == "__main__":
    main()
