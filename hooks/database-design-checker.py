#!/usr/bin/env python3
"""PostToolUse hook: database design checker.

A schema is the most expensive code to change later: a wrong relationship or a missing index is
fixed by migrating live rows under live traffic. So the design step gets a deterministic nudge,
and the two shapes that are cheap now and costly later get a warning.

Scope (wrapper-agnostic: `api/db/migrate/` counts the same as `db/migrate/`):
  Rails    db/migrate/*.rb, db/schema.rb, db/structure.sql, app/models/**/*.rb
  Django   migrations/**/*.py, models.py, a models/ package
  FastAPI  a models package (the house `app/models/`), alembic/versions/*.py
  SQL      any .sql file

Checks:
  1. Once per session, on the first in-scope edit: plan before writing more. First look up whether
     the concept already exists (the `orthogonality` skill's concept lookup), then relationships in
     Rails association terms, the query/index plan for the top queries, constraints, then the
     migration plan, then verify.
  2. Ruby: `has_and_belongs_to_many` -> use `has_many :through` a join model.
  3. Rails migrations: a foreign-key-shaped column left without an index. `add_column :t, :x_id`
     typed bigint/integer/uuid with no `add_index`/`t.index` leading with that column; or
     `t.references`/`t.belongs_to`/`add_reference`/`add_belongs_to` with `index: false` and no
     such index. LATER sibling migrations count, because the concurrent index is often its own
     file — and only a later migration can index a column this one adds.
  4. Python model files: SQLAlchemy `mapped_column(ForeignKey(...))` / `Column(ForeignKey(...))`
     with none of `index=True`, `unique=True`, `primary_key=True`, and no `Index`,
     `UniqueConstraint`, or `PrimaryKeyConstraint` in the file leading with that column.

Deliberately NOT checked:
  - Reversibility, raw-SQL interpolation, destructive operations: `migration-validator.py` owns
    them at PreToolUse, before the write lands. Saying it twice is noise.
  - A second table or model for a concept that already exists, a column copied from a parent, a
    repeating group, an EAV shape, JSONB keys queried as columns: `orthogonality-checker.py` finds
    those against the project's architecture index (DK1-DK4, MF3, MF5), and the `orthogonality`
    skill owns their declared exceptions. They need other files, which this checker never reads.
  - String `*_id` columns (`external_id`, `stripe_customer_id`): another system's identifiers,
    not foreign keys into this database.
  - `t.references`/`add_reference` without `index: false`: Rails indexes those by default.
  - Django `models.ForeignKey`: Django creates the index itself (`db_index` defaults to True).
  - Alembic revisions and Django migrations, for check 4: they are generated from the models, so
    the model is where the fix goes. Flagging both would warn twice about one defect.
  - Column helpers inside a table block (`t.bigint :customer_id`), and multi-line calls whose
    `index: false` sits on a continuation line.
  - Whether an index is the RIGHT one (column order, partial, covering): that needs the query
    plan, which a regex cannot see. The notice asks for that plan instead.
  - pytest modules (`test_*.py`, `*_test.py`, `conftest.py`), even inside a `models/` directory:
    `tests/models/test_order.py` is the `std-python` tests mirror of a model, not a model.
Returns no warnings for files outside the scope above."""

import os
import re

import _hooklib as hooklib

DB_EXTENSIONS = (".rb", ".py", ".sql")
NOTICE_KEY = "database-design"
RAILS_SCHEMA_TAILS = ("/db/schema.rb", "/db/structure.sql")
PY_MIGRATION_DIRS = ("migrations", "alembic/versions")
PY_TEST_FILE = re.compile(r"(?:^|/)(?:test_[^/]*|[^/]*_test|conftest)\.py$")
MAX_LATER_MIGRATIONS = 50

NOTICE = (
    "DATABASE DESIGN — plan the schema before writing more of it, per the `std-database` skill: "
    "(0) look up whether the concept already exists — the `orthogonality` skill's "
    "`arch_index.py --name <Entity>`; (1) the relationships, in Rails association terms (has_one/belongs_to, has_many, "
    "has_many :through, polymorphic, self-referential) or their Django/SQLAlchemy equivalents; "
    "(2) the query/index plan for the top queries this schema must serve; (3) the constraints; "
    "(4) then the migration plan (the `db-migration` skill); (5) verify. Shown once per session."
)

HABTM_WARNING = (
    "WARNING: `has_and_belongs_to_many` gives the join table no model — it cannot carry "
    "attributes (a role, a timestamp), validations, or callbacks, and adding one later means "
    "reshaping a live table that has no primary key. Use `has_many :through` a join model "
    "instead, per the `std-database` skill."
)

COMMENT_LINE = re.compile(r"^[ \t]*#.*$", re.M)

# --- Rails ------------------------------------------------------------------------------------
_NAME = r"""[:"']?(\w+)["']?"""
_COLUMNS = r"""(\[[^\]]*\]|%[iwIW]\[[^\]]*\]|[:"']\w+["']?)"""
HABTM = re.compile(r"\bhas_and_belongs_to_many\b")
ADD_COLUMN_FK = re.compile(
    r"\badd_column\s*\(?\s*" + _NAME + r"""\s*,\s*[:"']?(\w+_id)["']?"""
    r"""\s*,\s*[:"']?(?:bigint|integer|uuid)\b""")
T_REFERENCE = re.compile(r"\b(t\.(?:references|belongs_to))\s*\(?\s*" + _NAME + r"([^\n]*)")
ADD_REFERENCE = re.compile(
    r"\b(add_(?:reference|belongs_to))\s*\(?\s*" + _NAME + r"\s*,\s*" + _NAME + r"([^\n]*)")
ADD_INDEX = re.compile(r"\badd_index\s*\(?\s*" + _NAME + r"\s*,\s*" + _COLUMNS)
T_INDEX = re.compile(r"\bt\.index\s*\(?\s*" + _COLUMNS)
INDEX_FALSE = re.compile(r"\bindex:\s*false\b|:index\s*=>\s*false\b")

# --- SQLAlchemy -------------------------------------------------------------------------------
PARENS = {"(": 1, ")": -1}
PY_COLUMN_CALL = re.compile(r"\b(?:mapped_column|Column)\s*\(")
PY_FOREIGN_KEY = re.compile(r"\bForeignKey\s*\(")
PY_SELF_INDEXED = re.compile(r"\b(?:index|unique|primary_key)\s*=\s*True\b")
PY_INDEX_LEADS = re.compile(
    r"""\bIndex\s*\(\s*(?:["'][^"']*["']|None)\s*,\s*["']?(?:\w+\.)?(\w+)"""
    r"""|\b(?:UniqueConstraint|PrimaryKeyConstraint)\s*\(\s*["']?(?:\w+\.)?(\w+)""")
PY_NAMED_COLUMN = re.compile(r"""\s*["'](\w+)["']""")
PY_ASSIGN_TARGET = re.compile(r"(\w+)\s*(?::[^=\n]*)?=\s*(?:\w+\.)?$")


def fk_column_warning(sites):
    return (
        f"WARNING: foreign-key column added with no index — {', '.join(sites)}. PostgreSQL does "
        "not index foreign keys (and `add_foreign_key` does not create one), so every join or "
        "lookup on the column scans the table, as does every parent delete once a constraint "
        "exists. Use `add_reference` (indexed by default) or an `add_index` that leads with the "
        "column — concurrently on a large table (the `db-migration` skill). Per the "
        "`std-database` skill."
    )


def index_false_warning(sites):
    return (
        f"WARNING: `index: false` leaves a foreign key unindexed — {', '.join(sites)} — and no "
        "`add_index`/`t.index` in this migration or a sibling one leads with it. PostgreSQL does "
        "not index foreign keys on its own. Drop `index: false`, or add the index in its own "
        "concurrent migration (the `db-migration` skill). Per the `std-database` skill."
    )


def sqlalchemy_warning(names):
    return (
        f"WARNING: SQLAlchemy foreign key without an index — {', '.join(names)}. PostgreSQL does "
        "not index foreign keys and SQLAlchemy does not add one, so joins, lookups, and parent "
        "deletes scan the table. Pass `index=True` to the column, or lead a composite `Index` in "
        "`__table_args__` with it — per the `std-database` skill. (Django's `models.ForeignKey` "
        "indexes itself; this check is SQLAlchemy only.)"
    )


def strip_comment_lines(source):
    """Blank whole-line `#` comments (Ruby and Python), so commented-out code is not read."""
    return COMMENT_LINE.sub("", source)


def check_habtm(content):
    return [HABTM_WARNING] if HABTM.search(strip_comment_lines(content)) else []


def _first_column(columns):
    """`customer_id` from `:customer_id`, `[:customer_id, :created_at]`, or `%i[customer_id id]`."""
    found = re.search(r"[A-Za-z_]\w*", re.sub(r"^%[iwIW]", "", columns))
    return found.group(0) if found else None


def _index_leads(code):
    """(table or None, leading column) for every `add_index` and `t.index` in Ruby source."""
    leads = {(m.group(1), _first_column(m.group(2))) for m in ADD_INDEX.finditer(code)}
    return leads | {(None, _first_column(m.group(1))) for m in T_INDEX.finditer(code)}


def _sibling_index_leads(file_path):
    """Index leads declared by the migrations that run AFTER this one, nearest first.

    `CREATE INDEX CONCURRENTLY` cannot run in a transaction, and `disable_ddl_transaction!`
    applies to a whole file, so the `std-database` skill's advice is a one-statement migration of
    its own: `index: false` here, `add_index ..., algorithm: :concurrently` next door. Reading only
    this file would flag that correct form.

    Only a later migration can index a column this one adds, so earlier ones are not read. Reading
    every sibling cost a mature app one file open per migration on every migration edit — 3,000
    freshly checked-out migrations took 22s on Windows, past the dispatcher's 20s timeout, which
    discards every checker's output for the edit (0.6s once the files were warm)."""
    directory, name = os.path.split(os.path.abspath(file_path))
    try:
        later = sorted(n for n in os.listdir(directory) if n.endswith(".rb") and n > name)
    except OSError:
        return set()
    leads = set()
    for sibling in later[:MAX_LATER_MIGRATIONS]:
        leads |= _index_leads(strip_comment_lines(hooklib.read_file(os.path.join(directory, sibling))))
    return leads


def _is_indexed(leads, columns, table):
    """True when an index on `table` (None: table unknown, match any) leads with a column."""
    return any(column in columns and (table is None or lead_table in (None, table))
               for lead_table, column in leads)


def _unindexed_candidates(code):
    """(site, table or None, columns an index may lead with): bare FK columns, then opt-outs.

    A polymorphic reference is indexed on (`x_type`, `x_id`), so either column may lead."""
    bare = [(f"`add_column :{m.group(1)}, :{m.group(2)}`", m.group(1), {m.group(2)})
            for m in ADD_COLUMN_FK.finditer(code)]
    opted_out = [(f"`{m.group(1)} :{m.group(2)}`", None, {f"{m.group(2)}_id", f"{m.group(2)}_type"})
                 for m in T_REFERENCE.finditer(code) if INDEX_FALSE.search(m.group(3))]
    opted_out += [(f"`{m.group(1)} :{m.group(2)}, :{m.group(3)}`", m.group(2),
                   {f"{m.group(3)}_id", f"{m.group(3)}_type"})
                  for m in ADD_REFERENCE.finditer(code) if INDEX_FALSE.search(m.group(4))]
    return bare, opted_out


def check_rails_fk_index(content, file_path):
    """Foreign-key-shaped columns a migration adds with no index leading with them."""
    code = strip_comment_lines(content)
    bare, opted_out = _unindexed_candidates(code)
    if not bare and not opted_out:
        return []
    leads = _index_leads(code) | _sibling_index_leads(file_path)
    warnings = []
    for candidates, build in ((bare, fk_column_warning), (opted_out, index_false_warning)):
        missing = [site for site, table, cols in candidates if not _is_indexed(leads, cols, table)]
        if missing:
            warnings.append(build(missing))
    return warnings


def _call_args(content, open_paren):
    """Argument text of the call whose `(` sits at `open_paren`, balancing nested parentheses."""
    depth = 0
    for i in range(open_paren, len(content)):
        depth += PARENS.get(content[i], 0)
        if depth == 0:
            return content[open_paren + 1:i]
    return content[open_paren + 1:]


def _py_column_name(content, call_start, args):
    """The column a call declares: its leading string argument, else the assignment target."""
    named = PY_NAMED_COLUMN.match(args)
    if named:
        return named.group(1)
    line = content[content.rfind("\n", 0, call_start) + 1:call_start]
    target = PY_ASSIGN_TARGET.search(line)
    return target.group(1) if target else None


def check_sqlalchemy_fk_index(content):
    """SQLAlchemy `ForeignKey` columns declared with no index of any kind."""
    code = strip_comment_lines(content)
    covered = {a or b for a, b in PY_INDEX_LEADS.findall(code)}
    missing = []
    for m in PY_COLUMN_CALL.finditer(code):
        args = _call_args(code, m.end() - 1)
        if not PY_FOREIGN_KEY.search(args) or PY_SELF_INDEXED.search(args):
            continue
        name = _py_column_name(code, m.start(), args)
        if name not in covered:
            missing.append(f"`{name}`" if name else "an unnamed column")
    return [sqlalchemy_warning(missing)] if missing else []


def _is_python_model(norm):
    """Django `models.py`, or a models package (a Django app's, or the house FastAPI one)."""
    if hooklib.under_any(norm, PY_MIGRATION_DIRS):
        return False
    return os.path.basename(norm) == "models.py" or hooklib.under(norm, "models")


def classify(file_path):
    """'migration' | 'model-rb' | 'model-py' | 'schema' | None: which checks apply to the file."""
    norm = hooklib.normalize(file_path)
    ext = os.path.splitext(norm)[1]
    if ext not in DB_EXTENSIONS or (ext == ".py" and PY_TEST_FILE.search(norm)):
        return None
    if ext == ".rb" and hooklib.under(norm, "db/migrate"):
        return "migration"
    if ext == ".rb" and hooklib.under(norm, "app/models"):
        return "model-rb"
    if ext == ".py" and _is_python_model(norm):
        return "model-py"
    py_migration = ext == ".py" and hooklib.under_any(norm, PY_MIGRATION_DIRS)
    if ext == ".sql" or py_migration or ("/" + norm).endswith(RAILS_SCHEMA_TAILS):
        return "schema"
    return None


def check(event):
    file_path = hooklib.get_file_path(event)
    kind = classify(file_path) if file_path else None
    if kind is None:
        return []
    warnings = [NOTICE] if hooklib.first_in_session(event, NOTICE_KEY) else []
    content = hooklib.read_file(file_path)
    if file_path.endswith(".rb"):
        warnings.extend(check_habtm(content))
    if kind == "migration":
        warnings.extend(check_rails_fk_index(content, file_path))
    if kind == "model-py":
        warnings.extend(check_sqlalchemy_fk_index(content))
    return warnings


if __name__ == "__main__":
    hooklib.run_post_checker(check)
