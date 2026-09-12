#!/usr/bin/env python3
"""Subject and candidate tables for the duplicated-knowledge detectors (DK1-DK4, MF3).

Edit mode loads only the tables that can matter for the edited file: its own tables (a migration's
change to a table another file declares is merged onto that table first), tables whose normalized
name, near-name or synonym matches, tables sharing three or more column names, and FK parents. A
5,000-table schema therefore costs a handful of indexed lookups per edit, not a full load.
Scan mode loads every merged table and blocks candidate pairs by name keys (DK1) or shared column
keys (DK2); a column key shared by more than COMMON_KEY_LIMIT tables carries no signal and is not
used for blocking (it still counts in the Jaccard value).
"""
import copy

import _archdup
import _archrules
import _archview

COMMON_KEY_LIMIT = 100


def keys(table):
    if "_keys" not in table:
        table["_keys"] = _archdup.column_keys(table["columns"])
    return table["_keys"]


def facts_table(view, table, delta, base):
    """A detector-shaped table for one table of the edited file."""
    columns = [_archview.column_dict(dict(c, family=c.get("family"))) for c in table["columns"]]
    if table["origin"] == "alter" and table["name"] in base:
        merged = copy.deepcopy(base[table["name"]])
        merged.pop("_keys", None)
        for column in columns:
            _archview.apply_column(merged, column)
        merged.update(path=delta["path"], line=table["line"], origin="alter", file_id=delta.get("file_id"),
                      delta_columns=[c["name"] for c in columns])
        return merged
    row = {"id": None, "file_id": delta.get("file_id"), "name": table["name"], "context": delta["context"],
           "deployable": delta["deployable"], "line": table["line"], "origin": table["origin"], "kind": table["kind"],
           "read_model": table.get("read_model"), "extra": {"concept": table.get("concept"), "indexes": table.get("indexes"),
                                                             "composite_fks": table.get("composite_fks")}}
    built = _archview.table_dict(row, columns, delta["path"])
    models = view.rows("models", {"deployable": delta["deployable"], "tbl": table["name"]})
    return view.place_table(built, next((m for m in models if m["file_id"] != delta.get("file_id")), None))


def model_subjects(view, delta, base, mine):
    """Name-only subjects for models whose table no schema, migration or model file declares yet."""
    names = {t["name"] for t in mine}
    subjects = []
    for model in delta["facts"]["models"]:
        if model.get("abstract") or model.get("proxy") or model.get("sti_parent") or not model.get("table"):
            continue
        if model["table"] not in names and model["table"] not in base:
            row = {"name": model["table"], "context": delta["context"], "deployable": delta["deployable"],
                   "line": model["line"], "origin": "model", "kind": "table", "extra": {"concept": model["symbol"]}}
            subjects.append(view.place_table(_archview.table_dict(row, [], delta["path"])))
    return subjects


def _parent_names(tables):
    names = set()
    for table in tables:
        for column in table["columns"]:
            name = column["name"].lower()
            names |= {column["fk_table"]} if column.get("fk_table") else ({_archdup.pluralize(name[:-3])} if name.endswith("_id") else set())
    return names


def candidate_names(view, delta, mine):
    """Table names in the deployable that could pair with the edited file's tables."""
    deployable, words = delta["deployable"], set()
    for table in mine:
        own = {table["norm"], table["near"], _archdup.normalize_name(table.get("concept") or table["name"])[0]}
        words |= own | {word for group in view.groups if own & group for word in group}
    names = {r["name"] for key in ("norm", "near") for r in view.select("tables", {"deployable": deployable, key: sorted(words)}, ["name"])}
    wanted = sorted({c["name"] for t in mine for c in t["columns"] if c["name"].lower() not in _archdup.INFRA_COLUMNS})
    counts = {}
    for row in view.select("columns", {"name": wanted}, ["table_id", "name"]) if wanted else []:
        counts.setdefault(row["table_id"], set()).add(row["name"])
    ids = [i for i, found in counts.items() if len(found) >= 3]
    names |= {r["name"] for r in view.select("tables", {"id": ids, "deployable": deployable}, ["name"])} if ids else set()
    return names | _parent_names(mine)


def _edit_subjects(view, delta):
    deployable, exclude = delta["deployable"], delta.get("file_id")
    own = {t["name"] for t in delta["facts"]["tables"]} | {m.get("table") for m in delta["facts"]["models"]}
    base = view.tables_named(deployable, own, exclude)
    mine = []
    for table in (t for t in delta["facts"]["tables"] if t.get("kind") != "dropped"):
        if _archrules.out_of_time(view):
            break
        mine.append(facts_table(view, table, delta, base))
    mine += model_subjects(view, delta, base, mine)
    others = view.tables_named(deployable, candidate_names(view, delta, mine) | set(base), exclude)
    names = {m["name"] for m in mine}
    return mine, [t for n, t in others.items() if n not in names] + mine


def edit_subjects(view, delta):
    """(subject tables, pool they are compared with) for one edited file, computed once per check."""
    return view.cached(("edit-subjects", delta["path"]), lambda: _edit_subjects(view, delta))


def scan_tables(view):
    return view.cached("scan-tables", lambda: [t for dep in view.deployables() for t in view.tables(dep).values()])


def subjects(view, delta):
    """(subject tables, pool or None). A None pool means: use the subject's whole deployable."""
    return edit_subjects(view, delta) if delta is not None else (scan_tables(view), None)


def _name_keys(table, groups):
    own = {table["norm"], table["near"]}
    return own | {"syn:%d" % i for i, group in enumerate(groups) if own & group}


def _bucket_pairs(bucket):
    pairs = {}
    for i, a in enumerate(bucket):
        pairs.update({tuple(sorted((a["name"], b["name"]))) + (a["deployable"],): (a, b) for b in bucket[i + 1:]})
    return pairs


def name_pairs(view, tables):
    buckets, pairs = {}, {}
    for table in tables:
        for key in _name_keys(table, view.groups):
            buckets.setdefault((table["deployable"], key), []).append(table)
    for bucket in buckets.values():
        pairs.update(_bucket_pairs(bucket))
    return list(pairs.values())


def column_pairs(tables):
    buckets, counts = {}, {}
    for table in tables:
        for key in (k for k in keys(table) if not k.startswith("fk:")):
            buckets.setdefault((table["deployable"], key), []).append(table)
    for bucket in (b for b in buckets.values() if len(b) <= COMMON_KEY_LIMIT):
        for pair, (a, b) in _bucket_pairs(bucket).items():
            counts[pair] = (counts.get(pair, (0, a, b))[0] + 1, a, b)
    return [(a, b) for n, a, b in counts.values() if n >= 3]


def pairs(view, delta, mode):
    """(a, b) table pairs to compare: subject x pool in edit mode, yielded lazily so a detector stops at its
    deadline even when the edited file declares thousands of tables; blocked pairs in scan mode."""
    if delta is not None:
        mine, pool = edit_subjects(view, delta)
        return ((a, b) for a in mine for b in pool if b is not a)
    tables = scan_tables(view)
    return name_pairs(view, tables) if mode == "name" else column_pairs(tables)
