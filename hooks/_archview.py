#!/usr/bin/env python3
"""A read model over the orthogonality index for the detectors, loaded lazily and cached for one
check or one scan.

Tables are merged per deployable: schema files (db/schema.rb, structure.sql) and ORM models first,
raw SQL next, migrations replayed in file order only when the deployable has no schema file, and
Alembic `create_table` only for a table no model declares. A table's context is its declared owner
(`.claude/orthogonality.json` tables), else the context of the model file mapping it, else the
context of the file declaring it. The view never writes.
"""
import json
import os
import posixpath
import re

import _archcontexts
import _archdup
import _archgraph
import _hookpaths

ORIGIN_RANK = {"schema": 0, "model": 1, "sql": 2, "migration": 3, "alter": 3, "alembic": 4}
FILE_COLUMNS = ["id", "path", "kind", "lang", "framework", "deployable", "context"]
_REGISTRY = {}


def registry():
    """The mechanism registry, `hooks/_mechanisms.json`."""
    if "data" not in _REGISTRY:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_mechanisms.json"), encoding="utf-8") as handle:
            _REGISTRY["data"] = json.load(handle)
    return _REGISTRY["data"]


def column_dict(row):
    return {"name": row["name"], "family": row.get("family") or "other", "fk_table": row.get("fk_table"),
            "nullable": row.get("nullable"), "op": row.get("op") or "add", "line": row.get("line")}


def table_dict(row, columns, path):
    extra = json.loads(row.get("extra") or "{}") if isinstance(row.get("extra"), str) else (row.get("extra") or {})
    return {"id": row.get("id"), "file_id": row.get("file_id"), "name": row["name"], "concept": extra.get("concept"),
            "context": row.get("context"), "declared": False, "deployable": row.get("deployable"), "path": path,
            "line": row.get("line") or 1, "origin": row["origin"], "kind": row.get("kind") or "table",
            "read_model": bool(row.get("read_model")), "model": None,
            "columns": [c for c in columns if c["op"] in ("add", "fk")],
            "indexes": list(extra.get("indexes") or []), "composite_fks": list(extra.get("composite_fks") or [])}


def apply_column(table, column):
    """Apply one migration column change (add, fk, remove, rename:<new>) to a merged table."""
    op, name = column["op"], column["name"]
    if op == "remove":
        table["columns"] = [c for c in table["columns"] if c["name"] != name]
    elif op.startswith("rename:"):
        for existing in (c for c in table["columns"] if c["name"] == name):
            existing["name"] = op.split(":", 1)[1]
    elif op == "fk" and any(c["name"] == name for c in table["columns"]):
        for existing in (c for c in table["columns"] if c["name"] == name):
            existing["fk_table"] = column["fk_table"]
    else:
        table["columns"] = [c for c in table["columns"] if c["name"] != name] + [dict(column, op="add")]


def _replay(merged, row, columns, path):
    name = row["name"]
    if row.get("kind") == "dropped":
        merged.pop(name, None)
        return
    if row["origin"] == "migration" or name not in merged:
        merged[name] = table_dict(dict(row, origin="migration"), [] if row["origin"] == "alter" else columns, path)
        if row["origin"] == "migration":
            return
    for column in columns:
        apply_column(merged[name], column)
    merged[name]["indexes"] += table_dict(row, [], path)["indexes"]


def migration_version(path):
    """A Rails migration's version from its file name, padded to 14 digits (0 when it has none)."""
    match = re.match(r"(\d{8,14})", posixpath.basename(path or ""))
    return int(match.group(1).ljust(14, "0")) if match else 0


def merge_tables(rows, columns, paths, schema_version="auto"):
    """{table name: merged table} for one deployable's table rows. Migrations replay on top of the schema file
    only when newer than the version it records (every migration when the deployable has no schema file)."""
    if schema_version == "auto":
        schema_version = 0 if any(r["origin"] == "schema" for r in rows) else None
    ordered = sorted(rows, key=lambda r: (ORIGIN_RANK.get(r["origin"], 3), paths.get(r["file_id"], ""), r["line"] or 0))
    merged = {}
    for row in ordered:
        cols = [column_dict(c) for c in columns.get(row["id"], [])]
        path = paths.get(row["file_id"], "")
        if row["origin"] in ("migration", "alter"):
            if schema_version is None or (schema_version > 0 and migration_version(path) > schema_version):
                _replay(merged, row, cols, path)
        elif row.get("kind") != "dropped":
            merged.setdefault(row["name"], table_dict(row, cols, path))
    return merged


class IndexView(object):
    def __init__(self, store, root, config=None):
        self.store, self.root, self.config = store, root, config or {}
        stored = store.get_meta("context_decl") if store is not None else None
        self.cmap = _archcontexts.with_config(json.loads(stored) if stored else None, self.config)
        self.groups = _archdup.synonym_groups((self.config.get("concepts") or {}).get("synonyms") or ())
        self.prefixes = tuple(item["name"] for item in self.cmap["items"].values())
        self._memo, self._files = {}, {}

    def cached(self, key, build):
        if key not in self._memo:
            self._memo[key] = build()
        return self._memo[key]

    def registry(self):
        return registry()

    def select(self, table, where=None, columns=None, distinct=False):
        return self.store.select(table, where, columns, distinct) if self.store is not None else []

    def file_rows(self, ids):
        wanted = {i for i in ids if i is not None}
        missing = [i for i in wanted if i not in self._files]
        for row in self.select("files", {"id": missing}, FILE_COLUMNS) if missing else []:
            self._files[row["id"]] = row
        return {i: self._files[i] for i in wanted if i in self._files}

    def file_by_path(self, rel):
        rows = self.select("files", {"path": rel}, FILE_COLUMNS)
        for row in rows:
            self._files[row["id"]] = row
        return rows[0] if rows else None

    def all_files(self):
        return self.cached("all_files", lambda: [self._files.setdefault(r["id"], r) for r in self.select("files", None, FILE_COLUMNS)])

    def deployables(self):
        return sorted({r["deployable"] for r in self.select("files", None, ["deployable"], distinct=True)})

    def with_paths(self, rows):
        files = self.file_rows([r.get("file_id") for r in rows])
        for row in rows:
            row["path"] = files.get(row.get("file_id"), {}).get("path", "")
        return rows

    def rows(self, table, where=None):
        return self.with_paths(self.select(table, where))

    def models(self, deployable):
        return self.cached(("models", deployable), lambda: self.rows("models", {"deployable": deployable}))

    def tables(self, deployable, exclude_file=None):
        return self.cached(("tables", deployable, exclude_file), lambda: self._load_tables(deployable, exclude_file, None))

    def tables_named(self, deployable, names, exclude_file=None):
        """Merged tables for just `names`: every origin row of those names, so replay stays correct."""
        wanted = tuple(sorted({n for n in names if n}))
        if not wanted:
            return {}
        return self.cached(("named", deployable, exclude_file, wanted), lambda: self._load_tables(deployable, exclude_file, wanted))

    def schema_version(self, deployable):
        """None without a schema file; else the newest migration version it records (0 when it records none)."""
        def build():
            rows = self.select("files", {"deployable": deployable, "kind": "schema"}, ["path"])
            if not rows:
                return None
            texts, versions = (getattr(self, "options", None) or {}).get("texts") or {}, []
            for row in rows:
                text = texts[row["path"]] if row["path"] in texts else _hookpaths._read_text(os.path.join(self.root, row["path"]))
                versions += [int((a or b).replace("_", "").ljust(14, "0")) for a, b in re.findall(r"version:\s*([\d_]{8,17})|\('(\d{14})'\)", text)]
            return max(versions) if versions else 0
        return self.cached(("schema-version", deployable), build)

    def _load_tables(self, deployable, exclude_file, names):
        where = {"deployable": deployable} if names is None else {"deployable": deployable, "name": list(names)}
        rows = [r for r in self.select("tables", where) if r["file_id"] != exclude_file]
        columns = {}
        for column in self.select("columns", {"table_id": [r["id"] for r in rows]}) if rows else []:
            columns.setdefault(column["table_id"], []).append(column)
        paths = {i: f["path"] for i, f in self.file_rows([r["file_id"] for r in rows]).items()}
        merged = merge_tables(rows, columns, paths, self.schema_version(deployable))
        models = self.models(deployable) if names is None else self.rows("models", {"deployable": deployable, "tbl": list(names)})
        by_table = {}
        for model in (m for m in models if m["file_id"] != exclude_file):
            by_table.setdefault(model["tbl"], model)
        for table in merged.values():
            self.place_table(table, by_table.get(table["name"]))
        return merged

    def place_table(self, table, model=None):
        """Set a table's context (owner, then mapping model, then declaring file) and declared flag."""
        owner = _archcontexts.owner_of_table(self.cmap, table["name"])
        table["model"] = model or table.get("model")
        table["context"] = owner or (table["model"]["context"] if table["model"] else table["context"])
        table["declared"] = bool(owner) or _archcontexts.is_declared(self.cmap, table["context"])
        norm = _archdup.normalize_name(table.get("concept") or table["name"], self.prefixes if table["declared"] else ())
        table["norm"], table["near"] = norm
        return table

    def markers(self, rel, delta=None):
        if delta is not None and delta.get("path") == rel:
            return delta["facts"]["markers"]
        row = self.file_by_path(rel)
        return self.select("markers", {"file_id": row["id"]}) if row else []

    def context_edges(self, exclude_file=None):
        """{(src context, dst context): example file id} over non-type-only resolved refs."""
        def build():
            edges = {}
            for row in self.select("refs", {"type_only": 0}, ["src_context", "dst_context", "file_id"], distinct=True):
                if row["file_id"] != exclude_file and row["dst_context"] and row["src_context"] != row["dst_context"]:
                    edges.setdefault((row["src_context"], row["dst_context"]), row["file_id"])
            return edges
        return self.cached(("edges", exclude_file), build)

    def edge_example(self, src, dst, file_id):
        rows = self.select("refs", {"file_id": file_id, "src_context": src, "dst_context": dst, "type_only": 0}, ["line"])
        path = self.file_rows([file_id]).get(file_id, {}).get("path", "")
        return path, min([r["line"] for r in rows] or [0])

    def resolve(self, ref, src_rel, deployable):
        """(dst path, dst context) for one parsed ref, looked up in the index; (None, None) if unresolved."""
        if ref["lang"] == "rb":
            names = _archgraph.ruby_candidates(ref["symbol"], ref.get("scope"))
            by_symbol = {r["symbol"]: r["file_id"] for r in self.select("consts", {"symbol": names}, ["symbol", "file_id"])}
            hit = next((by_symbol[n] for n in names if n in by_symbol), None)
            row = self.file_rows([hit]).get(hit)
        else:
            candidates = (_archgraph.python_candidates(ref["symbol"], src_rel, deployable) if ref["lang"] == "py"
                          else _archgraph.js_candidates(ref["symbol"], src_rel, self.root, deployable))
            found = {r["path"]: r for r in self.select("files", {"path": candidates}, FILE_COLUMNS)} if candidates else {}
            row = next((found[c] for c in candidates if c in found), None)
        return (row["path"], row["context"]) if row else (None, None)

    def json_field_names(self):
        """Every column name the index knows as a JSON column (the MF5 confidence hint for Python)."""
        return self.cached("json_fields", lambda: {r["name"] for r in self.select("columns", {"family": "json"}, ["name"], distinct=True)})

    def not_json_names(self):
        """Names a Django lookup can start with that are not JSON columns: ORM models' relation names and
        related_name values, and their plain columns (the MF5 exclusion for Python)."""
        def build():
            tables = self.select("tables", {"origin": "model"}, ["id", "extra"])
            names = set()
            for row in tables:
                extra = json.loads(row.get("extra") or "{}") if isinstance(row.get("extra"), str) else (row.get("extra") or {})
                names |= set(extra.get("relations") or [])
            columns = self.select("columns", {"table_id": [t["id"] for t in tables]}, ["name", "family"]) if tables else []
            return (names | {c["name"] for c in columns if c.get("family") != "json"}) - self.json_field_names()
        return self.cached("not_json", build)

    def baseline(self):
        return self.cached("baseline", lambda: {r["fingerprint"]: r for r in self.select("findings_baseline")})

    def meta(self, key, default=None):
        return self.store.get_meta(key, default) if self.store is not None else default
