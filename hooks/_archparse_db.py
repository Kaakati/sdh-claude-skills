#!/usr/bin/env python3
"""Rails schema extraction: db/schema.rb, migrations (replayed when no schema file exists), and
Active Record model classes.

A table is {"name", "line", "origin", "kind", "columns", "indexes", "composite_fks", "read_model"};
a column is {"name", "family", "fk_table", "nullable", "op", "line"}; an index is
{"columns", "unique", "partial"}. `origin` is "schema" for db/schema.rb, "migration" for a
create_table in a migration and "alter" for a migration change to a table it did not create;
`op` is "add", "remove" or "rename:<new>" and is applied in migration order by the replay.

Regex per statement, not a Ruby parser: `create_table` blocks end at the `end` on the opener's
indentation (the formatter's layout), and dynamic table names are not seen.
"""
import bisect
import re

import _archdup

_NAME = r"""[:"']?([\w.]+)["']?"""
_COLUMNS = r"""(\[[^\]]*\]|%[iwIW]\[[^\]]*\]|[:"'][\w]+["']?)"""
CREATE_TABLE = re.compile(r"^([ \t]*)create_table\s*\(?\s*" + _NAME + r"([^\n]*)", re.M)
CHANGE_TABLE = re.compile(r"^([ \t]*)change_table\s*\(?\s*" + _NAME + r"([^\n]*)", re.M)
T_CALL = re.compile(r"^\s*t\.(\w+)\s*\(?\s*([^\n]*)$")
ADD_COLUMN = re.compile(r"^\s*add_column\s*\(?\s*" + _NAME + r"\s*,\s*" + _NAME + r"\s*,\s*" + _NAME + r"([^\n]*)", re.M)
REMOVE_COLUMN = re.compile(r"^\s*remove_column\s*\(?\s*" + _NAME + r"\s*,\s*" + _NAME, re.M)
RENAME_COLUMN = re.compile(r"^\s*rename_column\s*\(?\s*" + _NAME + r"\s*,\s*" + _NAME + r"\s*,\s*" + _NAME, re.M)
ADD_REFERENCE = re.compile(r"^\s*add_(?:reference|belongs_to)\s*\(?\s*" + _NAME + r"\s*,\s*" + _NAME + r"([^\n]*)", re.M)
ADD_INDEX = re.compile(r"^\s*add_index\s*\(?\s*" + _NAME + r"\s*,\s*" + _COLUMNS + r"([^\n]*)", re.M)
ADD_FK = re.compile(r"^\s*add_foreign_key\s*\(?\s*" + _NAME + r"\s*,\s*" + _NAME + r"([^\n]*)", re.M)
DROP_TABLE = re.compile(r"^\s*drop_table\s*\(?\s*" + _NAME, re.M)
CREATE_VIEW = re.compile(r"^\s*create_view\s*\(?\s*" + _NAME + r"([^\n]*)", re.M)
_ARG_NAME = re.compile(r"""^[:"']([\w]+)["']?$""")
_OPTION = re.compile(r"\b(\w+):\s*([^,]+)")
_FK_TARGET = re.compile(r"""to_table:\s*[:"']?(\w+)""")
_FK_COLUMN = re.compile(r"""column:\s*(\[[^\]]*\]|[:"']\w+["']?)""")
CLASS_LINE = re.compile(r"^([ \t]*)class\s+([A-Z][\w:]*)\s*(?:<\s*([A-Z][\w:]*))?", re.M)
MODULE_LINE = re.compile(r"^([ \t]*)module\s+([A-Z][\w:]*)", re.M)
TABLE_NAME = re.compile(r"""self\.table_name\s*=\s*["']([\w.]+)["']""")
ABSTRACT = re.compile(r"self\.abstract_class\s*=\s*true")
AR_BASES = ("ApplicationRecord", "ActiveRecord::Base", "Base")
NON_COLUMN_CALLS = ("index", "check_constraint", "remove_index", "foreign_key", "remove_foreign_key", "change_default",
                    "change_null", "remove_check_constraint", "exclusion_constraint", "unique_constraint")


_LINES = [None, []]


def line_of(text, offset):
    """1-based line of `offset`; the newline index is built once per text, so a 5,000-table schema stays linear."""
    if _LINES[0] is not text:
        _LINES[0], _LINES[1] = text, [m.start() for m in re.finditer("\n", text)]
    return bisect.bisect_left(_LINES[1], offset) + 1


def url_host(url):
    """`host[:port]`, lowercased, from a URL or its authority. Userinfo (`user:pass@`), path, query and fragment
    are dropped: a credential in a base URL never reaches the index or a finding, and `user@host` and `host`
    name one upstream. Shared by the JS, Python and Ruby client-factory parsers."""
    text = str(url or "").split("://", 1)[-1]
    for mark in "/?#":
        text = text.split(mark, 1)[0]
    return text.rsplit("@", 1)[-1].lower()


def bare(name):
    return str(name or "").split(".")[-1]


def split_args(args):
    """Top-level comma split of a call's argument text (brackets and braces kept whole)."""
    parts, depth, start = [], 0, 0
    for i, ch in enumerate(args):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(args[start:i].strip())
            start = i + 1
    parts.append(args[start:].strip())
    return [p for p in parts if p]


def names_in(columns_text):
    return re.findall(r"\w+", re.sub(r"^%[iwIW]", "", columns_text))


def new_table(name, line, origin, kind="table"):
    return {"name": bare(name), "line": line, "origin": origin, "kind": kind, "columns": [], "indexes": [],
            "composite_fks": [], "read_model": kind in ("view", "matview")}


def column(name, type_name, line, **extra):
    entry = {"name": name, "family": _archdup.column_family(type_name), "fk_table": None,
             "nullable": None, "op": "add", "line": line}
    entry.update(extra)
    return entry


def _reference_columns(names, rest, line):
    options = dict(_OPTION.findall(rest))
    target = _FK_TARGET.search(rest)
    polymorphic = "true" in options.get("polymorphic", "")
    columns = []
    for name in names:
        fk = None if polymorphic else bare(target.group(1)) if target else _archdup.pluralize(name)
        columns.append(column(name + "_id", options.get("type", "bigint"), line, fk_table=fk))
        if polymorphic:
            columns.append(column(name + "_type", "string", line))
    return columns


def t_call_columns(method, args, line):
    """Columns one `t.<method> ...` line adds (or removes/renames) inside a table block."""
    parts = split_args(args.rstrip(") "))
    names = [m.group(1) for m in (_ARG_NAME.match(p) for p in parts) if m]
    rest = ", ".join(p for p in parts if not _ARG_NAME.match(p))
    if method == "timestamps":
        return [column("created_at", "datetime", line), column("updated_at", "datetime", line)]
    if method in ("references", "belongs_to"):
        return _reference_columns(names, rest, line)
    if method == "remove":
        return [column(n, "", line, op="remove") for n in names]
    if method == "rename" and len(names) >= 2:
        return [column(names[0], "", line, op="rename:" + names[1])]
    if method == "column" and len(names) >= 2:
        names, method = names[:1], names[1]
    if method in NON_COLUMN_CALLS or method.startswith("remove_"):
        return []
    nullable = False if re.search(r"\bnull:\s*false", rest) else None
    return [column(n, method, line, nullable=nullable) for n in names]


def index_entry(columns_text, rest):
    return {"columns": names_in(columns_text), "unique": bool(re.search(r"\bunique:\s*true", rest)),
            "partial": bool(re.search(r"\bwhere:", rest))}


def _block_lines(text, match):
    """(line number, line) pairs inside the block opened by `match`, up to its `end`."""
    indent = match.group(1)
    closer = re.compile(r"^" + re.escape(indent) + r"end\b", re.M)
    end = closer.search(text, match.end())
    body = text[match.end():end.start() if end else len(text)]
    first = line_of(text, match.end())
    return [(first + i, raw) for i, raw in enumerate(body.split("\n"))]


def fill_block(table, text, match):
    for number, raw in _block_lines(text, match):
        call = T_CALL.match(raw)
        if not call:
            continue
        if call.group(1) == "index":
            cols = re.match(r"\s*" + _COLUMNS + r"(.*)$", call.group(2))
            if cols:
                table["indexes"].append(index_entry(cols.group(1), cols.group(2)))
            continue
        table["columns"].extend(t_call_columns(call.group(1), call.group(2), number))


def _target(tables, name, text_offset, text):
    """The table `name` defined in this file, else a new `alter` entry for it."""
    key = bare(name)
    if key not in tables:
        tables[key] = new_table(key, line_of(text, text_offset), "alter")
    return tables[key]


def _apply_foreign_key(tables, match, text):
    child, rest = _target(tables, match.group(1), match.start(), text), match.group(3)
    parent = bare(match.group(2))
    named = _FK_COLUMN.search(rest)
    cols = names_in(named.group(1)) if named else [_archdup.singular(parent) + "_id"]
    if len(cols) > 1:
        child["composite_fks"].append({"columns": cols, "parent": parent})
        return
    for entry in child["columns"]:
        if entry["name"] == cols[0]:
            entry["fk_table"] = parent
            return
    child["columns"].append(column(cols[0], "bigint", line_of(text, match.start()), fk_table=parent, op="fk"))


def _statements(tables, text):
    for match in ADD_COLUMN.finditer(text):
        _target(tables, match.group(1), match.start(), text)["columns"].append(
            column(match.group(2), match.group(3), line_of(text, match.start()),
                   nullable=False if re.search(r"\bnull:\s*false", match.group(4)) else None))
    for match in REMOVE_COLUMN.finditer(text):
        _target(tables, match.group(1), match.start(), text)["columns"].append(
            column(match.group(2), "", line_of(text, match.start()), op="remove"))
    for match in RENAME_COLUMN.finditer(text):
        _target(tables, match.group(1), match.start(), text)["columns"].append(
            column(match.group(2), "", line_of(text, match.start()), op="rename:" + match.group(3)))
    for match in ADD_REFERENCE.finditer(text):
        _target(tables, match.group(1), match.start(), text)["columns"].extend(
            _reference_columns([match.group(2)], match.group(3), line_of(text, match.start())))
    for match in ADD_INDEX.finditer(text):
        _target(tables, match.group(1), match.start(), text)["indexes"].append(index_entry(match.group(2), match.group(3)))
    for match in ADD_FK.finditer(text):
        _apply_foreign_key(tables, match, text)


def parse_schema_rb(text, origin="schema"):
    """Tables from db/schema.rb (origin "schema") or one migration (origin "migration")."""
    tables = {}
    for match in CREATE_TABLE.finditer(text):
        table = new_table(match.group(2), line_of(text, match.start()), origin)
        fill_block(table, text, match)
        tables[table["name"]] = table
    for match in CHANGE_TABLE.finditer(text):
        fill_block(_target(tables, match.group(2), match.start(), text), text, match)
    _statements(tables, text)
    for match in CREATE_VIEW.finditer(text):
        kind = "matview" if re.search(r"materialized:\s*true", match.group(2)) else "view"
        tables[bare(match.group(1))] = new_table(match.group(1), line_of(text, match.start()), origin, kind)
    for match in DROP_TABLE.finditer(text):
        tables.setdefault(bare(match.group(1)), new_table(match.group(1), line_of(text, match.start()), "alter"))["kind"] = "dropped"
    return list(tables.values())


def parse_rails_migration(text):
    return parse_schema_rb(text, origin="migration")


def _class_spans(text):
    """(fully qualified name, parent, line, body) per class, with namespaces from indentation."""
    heads = sorted([(m.start(), len(m.group(1)), m.group(2), m.group(3), "class") for m in CLASS_LINE.finditer(text)]
                   + [(m.start(), len(m.group(1)), m.group(2), None, "module") for m in MODULE_LINE.finditer(text)])
    stack, spans = [], []
    for index, (offset, indent, name, parent, kind) in enumerate(heads):
        while stack and stack[-1][0] >= indent:
            stack.pop()
        qualified = "::".join([s[1] for s in stack] + [name])
        stack.append((indent, name))
        if kind == "class":
            end = heads[index + 1][0] if index + 1 < len(heads) else len(text)
            spans.append((qualified, parent, line_of(text, offset), text[offset:end]))
    return spans


def parse_rails_models(text):
    """Active Record classes: symbol, table (explicit or conventional), abstract, STI parent."""
    models = []
    for symbol, parent, line, body in _class_spans(text):
        if not parent:
            continue
        explicit = TABLE_NAME.search(body)
        table = bare(explicit.group(1)) if explicit else _archdup.pluralize(_archdup.snake(symbol.split("::")[-1]))
        models.append({"symbol": symbol, "table": table, "line": line, "abstract": bool(ABSTRACT.search(body)),
                       "sti_parent": None if parent in AR_BASES else parent, "proxy": False,
                       "framework": "rails", "columns": []})
    return models
