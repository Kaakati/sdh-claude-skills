#!/usr/bin/env python3
"""Which files the orthogonality index reads, and the one entry point that parses any of them.

`classify(rel)` names a file's kind from its project-relative path (wrapper-directory agnostic):
    manifest   Gemfile, package.json, pyproject.toml, requirements*.txt, config/importmap.rb, pnpm-workspace.yaml
    config     packwerk.yml, package.yml, package_todo.yml, .importlinter, setup.cfg, tach.toml,
               project.json, components.json, tsconfig*.json, jsconfig.json, .claude/orthogonality.json
    schema     db/schema.rb, db/structure.sql          migration  db/migrate/*.rb
    alembic    alembic/versions/*.py, migrations/versions/*.py
    pymigration  Django migrations/*.py (read for markers only; models are the source)
    model      app/models/**/*.rb, models.py, models/**/*.py
    sql, tf, source (.rb .py .ts .tsx .js .jsx)
`parse_text(rel, text, hints)` returns the facts dict every consumer shares (see `empty_facts`).
"""
import ast
import os
import re

import _archparse_db
import _archparse_js
import _archparse_manifest
import _archparse_py
import _archparse_pycode
import _archparse_rb
import _archparse_sql

SOURCE_EXTENSIONS = (".rb", ".py", ".ts", ".tsx", ".js", ".jsx", ".sql", ".tf")
CONFIG_BASENAMES = frozenset(("packwerk.yml", "package.yml", "package_todo.yml", ".importlinter", "setup.cfg",
                              "tach.toml", "project.json", "components.json", "tsconfig.json", "tsconfig.app.json",
                              "tsconfig.base.json", "jsconfig.json", "alembic.ini", ".jscpd.json",
                              ".dependency-cruiser.json", ".dependency-cruiser.js", ".dependency-cruiser.cjs"))
FACT_KEYS = ("tables", "models", "consts", "refs", "writes", "factories", "handlers", "pagination", "deps",
             "variants", "jsonb", "markers", "tf", "txns")
MARKER = re.compile(r"(?:#|//|--)\s*sdh:orthogonal-ok\b[ \t]*([A-Z]{2,}[0-9]*(?:-[A-Z0-9]+)*)?[ \t]*([^\n]*)")
JS_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")


def empty_facts():
    facts = {key: [] for key in FACT_KEYS}
    facts.update({"workspace_root": False, "errors": []})
    return facts


def _segments(rel):
    return "/" + rel.replace("\\", "/").strip("/")


def classify(rel):
    norm = _segments(rel)
    base, ext = os.path.basename(norm), os.path.splitext(norm)[1]
    if _archparse_manifest.is_manifest(norm):
        return "manifest"
    if base in CONFIG_BASENAMES or norm.endswith("/.claude/orthogonality.json") or re.match(r"tsconfig\.[\w.-]+\.json$", base):
        return "config"
    if norm.endswith(("/db/schema.rb", "/db/structure.sql")):
        return "schema"
    if ext == ".rb" and "/db/migrate/" in norm:
        return "migration"
    if ext == ".py" and re.search(r"/(?:alembic|migrations)/versions/", norm):
        return "alembic"
    if ext == ".py" and "/migrations/" in norm:
        return "pymigration"
    if (ext == ".rb" and "/app/models/" in norm) or (ext == ".py" and _archparse_py.is_python_model_path(norm)):
        return "model"
    if ext == ".sql":
        return "sql"
    if ext == ".tf":
        return "tf"
    return "source" if ext in SOURCE_EXTENSIONS else None


def language(rel):
    ext = os.path.splitext(rel)[1]
    return {".rb": "rb", ".py": "py", ".sql": "sql", ".tf": "tf"}.get(ext) or ("js" if ext in JS_EXTENSIONS else None)


def markers(text):
    found = []
    for match in MARKER.finditer(text):
        found.append({"line": text.count("\n", 0, match.start()) + 1, "detector": match.group(1) or "",
                      "reason": (match.group(2) or "").strip().rstrip("*/").strip()})
    return found


def _merge(facts, extra):
    for key, value in extra.items():
        if key in FACT_KEYS:
            facts[key].extend(value)


def _python(facts, rel, text, hints):
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError, MemoryError) as exc:
        facts["errors"].append("python parse: %s" % type(exc).__name__)
        return
    if classify(rel) == "alembic":
        facts["tables"].extend(_archparse_py.parse_alembic(tree))
        return
    tables, models = _archparse_py.parse_python_models(tree, rel)
    facts["tables"].extend(tables)
    facts["models"].extend(models)
    hints, columns = hints or {}, [c for t in tables for c in t["columns"]]
    json_fields = set(hints.get("json_fields") or ()) | {c["name"] for c in columns if c.get("family") == "json"}
    not_json = set(hints.get("not_json") or ()) | {c["name"] for c in columns if c.get("family") != "json"}
    not_json |= {name for model in models for name in model.get("relations") or ()}
    _merge(facts, _archparse_pycode.parse_python_code(tree, rel, json_fields, not_json))


def _schema_like(facts, rel, text, kind):
    if kind == "manifest":
        parsed = _archparse_manifest.parse_manifest(rel, text)
        facts["deps"], facts["workspace_root"] = parsed["deps"], parsed["workspace_root"]
        facts["errors"].extend(parsed["errors"])
    elif kind == "schema" and rel.endswith(".rb"):
        facts["tables"].extend(_archparse_db.parse_schema_rb(text))
    elif kind == "schema":
        facts["tables"].extend(_archparse_sql.parse_sql(text, "schema"))
    elif kind == "migration":
        facts["tables"].extend(_archparse_db.parse_rails_migration(text))
    elif kind == "sql":
        facts["tables"].extend(_archparse_sql.parse_sql(text, "sql"))
    elif kind == "tf":
        facts["tf"].extend(_archparse_js.parse_tf(text))


def parse_text(rel, text, hints=None):
    """Facts for one file. `hints` may carry {"json_fields": set, "not_json": set} known from the index."""
    facts = empty_facts()
    facts["markers"] = markers(text)
    kind = classify(rel)
    ext = os.path.splitext(rel)[1]
    if kind in ("manifest", "schema", "migration", "sql", "tf"):
        _schema_like(facts, rel, text, kind)
    elif kind in ("config", "pymigration", None):
        pass
    elif ext == ".rb":
        if kind == "model":
            facts["models"].extend(_archparse_db.parse_rails_models(text))
        _merge(facts, _archparse_rb.parse_ruby_code(text, rel))
    elif ext == ".py":
        _python(facts, rel, text, hints)
    elif ext in JS_EXTENSIONS:
        _merge(facts, _archparse_js.parse_js(text, rel))
    return facts
