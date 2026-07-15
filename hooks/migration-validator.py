#!/usr/bin/env python3
"""PreToolUse hook: Validates database migration files before they are written.

Checks:
1. Migration files must have reversible/down methods
2. No raw SQL string concatenation
3. Warns about irreversible operations without expand/contract pattern

Emits an 'ask' (confirmation) decision when warnings are found. Fails open: a
bug here must not block unrelated writes, so it uses the default run policy."""

import re

import _hooklib as hooklib

# Wrapper-agnostic: "/migrate/" already matches backend/db/migrate, api/db/migrate, or
# db/migrate at the repo root. A hard-coded "backend/" would only ever match repos that
# adopted our old forced layout.
MIGRATION_PATH_PATTERNS = ["/migrations/", "/migrate/"]

# `remove_column :t, :c` cannot be reversed — ActiveRecord does not know the type to restore.
# `remove_column :t, :c, :string` CAN. Match the 2-arg form only, or the hook fires on the
# exact form the migration guide recommends, and a gate that flags correct code is a gate
# people learn to ignore.
REMOVE_COLUMN_NO_TYPE = re.compile(
    r"\bremove_column\s+[:\"'][\w\"']+\s*,\s*[:\"'][\w\"']+\s*(?:\)|$|#)", re.M
)
# `drop_table :t` is irreversible; `drop_table :t do |t| ... end` is reversible.
DROP_TABLE_NO_BLOCK = re.compile(r"\bdrop_table\s+[:\"'][\w\"']+\s*(?!.*\bdo\b)(?:\)|$|#)", re.M)


def check(event):
    if hooklib.tool_name(event) not in ("Write", "Edit"):
        return

    file_path = hooklib.get_file_path(event)
    normalized_path = hooklib.normalize(file_path)

    if not any(pattern in normalized_path for pattern in MIGRATION_PATH_PATTERNS):
        return

    content = hooklib.get_content(event)
    warnings = []

    # Check 1: Ruby migration must have reversible pattern or down method
    if file_path.endswith(".rb"):
        has_down = bool(re.search(r'\bdef\s+down\b', content))
        has_reversible = bool(re.search(r'\breversible\s+do\b', content))
        has_change = bool(re.search(r'\bdef\s+change\b', content))
        has_up = bool(re.search(r'\bdef\s+up\b', content))

        if has_up and not has_down:
            warnings.append("Migration has 'up' method but no 'down' method. Add a 'down' method for rollback safety.")

        if has_change and not has_reversible:
            # Only the genuinely irreversible forms. ActiveRecord CAN invert `rename_column`,
            # a `remove_column` that carries its type, and a `drop_table` with a block — so
            # flagging those would be crying wolf on correct code.
            irreversible_ops = []
            if REMOVE_COLUMN_NO_TYPE.search(content):
                irreversible_ops.append("remove_column without a type argument")
            if re.search(r'\bchange_column\b', content):
                irreversible_ops.append("change_column (the old type is unknowable)")
            if DROP_TABLE_NO_BLOCK.search(content):
                irreversible_ops.append("drop_table without a block")
            if re.search(r'\bexecute\b', content):
                irreversible_ops.append("execute (raw SQL)")

            if irreversible_ops:
                warnings.append(
                    f"`change` cannot be reversed: {', '.join(irreversible_ops)}. "
                    "Pass the type (`remove_column :orders, :status, :string`), use a "
                    "`reversible do` block, or write explicit `up`/`down` — see the "
                    "`db-migration` skill. If it is genuinely irreversible, say so with "
                    "`raise ActiveRecord::IrreversibleMigration` in `down`."
                )

        # rename_column IS reversible — the risk is different, and so is the remedy.
        if re.search(r'\brename_column\b', content):
            warnings.append(
                "rename_column breaks every running instance the moment it lands: old code "
                "still selects the old name. It is reversible, so this is not a rollback "
                "problem — it is a rolling-deploy problem. Use expand/contract (add the new "
                "column, dual-write, backfill, switch reads, drop) — see the `db-migration` skill."
            )

    # Check 2: No raw SQL string interpolation
    sql_interpolation = re.findall(r'execute\s*[(\s]*["\'].*#\{.*\}.*["\']', content)
    if sql_interpolation:
        warnings.append(
            "Raw SQL with string interpolation detected. Use parameterized queries or "
            "ActiveRecord methods to prevent SQL injection per the `std-security` skill."
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
            "Follow expand/contract pattern per the `std-database` skill. Consider multi-step migration."
        )

    if warnings:
        hooklib.ask(
            "Migration validation warnings:\n"
            + "\n".join(f"- {w}" for w in warnings)
        )


if __name__ == "__main__":
    hooklib.run_pre_blocker(check, fail_closed=False, gate_label="migration-validator")
