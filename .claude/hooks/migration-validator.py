#!/usr/bin/env python3
"""
PreToolUse hook: Validates database migration files before they are written.

Checks:
1. Migration files must have reversible/down methods
2. No raw SQL string concatenation
3. Warns about irreversible operations without expand/contract pattern

Exit codes:
  0 = allow (pass or not a migration file)
  2 = block (dangerous migration pattern detected)
"""
import json
import sys
import re

def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # Only check Write tool for migration files
    if tool_name not in ("Write", "Edit"):
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    normalized_path = file_path.replace("\\", "/")

    # Check if this is a migration file
    is_migration = any(pattern in normalized_path for pattern in [
        "/migrations/",
        "/db/migrate/",
        "/migrate/",
    ])

    if not is_migration:
        sys.exit(0)

    content = tool_input.get("content", "")
    if not content and tool_name == "Edit":
        content = tool_input.get("new_string", "")

    warnings = []

    # Check 1: Ruby migration must have reversible pattern or down method
    if file_path.endswith(".rb"):
        has_down = bool(re.search(r'\bdef\s+down\b', content))
        has_reversible = bool(re.search(r'\breversible\s+do\b', content))
        has_change = bool(re.search(r'\bdef\s+change\b', content))
        has_up = bool(re.search(r'\bdef\s+up\b', content))

        # If using up/down pattern, down must exist
        if has_up and not has_down:
            warnings.append("Migration has 'up' method but no 'down' method. Add a 'down' method for rollback safety.")

        # Check for irreversible operations in change method (no auto-rollback)
        if has_change and not has_reversible:
            irreversible_ops = []
            if re.search(r'\bremove_column\b', content):
                irreversible_ops.append("remove_column")
            if re.search(r'\bchange_column\b', content):
                irreversible_ops.append("change_column")
            if re.search(r'\bdrop_table\b', content):
                irreversible_ops.append("drop_table")
            if re.search(r'\brename_column\b', content):
                irreversible_ops.append("rename_column")
            if re.search(r'\bexecute\b', content):
                irreversible_ops.append("execute (raw SQL)")

            if irreversible_ops:
                warnings.append(
                    f"Irreversible operations in 'change' method: {', '.join(irreversible_ops)}. "
                    "Use 'reversible do' block or explicit 'up'/'down' methods per database.md."
                )

    # Check 2: No raw SQL string interpolation
    sql_interpolation = re.findall(r'execute\s*[(\s]*["\'].*#\{.*\}.*["\']', content)
    if sql_interpolation:
        warnings.append(
            "Raw SQL with string interpolation detected. Use parameterized queries or "
            "ActiveRecord methods to prevent SQL injection per security.md."
        )

    # Check 3: Warn about destructive operations
    destructive_ops = []
    if re.search(r'\bdrop_table\b', content):
        destructive_ops.append("drop_table")
    if re.search(r'\btruncate\b', content, re.IGNORECASE):
        destructive_ops.append("TRUNCATE")
    if re.search(r'\bDROP\s+INDEX\b', content, re.IGNORECASE):
        destructive_ops.append("DROP INDEX")

    if destructive_ops:
        warnings.append(
            f"Destructive operations detected: {', '.join(destructive_ops)}. "
            "Follow expand/contract pattern per database.md. Consider multi-step migration."
        )

    if warnings:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": "Migration validation warnings:\n" + "\n".join(f"- {w}" for w in warnings)
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    sys.exit(0)

if __name__ == "__main__":
    main()
