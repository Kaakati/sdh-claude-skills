#!/usr/bin/env python3
"""Python code facts through `ast`, for the boundary and mechanism detectors.

    refs        import / from-import targets; `if TYPE_CHECKING:` bodies are type-only
    writes      Django `Model.objects.create/update/delete/...`, `Model(...).save()`,
                SQLAlchemy `session.add(Model(...))`, `insert(Model)`, `update(Model)`, `delete(Model)`
    handlers    FastAPI `@app.exception_handler(Exception)` / `add_exception_handler(Exception, ...)`,
                DRF `REST_FRAMEWORK["EXCEPTION_HANDLER"]` and views overriding `handle_exception`
    factories   `httpx.Client(base_url=...)` / `httpx.AsyncClient(...)`
    pagination  DRF pagination classes, route parameters named cursor / offset / page
    jsonb       Django `filter(<json field>__<key>=...)` and SQLAlchemy `col["k"].astext`
    txns        `with transaction.atomic():`, `with session.begin():`, `@transaction.atomic`
    variants    token code (`jwt.encode/decode`) and service style (module functions vs classes)
Dynamic imports (`importlib`) and string-built queries are not seen.
"""
import ast
import os

from _archparse_db import url_host
from _archparse_py import call_name, const_value, dotted, subscript_key

WRITE_OPS = ("create", "bulk_create", "update", "delete", "get_or_create", "update_or_create", "bulk_update")
SQLA_WRITES = ("insert", "update", "delete")
JSON_FIELD_NAMES = frozenset(("data", "metadata", "meta", "payload", "attributes", "properties", "extra", "settings",
                              "details", "document", "config", "preferences", "options", "json", "raw"))
LOOKUPS = frozenset(("exact", "iexact", "contains", "icontains", "in", "gt", "gte", "lt", "lte", "startswith",
                     "istartswith", "endswith", "iendswith", "range", "isnull", "regex", "iregex", "has_key",
                     "has_keys", "has_any_keys", "contained_by", "len", "date", "year", "month", "day", "id", "pk"))
AS_TEXT = ("astext", "as_string", "as_integer", "as_float", "as_boolean", "as_numeric")
PAGINATION_CLASSES = {"LimitOffsetPagination": "limit-offset", "CursorPagination": "cursor",
                      "PageNumberPagination": "page-number"}
ROUTE_PARAMS = {"cursor": "cursor", "offset": "limit-offset", "page": "page-number"}


def _is_type_checking(test):
    return dotted(test).split(".")[-1] == "TYPE_CHECKING"


def _children(node, type_only):
    if isinstance(node, ast.If) and _is_type_checking(node.test):
        return [(c, True) for c in node.body] + [(c, type_only) for c in node.orelse]
    return [(c, type_only) for c in ast.iter_child_nodes(node)]


def walk(tree):
    """(node, type_only) for every node, iteratively (deep files cannot hit the recursion limit)."""
    stack = [(tree, False)]
    while stack:
        node, type_only = stack.pop()
        yield node, type_only
        stack.extend(_children(node, type_only))


def _import_refs(node, type_only):
    if isinstance(node, ast.Import):
        return [{"line": node.lineno, "symbol": a.name, "scope": "", "lang": "py", "type_only": type_only}
                for a in node.names]
    prefix = "." * (node.level or 0) + (node.module or "")
    return [{"line": node.lineno, "symbol": "%s:%s" % (prefix, a.name), "scope": "", "lang": "py",
             "type_only": type_only} for a in node.names if a.name != "*"]


def _objects_model(node):
    while isinstance(node, (ast.Call, ast.Attribute)):
        if isinstance(node, ast.Attribute) and node.attr == "objects" and isinstance(node.value, ast.Name):
            return node.value.id
        node = node.func if isinstance(node, ast.Call) else node.value
    return None


def _write(call):
    """(model symbol, op) for an ORM write call, else None."""
    func = call.func
    if isinstance(func, ast.Attribute) and func.attr in WRITE_OPS:
        model = _objects_model(func.value)
        if model:
            return model, func.attr
    if isinstance(func, ast.Attribute) and func.attr == "save" and call_name(func.value)[:1].isupper():
        return call_name(func.value), "save"
    if isinstance(func, ast.Attribute) and func.attr == "add" and dotted(func.value).endswith("session") and call.args:
        name = call_name(call.args[0])
        return (name, "add") if name[:1].isupper() else None
    if isinstance(func, ast.Name) and func.id in SQLA_WRITES and call.args and isinstance(call.args[0], ast.Name):
        return (call.args[0].id, func.id) if call.args[0].id[:1].isupper() else None
    return None


def _factory_target(call):
    base = next((k.value for k in call.keywords if k.arg == "base_url"), None)
    if base is None:
        return ""
    literal = const_value(base)
    if isinstance(literal, str):
        return "host:" + url_host(literal)
    if isinstance(base, ast.Subscript) or call_name(base) in ("getenv", "get"):
        inner = subscript_key(base) if isinstance(base, ast.Subscript) else (base.args or [None])[0]
        return "env:%s" % const_value(inner) if const_value(inner) else ""
    return "attr:" + dotted(base) if dotted(base) else ""


def _json_keys(call, known):
    """(field, key, confidence) per lookup on a JSON field. `known` = (names known to be JSON columns, names known
    not to be: relations, related_name values and plain columns). A JSON-ish name neither set holds is a guess."""
    json_fields, not_json = known
    names = [k.arg for k in call.keywords if k.arg] + [const_value(a) for a in call.args if isinstance(const_value(a), str)]
    found = []
    for name in names:
        parts = name.lstrip("-").split("__")
        if len(parts) < 2 or parts[1] in LOOKUPS:
            continue
        if parts[0] in json_fields:
            found.append((parts[0], parts[1], "high"))
        elif parts[0] in JSON_FIELD_NAMES and parts[0] not in not_json:
            found.append((parts[0], parts[1], "medium"))
    return found


def _sqla_json_keys(call):
    found = []
    for node in ast.walk(call):
        if isinstance(node, ast.Attribute) and node.attr in AS_TEXT and isinstance(node.value, ast.Subscript):
            key = const_value(subscript_key(node.value))
            field = dotted(node.value.value).split(".")[-1]
            if isinstance(key, str) and field:
                found.append((field, key, "high"))
    return found


def _call_facts(call, facts, known):
    write = _write(call)
    if write:
        facts["writes"].append({"line": call.lineno, "symbol": write[0], "op": write[1], "table": None})
    name, text = call_name(call), dotted(call.func)
    if name == "add_exception_handler" and call.args and dotted(call.args[0]) == "Exception":
        facts["handlers"].append({"line": call.lineno, "kind": "fastapi-global", "exception": "Exception"})
    if text in ("httpx.Client", "httpx.AsyncClient"):
        facts["factories"].append({"line": call.lineno, "kind": text, "target": _factory_target(call)})
    if name in ("filter", "exclude", "get", "order_by"):
        keys = _json_keys(call, known)
        keys += _sqla_json_keys(call) if not keys else []
        facts["jsonb"].extend({"line": call.lineno, "field": f, "key": k, "confidence": c} for f, k, c in keys)
    elif name == "where":
        facts["jsonb"].extend({"line": call.lineno, "field": f, "key": k, "confidence": c} for f, k, c in _sqla_json_keys(call))
    if text in ("jwt.encode", "jwt.decode"):
        facts["variants"].append({"line": call.lineno, "kind": "token-code", "variant": "pyjwt"})


def _function_facts(node, facts):
    for decorator in node.decorator_list:
        if call_name(decorator) == "exception_handler" and decorator.args and dotted(decorator.args[0]) == "Exception":
            facts["handlers"].append({"line": node.lineno, "kind": "fastapi-global", "exception": "Exception"})
        if dotted(decorator).endswith("transaction.atomic") or dotted(getattr(decorator, "func", decorator)).endswith("transaction.atomic"):
            facts["txns"].append({"line": node.lineno, "end_line": getattr(node, "end_lineno", node.lineno)})
        if call_name(decorator) in ("get", "api_route"):
            styles = {ROUTE_PARAMS[a.arg] for a in node.args.args + node.args.kwonlyargs if a.arg in ROUTE_PARAMS}
            facts["pagination"].extend({"line": node.lineno, "style": s} for s in sorted(styles))
    if node.name == "handle_exception" and node.args.args and node.args.args[0].arg == "self":
        facts["handlers"].append({"line": node.lineno, "kind": "drf-override", "exception": "Exception"})


def _with_facts(node, facts):
    for item in node.items:
        text = dotted(getattr(item.context_expr, "func", item.context_expr))
        if text.endswith("transaction.atomic") or text.endswith("session.begin") or text.endswith(".begin"):
            end = getattr(node, "end_lineno", None) or max(getattr(n, "lineno", node.lineno) for n in ast.walk(node))
            facts["txns"].append({"line": node.lineno, "end_line": end})


def _assign_facts(node, facts):
    target = dotted(node.targets[0]) if isinstance(node, ast.Assign) and node.targets else ""
    if target.split(".")[-1] == "pagination_class":
        style = PAGINATION_CLASSES.get(dotted(node.value).split(".")[-1])
        if style:
            facts["pagination"].append({"line": node.lineno, "style": style})
    for key, value in zip(getattr(node.value, "keys", []) or [], getattr(node.value, "values", []) or []):
        name = const_value(key)
        if name == "EXCEPTION_HANDLER":
            facts["handlers"].append({"line": node.lineno, "kind": "drf-global", "exception": "Exception"})
        elif name == "DEFAULT_PAGINATION_CLASS" and isinstance(const_value(value), str):
            style = PAGINATION_CLASSES.get(const_value(value).split(".")[-1])
            facts["pagination"].extend([{"line": node.lineno, "style": style}] if style else [])


def _service_style(tree, rel):
    norm = rel.replace("\\", "/")
    if not (os.path.basename(norm) == "services.py" or "/services/" in "/" + norm):
        return []
    functions = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("_")]
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)
               and any(isinstance(m, ast.FunctionDef) and m.name in ("execute", "__call__", "call") for m in n.body)]
    if not functions and not classes:
        return []
    return [{"line": 1, "kind": "py-service", "variant": "classes" if len(classes) >= len(functions) else "functions"}]


def parse_python_code(tree, rel, json_fields=None, not_json=None):
    """Code facts for one parsed module. `json_fields` holds field names known to be JSON columns; `not_json`
    holds names known not to be (Django relations, related_name values, plain columns)."""
    facts = {key: [] for key in ("refs", "writes", "handlers", "factories", "pagination", "jsonb", "txns", "variants")}
    known = (frozenset(json_fields or ()), frozenset(not_json or ()))
    for node, type_only in walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            facts["refs"].extend(_import_refs(node, type_only))
        elif isinstance(node, ast.Call):
            _call_facts(node, facts, known)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _function_facts(node, facts)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            _with_facts(node, facts)
        elif isinstance(node, ast.Assign):
            _assign_facts(node, facts)
    facts["variants"].extend(_service_style(tree, rel))
    return facts
