#!/usr/bin/env python3
"""Python model extraction through `ast`: Django models, SQLAlchemy declarative models and `Table()`
objects, and Alembic `op.create_table` revisions.

Django: `models.Model` subclasses (or subclasses of one in the same file), fields ending in
`Field` plus ForeignKey/OneToOneField (column `<name>_id`), `Meta.db_table`, `managed = False`
(a read model), `abstract = True` (fields inherited, no table), `proxy = True` (no table), and
`Meta.indexes` / `constraints`. The concept name is the class name, since the default table carries
the app label. Relation names (ForeignKey, OneToOneField and ManyToManyField fields, `related_name` and
`related_query_name`, or the default reverse query name) are recorded, so a lookup through a relation is
never read as a JSON key (MF5). SQLAlchemy: classes with `__tablename__`, `mapped_column` / `Column`
(type from the first argument or the `Mapped[...]` annotation), `ForeignKey("parents.id")`,
`__abstract__`, column mixins from the same file, and `__table_args__` `info={"read_model": True}`.
Imperative `registry.map_imperatively` mappings are not read.
"""
import ast
import os

import _archdup

_DJANGO_BASES = ("models.Model", "Model", "django.db.models.Model", "gis_models.Model")
_DJANGO_RELATIONS = ("ForeignKey", "OneToOneField")
_ANNOTATION_FAMILIES = {"int": "int", "str": "text", "bool": "bool", "datetime": "time", "date": "time",
                        "time": "time", "Decimal": "decimal", "float": "decimal", "dict": "json", "list": "json",
                        "UUID": "uuid", "Any": "other"}


def const_value(node):
    """The literal value of a Constant/Str/Num/NameConstant node, else None (3.6 through 3.14)."""
    kind = type(node).__name__
    if kind in ("Constant", "NameConstant"):
        return node.value
    if kind == "Str":
        return node.s
    if kind == "Num":
        return node.n
    return None


def subscript_key(node):
    """The index expression of a Subscript (3.9+ holds it directly; 3.6-3.8 wrap it in ast.Index)."""
    inner = node.slice
    return inner.value if type(inner).__name__ == "Index" else inner


def dotted(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def call_name(node):
    return dotted(node.func).split(".")[-1] if isinstance(node, ast.Call) else ""


def kwarg(call, name):
    for item in getattr(call, "keywords", []) or []:
        if item.arg == name:
            return item.value
    return None


def string_list(node):
    items = getattr(node, "elts", None) or []
    return [const_value(i) for i in items if isinstance(const_value(i), str)]


def _assignments(classdef):
    """(target name, value node, annotation or None, line) for simple class-body assignments."""
    for stmt in classdef.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            yield stmt.targets[0].id, stmt.value, None, stmt.lineno
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            yield stmt.target.id, stmt.value, stmt.annotation, stmt.lineno


def _meta(classdef):
    for stmt in classdef.body:
        if isinstance(stmt, ast.ClassDef) and stmt.name == "Meta":
            return {name: value for name, value, _, _ in _assignments(stmt)}
    return {}


def app_label(rel):
    parts = rel.replace("\\", "/").split("/")
    if "models" in parts[:-1]:
        index = parts.index("models")
        return parts[index - 1] if index > 0 else "app"
    return parts[-2] if len(parts) >= 2 else "app"


def _django_field(name, call, line):
    kind = call_name(call)
    if kind in _DJANGO_RELATIONS:
        target = call.args[0] if call.args else kwarg(call, "to")
        label = const_value(target) if const_value(target) is not None else dotted(target)
        column_name = const_value(kwarg(call, "db_column")) or name + "_id"
        return {"name": column_name, "family": "int", "fk_model": str(label or ""), "fk_table": None,
                "nullable": None, "op": "add", "line": line}
    if not kind.endswith("Field") or kind in ("ManyToManyField",):
        return None
    return {"name": const_value(kwarg(call, "db_column")) or name, "family": _archdup.column_family(kind),
            "fk_table": None, "nullable": None, "op": "add", "line": line}


def _django_relations(classdef):
    """Names a lookup traverses through this model's relations: each relation field, its `related_name` and
    `related_query_name`, or, with neither set, the default reverse query name (the lowercased model name)."""
    names = []
    for name, value, _, _ in _assignments(classdef):
        if not isinstance(value, ast.Call) or call_name(value) not in _DJANGO_RELATIONS + ("ManyToManyField",):
            continue
        given = [const_value(kwarg(value, key)) for key in ("related_name", "related_query_name")]
        given = [n for n in given if isinstance(n, str)]
        names += [name] + [n for n in given if not n.endswith("+")] + ([] if given else [classdef.name.lower()])
    return names


def _django_indexes(meta):
    indexes = []
    for key in ("indexes", "constraints"):
        for item in getattr(meta.get(key), "elts", None) or []:
            fields = string_list(kwarg(item, "fields")) if isinstance(item, ast.Call) else []
            if fields:
                indexes.append({"columns": fields, "unique": call_name(item) == "UniqueConstraint", "partial": False})
    for group in getattr(meta.get("unique_together"), "elts", None) or []:
        indexes.append({"columns": string_list(group), "unique": True, "partial": False})
    return indexes


def _django_model(classdef, rel, known):
    meta = _meta(classdef)
    columns = _inherited(classdef, known)
    for name, value, _, line in _assignments(classdef):
        if isinstance(value, ast.Call):
            field = _django_field(name, value, line)
            if field:
                columns.append(field)
    parents = [known[b] for b in _base_names(classdef) if known.get(b, {}).get("framework") == "django"]
    relations = {n for parent in parents for n in parent.get("relations") or []} | set(_django_relations(classdef))
    table = const_value(meta.get("db_table")) or "%s_%s" % (app_label(rel), classdef.name.lower())
    return {"symbol": classdef.name, "table": table, "line": classdef.lineno, "framework": "django",
            "abstract": const_value(meta.get("abstract")) is True, "proxy": const_value(meta.get("proxy")) is True,
            "managed": const_value(meta.get("managed")) is not False, "sti_parent": None,
            "columns": columns, "indexes": _django_indexes(meta), "relations": sorted(relations)}


def _annotation_family(annotation):
    text = dotted(annotation) if annotation is not None else ""
    if isinstance(annotation, ast.Subscript):
        inner = subscript_key(annotation)
        text = dotted(inner) or dotted(getattr(inner, "elts", [None])[0] if getattr(inner, "elts", None) else None)
    return _ANNOTATION_FAMILIES.get(text.split(".")[-1], "other") if text else "other"


def _sqla_column(name, call, annotation, line):
    kind = call_name(call)
    if kind not in ("mapped_column", "Column"):
        return None
    args = list(call.args)
    if args and isinstance(const_value(args[0]), str):
        name, args = const_value(args[0]), args[1:]
    fk = next((a for a in args if call_name(a) == "ForeignKey"), None)
    target = const_value(fk.args[0]) if fk is not None and fk.args else None
    typed = next((a for a in args if call_name(a) != "ForeignKey"), None)
    family = _archdup.column_family(dotted(getattr(typed, "func", typed)) if typed is not None else "")
    if family == "other":
        family = _annotation_family(annotation)
    return {"name": name, "family": "int" if target and family == "other" else family,
            "fk_table": str(target).split(".")[0] if isinstance(target, str) else None,
            "nullable": None, "op": "add", "line": line}


def _sqla_columns(classdef):
    columns = []
    for name, value, annotation, line in _assignments(classdef):
        if isinstance(value, ast.Call):
            column = _sqla_column(name, value, annotation, line)
            if column:
                columns.append(column)
    return columns


def _read_model_args(value):
    text = ast.dump(value) if value is not None else ""
    return "read_model" in text


def _sqla_model(classdef, inherited):
    body = {name: value for name, value, _, _ in _assignments(classdef)}
    return {"symbol": classdef.name, "table": const_value(body.get("__tablename__")), "line": classdef.lineno,
            "framework": "sqlalchemy", "abstract": const_value(body.get("__abstract__")) is True, "proxy": False,
            "managed": not _read_model_args(body.get("__table_args__")), "sti_parent": None,
            "columns": list(inherited) + _sqla_columns(classdef), "indexes": []}


def _base_names(classdef):
    return [dotted(base) for base in classdef.bases]


def _classify_class(classdef, known):
    bases = _base_names(classdef)
    body = {name for name, _, _, _ in _assignments(classdef)}
    if any(b in _DJANGO_BASES for b in bases) or any(known.get(b, {}).get("framework") == "django" for b in bases):
        return "django"
    if "__tablename__" in body or any(known.get(b, {}).get("framework") == "sqlalchemy" for b in bases):
        return "sqlalchemy"
    return "mixin" if any(isinstance(v, ast.Call) and call_name(v) in ("mapped_column", "Column")
                          for _, v, _, _ in _assignments(classdef)) else None


def _inherited(classdef, known):
    columns = []
    for base in _base_names(classdef):
        parent = known.get(base)
        if parent and (parent.get("abstract") or parent.get("framework") == "mixin"):
            columns.extend(parent["columns"])
    return columns


def _resolve_django_fks(models, rel):
    tables = {m["symbol"]: m["table"] for m in models}
    for model in models:
        for column in model["columns"]:
            label = column.pop("fk_model", None)
            if label:
                name = label.split(".")[-1]
                app = label.split(".")[0] if "." in label and not label.startswith("settings") else app_label(rel)
                column["fk_table"] = tables.get(name) or "%s_%s" % (app, name.lower())


def parse_python_models(tree, rel):
    """(tables, models) declared by the module's ORM classes and Table() objects."""
    known, models = {}, []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        kind = _classify_class(node, known)
        if kind == "django":
            known[node.name] = _django_model(node, rel, known)
        elif kind == "sqlalchemy":
            known[node.name] = _sqla_model(node, _inherited(node, known))
        elif kind == "mixin":
            known[node.name] = {"framework": "mixin", "columns": _sqla_columns(node)}
        if kind in ("django", "sqlalchemy"):
            models.append(known[node.name])
    _resolve_django_fks([m for m in models if m["framework"] == "django"], rel)
    tables = [model_table(m) for m in models if m["table"] and not m["abstract"] and not m["proxy"]]
    return tables + _imperative_tables(tree), models


def model_table(model):
    return {"name": model["table"], "concept": model["symbol"] if model["framework"] == "django" else None,
            "line": model["line"], "origin": "model", "kind": "table", "columns": model["columns"],
            "indexes": model.get("indexes") or [], "composite_fks": [], "read_model": not model["managed"],
            "relations": model.get("relations") or []}


def _table_call(call, origin):
    if not call.args or not isinstance(const_value(call.args[0]), str):
        return None
    table = {"name": const_value(call.args[0]), "concept": None, "line": call.lineno, "origin": origin,
             "kind": "table", "columns": [], "indexes": [], "composite_fks": [], "read_model": False}
    for arg in call.args[1:]:
        column = _sqla_column(None, arg, None, getattr(arg, "lineno", call.lineno)) if isinstance(arg, ast.Call) else None
        if column and column["name"]:
            table["columns"].append(column)
    return table


def _imperative_tables(tree):
    tables = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and call_name(node) == "Table" and dotted(node.func) in ("Table", "sa.Table", "sqlalchemy.Table"):
            table = _table_call(node, "model")
            if table:
                tables.append(table)
    return tables


def parse_alembic(tree):
    """Tables an Alembic revision creates with op.create_table (used only when no model maps them)."""
    tables = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and dotted(node.func) == "op.create_table":
            table = _table_call(node, "alembic")
            if table:
                tables.append(table)
    return tables


def is_python_model_path(rel):
    norm = rel.replace("\\", "/")
    return os.path.basename(norm) == "models.py" or "/models/" in "/" + norm
