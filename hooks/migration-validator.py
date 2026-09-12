#!/usr/bin/env python3
"""PreToolUse hook: Validates database migration files before they are written.

Checks:
1. Rails (`db/migrate`, multi-database `db/<name>_migrate`): an `up` without `down`, the genuinely
   irreversible forms inside `change`, rename_column's rolling-deploy risk
2. No raw SQL string interpolation (Ruby `#{}`; Python f-string, `%`, `+`, `.format()`)
3. Irreversible or destructive operations without the expand/contract pattern — for Alembic
   (`alembic/versions`) and Django (`migrations/`) too: destructive operations in the FORWARD
   direction, a `downgrade()` that does nothing, RunPython/RunSQL with no reverse. Rails is judged
   the same way: a `drop_table` in `def down` or a `reversible` block's `dir.down` undoes what the
   forward half created, so only `up`, `change` and top-level code are scanned for drops

It judges the file AS IT WILL BE after the write. For an Edit that is the file on disk with
old_string replaced: judging new_string alone asked "no down method" of an edit to a migration that
had one, and missed a `remove_column` added inside an existing `def change` — the canonical Rails
path (`rails g migration`, then Edit). Python migrations are parsed with `ast`, because Alembic's
`downgrade()` drops exactly what `upgrade()` created and only the forward half is destructive.

`database-design-checker.py` defers reversibility, raw-SQL interpolation and destructive operations
to this gate, so FastAPI and Django migrations get these checks here or nowhere.

Emits an 'ask' (confirmation) decision when warnings are found. Fails open: a
bug here must not block unrelated writes, so it uses the default run policy."""

import ast
import os
import re
import sys

import _hooklib as hooklib

# Wrapper-agnostic: segments, not a forced layout — backend/db/migrate, api/db/migrate, db/migrate
# at the root, svc/alembic/versions, billing/migrations all match.
MIGRATION_DIRS = ("migrations", "alembic/versions")

# `remove_column :t, :c` cannot be reversed — ActiveRecord does not know the type to restore.
# `remove_column :t, :c, :string` CAN. Match the 2-arg form only, or the hook fires on the
# exact form the migration guide recommends, and a gate that flags correct code is a gate
# people learn to ignore.
REMOVE_COLUMN_NO_TYPE = re.compile(
    r"\bremove_column\s+[:\"'][\w\"']+\s*,\s*[:\"'][\w\"']+\s*(?:\)|$|#)", re.M
)
# `drop_table :t` is irreversible; `drop_table :t do |t| ... end` is reversible.
DROP_TABLE_NO_BLOCK = re.compile(r"\bdrop_table\s+[:\"'][\w\"']+\s*(?!.*\bdo\b)(?:\)|$|#)", re.M)

_ALEMBIC_DROPS = ("drop_table", "drop_column", "drop_index", "drop_constraint")
_DJANGO_REMOVALS = ("DeleteModel", "RemoveField", "RemoveIndex", "RemoveConstraint")
_SQL_CALLS = ("execute", "exec_driver_sql", "RunSQL", "text")
_DESTRUCTIVE_SQL = re.compile(r"\b(?:DROP\s+(?:TABLE|COLUMN|INDEX|SCHEMA|DATABASE)|TRUNCATE)\b", re.I)
_PYTHON_DROPS = re.compile(
    r"\bop\.(drop_(?:table|column|index|constraint))\s*\(|\bmigrations\.(DeleteModel|RemoveField|RemoveIndex|RemoveConstraint)\b")

_UP_WITHOUT_DOWN = "Migration has 'up' method but no 'down' method. Add a 'down' method for rollback safety."
# rename_column IS reversible — the risk is different, and so is the remedy.
_RENAME_COLUMN = (
    "rename_column breaks every running instance the moment it lands: old code "
    "still selects the old name. It is reversible, so this is not a rollback "
    "problem — it is a rolling-deploy problem. Use expand/contract (add the new "
    "column, dual-write, backfill, switch reads, drop) — see the `db-migration` skill."
)
_RUBY_INTERPOLATION = (
    "Raw SQL with string interpolation detected. Use parameterized queries or "
    "ActiveRecord methods to prevent SQL injection per the `std-security` skill."
)
_PYTHON_INTERPOLATION = (
    "Raw SQL built with an f-string, `%`, `+` or `.format()` detected. Use bound parameters "
    "(`sa.text(sql).bindparams(...)`, `RunSQL(sql, params)`, `cursor.execute(sql, params)`) to "
    "prevent SQL injection per the `std-security` skill."
)
_EMPTY_DOWNGRADE = (
    "`downgrade()` does nothing (`pass` or `raise NotImplementedError`), so `alembic downgrade` "
    "cannot undo this revision. Write the reverse operations — see the `std-fastapi` skill. If the "
    "revision is genuinely irreversible, approve this and keep a `raise` that says why."
)
_NO_REVERSE = (
    "`{}` has no reverse, so migrating back past it fails. Pass `reverse_code=` / `reverse_sql=` "
    "(`migrations.RunPython.noop` when there is nothing to undo) — see the `std-django` skill."
)


def _is_migration(path):
    norm = hooklib.normalize(path)
    if hooklib.under_any(norm, MIGRATION_DIRS):
        return True
    return any(part == "migrate" or part.endswith("_migrate") for part in norm.split("/")[:-1])


def _post_write_text(event, file_path):
    """The file as it will be after this write: Write's content, or the edits applied to disk."""
    data, tool = hooklib.tool_input(event), hooklib.tool_name(event)
    if tool == "Write":
        return data.get("content", "") or ""
    base = event.get("cwd") or ""
    text = hooklib.read_file(file_path if os.path.isabs(file_path) else os.path.join(base, file_path))
    for edit in (data.get("edits") if tool == "MultiEdit" else [data]) or []:
        if isinstance(edit, dict):
            text = _apply_edit(text, edit)
    return text


def _apply_edit(text, edit):
    old, new = edit.get("old_string", "") or "", edit.get("new_string", "") or ""
    if old and old in text:
        return text.replace(old, new) if edit.get("replace_all") else text.replace(old, new, 1)
    # Nothing on disk to apply it to (a new file, or a stale old_string): judge both.
    return text + "\n" + new if text else new


def _destructive_message(ops):
    return (
        f"Destructive operations detected: {', '.join(ops)}. "
        "Follow expand/contract pattern per the `std-database` skill. Consider multi-step migration."
    )


def _irreversible_in_change(content):
    """Only the genuinely irreversible forms. ActiveRecord CAN invert `rename_column`, a
    `remove_column` that carries its type, and a `drop_table` with a block — so flagging those
    would be crying wolf on correct code."""
    if not re.search(r'\bdef\s+change\b', content) or re.search(r'\breversible\s+do\b', content):
        return []
    found = []
    if REMOVE_COLUMN_NO_TYPE.search(content):
        found.append("remove_column without a type argument")
    if re.search(r'\bchange_column\b', content):
        found.append("change_column (the old type is unknowable)")
    if DROP_TABLE_NO_BLOCK.search(content):
        found.append("drop_table without a block")
    if re.search(r'\bexecute\b', content):
        found.append("execute (raw SQL)")
    return found


def _ruby_warnings(content):
    warnings = []
    if re.search(r'\bdef\s+up\b', content) and not re.search(r'\bdef\s+down\b', content):
        warnings.append(_UP_WITHOUT_DOWN)
    irreversible = _irreversible_in_change(content)
    if irreversible:
        warnings.append(
            f"`change` cannot be reversed: {', '.join(irreversible)}. "
            "Pass the type (`remove_column :orders, :status, :string`), use a "
            "`reversible do` block, or write explicit `up`/`down` — see the "
            "`db-migration` skill. If it is genuinely irreversible, say so with "
            "`raise ActiveRecord::IrreversibleMigration` in `down`."
        )
    if re.search(r'\brename_column\b', content):
        warnings.append(_RENAME_COLUMN)
    if re.findall(r'execute\s*[(\s]*["\'].*#\{.*\}.*["\']', content):
        warnings.append(_RUBY_INTERPOLATION)
    return warnings


def _sql_destructive_warnings(content):
    ops = [label for pattern, label in ((r'\bdrop_table\b', "drop_table"), (r'(?i)\btruncate\b', "TRUNCATE"),
                                        (r'(?i)\bDROP\s+INDEX\b', "DROP INDEX")) if re.search(pattern, content)]
    return [_destructive_message(ops)] if ops else []


# --- Python (Alembic / Django), via ast --------------------------------------------------------

def _call_name(node):
    """`op.drop_table(...)` -> 'drop_table'; `RunSQL(...)` -> 'RunSQL'; '' for anything else."""
    if not isinstance(node, ast.Call):
        return ""
    return node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")


def _string(node):
    """The literal text of a string node (f-string literal parts included), else ''."""
    if isinstance(node, ast.JoinedStr):
        return "".join(_string(value) for value in node.values)
    if sys.version_info >= (3, 8):
        return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else ""
    return node.s if isinstance(node, ast.Str) else ""  # Python 3.6 / 3.7


def _function(tree, name):
    return next((node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name), None)


def _sql_argument(call):
    if call.args:
        return call.args[0]
    return next((keyword.value for keyword in call.keywords if keyword.arg in ("sql", "statement")), None)


def _is_empty(function):
    """Only `pass`, a docstring, or `raise NotImplementedError`."""
    for statement in function.body:
        docstring = isinstance(statement, ast.Expr) and bool(_string(statement.value))
        raises = isinstance(statement, ast.Raise) and "NotImplementedError" in ast.dump(statement)
        if not (isinstance(statement, ast.Pass) or docstring or raises):
            return False
    return True


def _python_destructive(tree):
    """Destructive operations in the FORWARD direction: Alembic's `upgrade()` (its `downgrade()`
    drops what `upgrade()` created, which is the point) and Django's operations."""
    upgrade, found = _function(tree, "upgrade"), set()
    for node in ast.walk(upgrade or tree):
        name = _call_name(node)
        if name in _ALEMBIC_DROPS and upgrade is not None:
            found.add("op." + name)
        elif name in _DJANGO_REMOVALS:
            found.add("migrations." + name)
        elif name in _SQL_CALLS and _DESTRUCTIVE_SQL.search(_string(_sql_argument(node))):
            found.add(name + "(DROP/TRUNCATE)")
    return sorted(found)


def _python_irreversible(tree):
    reasons = set()
    upgrade, downgrade = _function(tree, "upgrade"), _function(tree, "downgrade")
    if upgrade is not None and downgrade is not None and not _is_empty(upgrade) and _is_empty(downgrade):
        reasons.add(_EMPTY_DOWNGRADE)
    for node in ast.walk(tree):
        name = _call_name(node)
        if name not in ("RunPython", "RunSQL"):
            continue
        if len(node.args) < 2 and not any(keyword.arg in ("reverse_code", "reverse_sql") for keyword in node.keywords):
            reasons.add(_NO_REVERSE.format(name))
    return sorted(reasons)


def _is_interpolated(node):
    """An f-string with a placeholder, `"..." % x`, `"..." + x`, or `"...".format(x)`."""
    if isinstance(node, ast.JoinedStr):
        return any(isinstance(value, ast.FormattedValue) for value in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mod, ast.Add)):
        return bool(_string(node.left) or _string(node.right))
    return _call_name(node) == "format" and bool(_string(getattr(node.func, "value", None)))


def _python_warnings(content):
    try:
        tree = ast.parse(content)
    except (SyntaxError, ValueError):  # a partial file: fall back to the destructive calls by name
        drops = sorted({op or model for op, model in _PYTHON_DROPS.findall(content)})
        return [_destructive_message(drops)] if drops else []
    drops = _python_destructive(tree)
    warnings = [_destructive_message(drops)] if drops else []
    warnings.extend(_python_irreversible(tree))
    if any(_call_name(node) in _SQL_CALLS and _is_interpolated(_sql_argument(node)) for node in ast.walk(tree)):
        warnings.append(_PYTHON_INTERPOLATION)
    return warnings


# --- Rails: the rollback direction ---------------------------------------------------------------

# Where the rollback half starts: `def down` (or `def self.down`), or `dir.down do` in `reversible`.
_ROLLBACK_START = re.compile(r"^([ \t]*)(?:def[ \t]+(?:self\.)?down\b|\w+\.down[ \t]+do\b)")
# A rollback half that opens and closes on one line: `def down; drop_table :t; end`, an endless
# `def down = drop_table(:t)`, `dir.down { execute "DROP INDEX ..." }`, `dir.down do ... end`.
_ROLLBACK_ONE_LINE = re.compile(
    r"\bdef[ \t]+(?:self\.)?down\b(?:[ \t]*;[^\n]*?;[ \t]*end\b|[ \t]*(?:\(\))?[ \t]*=[^\n]*)"
    r"|\b\w+\.down[ \t]*(?:\{(?:[^{}\n]|#\{[^{}\n]*\})*\}|do\b[^\n]*?\bend\b)")


def _forward_ruby(content):
    """The migration without its rollback direction: `def down` bodies (to the `end` at their own
    indentation) and `dir.down` blocks. A drop there undoes what the forward half created — the
    reason the Python path judges only Alembic's `upgrade()`. A forward `drop_table`, block or not,
    still asks."""
    kept, closing = [], None
    for line in _ROLLBACK_ONE_LINE.sub("", content).split("\n"):
        if closing is not None:
            if re.match(re.escape(closing) + r"end\b", line):
                closing = None
            continue
        start = _ROLLBACK_START.match(line)
        if start:
            closing = start.group(1)
            continue
        kept.append(line)
    return "\n".join(kept)


def check(event):
    if hooklib.tool_name(event) not in ("Write", "Edit", "MultiEdit"):
        return

    file_path = hooklib.get_file_path(event)
    if not _is_migration(file_path):
        return

    content = _post_write_text(event, file_path)
    if file_path.endswith(".py"):
        warnings = _python_warnings(content)
    elif file_path.endswith(".rb"):
        warnings = _ruby_warnings(content) + _sql_destructive_warnings(_forward_ruby(content))
    else:
        warnings = _sql_destructive_warnings(content)

    if warnings:
        hooklib.ask(
            "Migration validation warnings:\n"
            + "\n".join(f"- {w}" for w in warnings)
        )


if __name__ == "__main__":
    hooklib.run_pre_blocker(check, fail_closed=False, gate_label="migration-validator")
