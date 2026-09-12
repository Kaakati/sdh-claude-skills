#!/usr/bin/env python3
"""SQL DDL extraction for db/structure.sql and raw .sql files.

Comments, dollar-quoted bodies and string literals are blanked first (newlines kept, so offsets
still map to lines), then the text is split on `;`. Read per statement:
    CREATE [UNLOGGED|TEMP] TABLE t (...)      columns, inline REFERENCES, table constraints
    CREATE TABLE t PARTITION OF parent        kind "partition"
    ALTER TABLE t ADD [CONSTRAINT x] FOREIGN KEY (a[, b]) REFERENCES p   single or composite FK
    ALTER TABLE t ADD COLUMN c type           a column change ("alter" when t is defined elsewhere)
    CREATE [UNIQUE] INDEX ... ON t (cols) [WHERE ...]
    CREATE [MATERIALIZED] VIEW v              kind "view" / "matview" (column lists not expanded)
Triggers and functions are not interpreted.
"""
import re

import _archdup
import _archparse_db as db

_NOISE = re.compile(r"--[^\n]*|/\*.*?\*/|\$(\w*)\$.*?\$\1\$|'(?:''|[^'])*'", re.S)
_IDENT = r'(?:"?[\w$]+"?\.)?"?([\w$]+)"?'
CREATE_TABLE = re.compile(r"^\s*CREATE\s+(?:(?:GLOBAL|LOCAL)\s+)?(?:TEMP(?:ORARY)?\s+|UNLOGGED\s+)?TABLE\s+"
                          r"(?:IF\s+NOT\s+EXISTS\s+)?" + _IDENT, re.I)
CREATE_VIEW = re.compile(r"^\s*CREATE\s+(?:OR\s+REPLACE\s+)?(MATERIALIZED\s+)?VIEW\s+(?:IF\s+NOT\s+EXISTS\s+)?" + _IDENT, re.I)
CREATE_INDEX = re.compile(r"^\s*CREATE\s+(UNIQUE\s+)?INDEX\s+(?:CONCURRENTLY\s+)?(?:IF\s+NOT\s+EXISTS\s+)?"
                          r"(?:\S+\s+)?ON\s+(?:ONLY\s+)?" + _IDENT + r"(?:\s+USING\s+\w+)?\s*\(([^;]*?)\)\s*(WHERE)?", re.I | re.S)
ALTER_TABLE = re.compile(r"^\s*ALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:ONLY\s+)?" + _IDENT + r"\s+(.*)$", re.I | re.S)
FK_CLAUSE = re.compile(r"FOREIGN\s+KEY\s*\(([^)]*)\)\s*REFERENCES\s+" + _IDENT, re.I)
ADD_COLUMN = re.compile(r"\bADD\s+(?:COLUMN\s+)?(?:IF\s+NOT\s+EXISTS\s+)?(?!(?:CONSTRAINT|FOREIGN|PRIMARY|UNIQUE|CHECK|EXCLUDE)\b)"
                        r"\"?(\w+)\"?\s+(?!CONSTRAINT\b|FOREIGN\b)"
                        r"([A-Za-z][\w ]*?(?:\([^)]*\))?)(?=\s+(?:NOT|NULL|DEFAULT|REFERENCES|CONSTRAINT|PRIMARY|UNIQUE|CHECK|GENERATED)\b|\s*,|\s*$)", re.I)
PARTITION_OF = re.compile(r"\bPARTITION\s+OF\s+" + _IDENT, re.I)
INLINE_REF = re.compile(r"\bREFERENCES\s+" + _IDENT, re.I)
_CONSTRAINT_START = re.compile(r"^(?:CONSTRAINT|PRIMARY|UNIQUE|CHECK|FOREIGN|EXCLUDE|LIKE)\b", re.I)
_TYPE_END = re.compile(r"\s+(?:NOT\s+NULL|NULL|DEFAULT|REFERENCES|CONSTRAINT|PRIMARY|UNIQUE|CHECK|GENERATED|COLLATE)\b", re.I)


def blank_noise(text):
    return _NOISE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def statements(text):
    """(offset, statement) for each `;`-terminated statement of the blanked text."""
    clean = blank_noise(text)
    return [(m.start(), m.group(0)) for m in re.finditer(r"[^;]+", clean) if m.group(0).strip()]


def _paren_body(statement, start):
    open_at = statement.find("(", start)
    if open_at < 0:
        return None, 0
    depth = 0
    for i in range(open_at, len(statement)):
        depth += {"(": 1, ")": -1}.get(statement[i], 0)
        if depth == 0:
            return statement[open_at + 1:i], open_at + 1
    return statement[open_at + 1:], open_at + 1


def _constraint(table, item):
    fk = FK_CLAUSE.search(item)
    if fk:
        cols = re.findall(r"\w+", fk.group(1))
        _attach_fk(table, cols, fk.group(2))
        return
    unique = re.match(r"^(?:CONSTRAINT\s+\S+\s+)?UNIQUE\s*\(([^)]*)\)", item, re.I)
    if unique:
        table["indexes"].append({"columns": re.findall(r"\w+", unique.group(1)), "unique": True, "partial": False})


def _attach_fk(table, cols, parent):
    if len(cols) > 1:
        table["composite_fks"].append({"columns": cols, "parent": parent})
        return
    for entry in table["columns"]:
        if cols and entry["name"] == cols[0]:
            entry["fk_table"] = parent
            return
    if cols:
        table["columns"].append(db.column(cols[0], "bigint", table["line"], fk_table=parent, op="fk"))


def _column_item(table, item, line):
    match = re.match(r'^"?(\w+)"?\s+(.+)$', item, re.S)
    if not match:
        return
    rest = match.group(2)
    type_end = _TYPE_END.search(rest)
    type_name = rest[:type_end.start()] if type_end else rest
    ref = INLINE_REF.search(rest)
    table["columns"].append(db.column(match.group(1), type_name.strip(), line,
                                      fk_table=ref.group(1) if ref else None,
                                      nullable=False if re.search(r"\bNOT\s+NULL\b", rest, re.I) else None))


def _create_table(text, offset, statement, origin):
    name = CREATE_TABLE.match(statement)
    table = db.new_table(name.group(1), db.line_of(text, offset + name.start(1)), origin)
    partition = PARTITION_OF.search(statement)
    if partition:
        table["kind"] = "partition"
    body, body_at = _paren_body(statement, name.end())
    for item in db.split_args(body or ""):
        line = db.line_of(text, offset + body_at + max(0, (body or "").find(item)))
        if _CONSTRAINT_START.match(item):
            _constraint(table, item)
        else:
            _column_item(table, item, line)
    return table


def _alter(tables, text, offset, statement):
    match = ALTER_TABLE.match(statement)
    name = match.group(1)
    if name not in tables:
        tables[name] = db.new_table(name, db.line_of(text, offset + match.start(1)), "alter")
    table, actions = tables[name], match.group(2)
    for fk in FK_CLAUSE.finditer(actions):
        _attach_fk(table, re.findall(r"\w+", fk.group(1)), fk.group(2))
    for add in ADD_COLUMN.finditer(actions):
        table["columns"].append(db.column(add.group(1), add.group(2), db.line_of(text, offset + match.start(2) + add.start())))


def _index(tables, text, offset, statement):
    match = CREATE_INDEX.match(statement)
    name = match.group(2)
    if name not in tables:
        tables[name] = db.new_table(name, db.line_of(text, offset), "alter")
    columns = [c for c in (re.findall(r'"?(\w+)"?', part.strip())[:1] for part in db.split_args(match.group(3))) if c]
    tables[name]["indexes"].append({"columns": [c[0] for c in columns], "unique": bool(match.group(1)),
                                    "partial": bool(match.group(4))})


def parse_sql(text, origin="sql"):
    """Tables, views and their indexes/foreign keys from SQL DDL."""
    tables = {}
    for offset, statement in statements(text):
        if CREATE_TABLE.match(statement):
            table = _create_table(text, offset, statement, origin)
            previous = tables.get(table["name"])
            if previous and previous["origin"] == "alter":
                table["columns"].extend(previous["columns"])
                table["indexes"].extend(previous["indexes"])
            tables[table["name"]] = table
        elif CREATE_VIEW.match(statement):
            view = CREATE_VIEW.match(statement)
            kind = "matview" if view.group(1) else "view"
            tables[view.group(2)] = db.new_table(view.group(2), db.line_of(text, offset + view.start(2)), origin, kind)
        elif ALTER_TABLE.match(statement):
            _alter(tables, text, offset, statement)
        elif CREATE_INDEX.match(statement):
            _index(tables, text, offset, statement)
    for table in tables.values():
        for entry in table["columns"]:
            entry["family"] = entry["family"] or _archdup.column_family("")
    return list(tables.values())
