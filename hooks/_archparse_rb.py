#!/usr/bin/env python3
"""Ruby code facts by comment- and string-blanked regex, for the boundary and mechanism detectors.

    consts      class/module names and CONSTANT assignments, fully qualified by lexical nesting
    refs        constant references with the lexical scope they appear in (resolved later against
                the index's constant -> file map, the way Packwerk resolves through Zeitwerk)
    writes      `Model.create/insert_all/upsert_all/update_all/delete_all/destroy_all`, chained
                `Model.where(...).update_all` / `find(...).update!`, raw INSERT/UPDATE/DELETE in execute
    handlers    `rescue_from` in base controllers; error-envelope builder methods
    factories   `Faraday.new(url: ...)`
    pagination  pagy / kaminari `.page` / will_paginate `.paginate` / hand-rolled `.offset(params`
    variants    service entry point, job base, serializer base, view component base, token code
    jsonb       `where/order(...)` strings using `->>`; txns: `.transaction do ... end`
Not seen: `constantize`, `send`, meta-programmed associations, custom Zeitwerk inflections.
"""
import bisect
import os
import re

from _archparse_db import CLASS_LINE, MODULE_LINE, line_of, url_host

_STRING_OR_COMMENT = re.compile(r"\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*'|(#(?!\{)[^\n]*)")
_HEREDOC = re.compile(r"<<[~-]?(['\"]?)([A-Z_]\w*)\1")
CONST_ASSIGN = re.compile(r"^([ \t]*)([A-Z][A-Z0-9_]*)\s*=(?!=)", re.M)
CONST_REF = re.compile(r"(?<![\w:@$.])(?:::)?([A-Z]\w*(?:::[A-Z]\w*)*)")
WRITE_DIRECT = re.compile(r"\b([A-Z][\w:]*)\s*\.\s*(create!?|insert_all!?|upsert_all|update_all|delete_all|destroy_all|"
                          r"insert!?|upsert|find_or_create_by!?|create_or_find_by!?)(?![\w!?])")
WRITE_CHAIN = re.compile(r"\b([A-Z][\w:]*)\s*\.\s*(?:where|find_by!?|find|lock|unscoped|all|joins|includes)\b[^\n]*?"
                         r"\.\s*(update_all|update!?|destroy!?|delete_all|destroy_all|delete|update_columns?)(?![\w!?])")
RAW_WRITE = re.compile(r"\b(?:execute|exec_query|exec_update|exec_delete|exec_insert)\b[\s\S]{0,300}?"
                       r"\b(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+\"?(\w+)\"?", re.I)
RESCUE_FROM = re.compile(r"^\s*rescue_from\s+([A-Z][\w:]*)", re.M)
ENVELOPE_DEF = re.compile(r"^\s*def\s+(?:self\.)?(render_error|error_body|error_response|error_payload|render_api_error|"
                          r"error_json|build_error)\b", re.M)
FARADAY = re.compile(r"\bFaraday\.new\b([^\n]*(?:\n[^\n]*){0,3})")
PAGINATION = (("pagy", re.compile(r"\bpagy(?:_\w+)?\s*\(")), ("kaminari", re.compile(r"\.page\s*\(")),
              ("will_paginate", re.compile(r"\.paginate\s*\(")), ("offset", re.compile(r"\.offset\s*\(\s*params")))
VARIANTS = (
    ("job-base", "active_job", re.compile(r"^\s*class\s+\S+\s*<\s*ApplicationJob\b", re.M)),
    ("job-base", "sidekiq", re.compile(r"^\s*include\s+Sidekiq::(?:Job|Worker)\b", re.M)),
    ("serializer-base", "panko", re.compile(r"<\s*Panko::Serializer\b")),
    ("serializer-base", "active_model_serializers", re.compile(r"<\s*ActiveModel::Serializer\b")),
    ("serializer-base", "jsonapi-serializer", re.compile(r"\binclude\s+JSONAPI::Serializer\b")),
    ("view-component-base", "phlex", re.compile(r"<\s*Phlex::(?:HTML|SVG)\b")),
    ("view-component-base", "view_component", re.compile(r"<\s*ViewComponent::Base\b")),
    ("result-style", "dry-monads", re.compile(r"\bDry::Monads\b")),
    ("token-code", "jwt", re.compile(r"\bJWT\.(?:encode|decode)\b")),
)
SERVICE_ENTRY = re.compile(r"^\s*def\s+(call|perform|execute|run)\b", re.M)
JSONB_CALL = re.compile(r"\.(?:where|order|reorder|group|having|pluck|select|joins|find_by)\s*\(\s*(\"|')([^\n]*?)\1")
JSONB_KEY = re.compile(r"(\w+)\s*->>?\s*'(\w+)'")
TRANSACTION = re.compile(r"^([ \t]*).*?(?:ActiveRecord::Base|[A-Z][\w:]*)\.transaction\b[^\n]*\bdo\b", re.M)
BASE_CONTROLLERS = ("application_controller.rb", "base_controller.rb", "api_controller.rb")
MAX_REFS = 2000
CORE_CONSTANTS = frozenset(("ENV", "ARGV", "STDIN", "STDOUT", "STDERR", "Rails", "Time", "Date", "DateTime", "JSON",
                            "Integer", "String", "Hash", "Array", "Float", "Set", "File", "Dir", "IO", "Kernel",
                            "Object", "Struct", "Class", "Module", "Math", "Process", "Thread", "Mutex", "BigDecimal",
                            "URI", "Logger", "SecureRandom", "Base64", "Digest", "OpenStruct", "Pathname", "Regexp",
                            "Symbol", "Proc", "Range", "StandardError", "ArgumentError", "RuntimeError", "Exception",
                            "NotImplementedError", "Comparable", "Enumerable"))


def _blank(text, keep_strings):
    """Comments blanked (and strings too unless `keep_strings`), heredoc bodies blanked; lines kept."""
    def swap(match):
        if match.group(1) is None and keep_strings:
            return match.group(0)
        return re.sub(r"[^\n]", " ", match.group(0))
    text = _STRING_OR_COMMENT.sub(swap, text)
    for match in list(_HEREDOC.finditer(text)):
        end = re.compile(r"^\s*" + re.escape(match.group(2)) + r"\s*$", re.M).search(text, match.end())
        if end and not keep_strings:
            body = text[match.end():end.start()]
            text = text[:match.end()] + re.sub(r"[^\n]", " ", body) + text[end.start():]
    return text


def _scopes(code):
    """(sorted line starts, scope names) from class/module heads, nesting by indentation."""
    heads = sorted([(m.start(), len(m.group(1)), m.group(2)) for m in CLASS_LINE.finditer(code)]
                   + [(m.start(), len(m.group(1)), m.group(2)) for m in MODULE_LINE.finditer(code)])
    stack, lines, names, consts = [], [], [], []
    for offset, indent, name in heads:
        while stack and stack[-1][0] >= indent:
            stack.pop()
        qualified = (stack[-1][1] + "::" if stack else "") + name
        stack.append((indent, qualified))
        lines.append(line_of(code, offset))
        names.append(qualified)
        consts.append({"symbol": qualified, "line": lines[-1]})
    return lines, names, consts


def _scope_at(scopes, line):
    index = bisect.bisect_right(scopes[0], line) - 1
    return scopes[1][index] if index >= 0 else ""


def _consts_and_refs(code):
    scopes = _scopes(code)
    consts = list(scopes[2])
    for match in CONST_ASSIGN.finditer(code):
        line = line_of(code, match.start())
        scope = _scope_at(scopes, line)
        consts.append({"symbol": (scope + "::" if scope else "") + match.group(2), "line": line})
    refs, seen = [], {(c["symbol"].split("::")[-1], c["line"]) for c in consts[len(scopes[2]):]}
    defined_lines = set(scopes[0])
    for match in CONST_REF.finditer(code):
        line = line_of(code, match.start())
        key = (match.group(1), line)
        head_name = line in defined_lines and code[max(0, match.start() - 8):match.start()].strip() in ("class", "module")
        if key in seen or head_name or match.group(1) in CORE_CONSTANTS or len(refs) >= MAX_REFS:
            continue
        seen.add(key)
        refs.append({"line": line, "symbol": match.group(1), "scope": _scope_at(scopes, line), "lang": "rb", "type_only": False})
    return consts, refs


def _writes(nostr, code):
    writes = [{"line": line_of(nostr, m.start()), "symbol": m.group(1), "op": m.group(2), "table": None}
              for pattern in (WRITE_DIRECT, WRITE_CHAIN) for m in pattern.finditer(nostr)]
    writes += [{"line": line_of(code, m.start()), "symbol": None, "op": "sql", "table": m.group(1)} for m in RAW_WRITE.finditer(code)]
    return writes


def _faraday_target(args):
    env = re.search(r"ENV(?:\.fetch\(\s*|\[\s*)[\"'](\w+)", args)
    if env:
        return "env:" + env.group(1)
    host = re.search(r"[\"']https?://([^/\"']+)", args)
    if host:
        return "host:" + url_host(host.group(1))
    attr = re.search(r"\burl:\s*([\w.:\[\]]+)", args)
    return "attr:" + attr.group(1) if attr else ""


def _handlers(nostr, code, rel):
    handlers = []
    if os.path.basename(rel) in BASE_CONTROLLERS:
        handlers += [{"line": line_of(nostr, m.start()), "kind": "rails-rescue", "exception": m.group(1)}
                     for m in RESCUE_FROM.finditer(nostr)]
    if re.search(r"request_?id|requestId", code, re.I) and re.search(r"\bcode\b", code):
        handlers += [{"line": line_of(nostr, m.start()), "kind": "envelope-builder", "exception": ""}
                     for m in ENVELOPE_DEF.finditer(nostr)]
    return handlers


def _variants(nostr, rel):
    found = [{"line": line_of(nostr, m.start()), "kind": kind, "variant": variant}
             for kind, variant, pattern in VARIANTS for m in list(pattern.finditer(nostr))[:1]]
    if "/app/services/" in "/" + rel.replace("\\", "/"):
        entry = SERVICE_ENTRY.search(nostr)
        if entry:
            found.append({"line": line_of(nostr, entry.start()), "kind": "service-entry", "variant": entry.group(1)})
    return found


def _txns(nostr):
    txns = []
    for match in TRANSACTION.finditer(nostr):
        end = re.compile(r"^" + re.escape(match.group(1)) + r"end\b", re.M).search(nostr, match.end())
        txns.append({"line": line_of(nostr, match.start()), "end_line": line_of(nostr, end.start()) if end else line_of(nostr, match.end())})
    return txns


def parse_ruby_code(text, rel):
    code = _blank(text, keep_strings=True)
    nostr = _blank(text, keep_strings=False)
    consts, refs = _consts_and_refs(nostr)
    jsonb = []
    for match in JSONB_CALL.finditer(code):
        if "@>" not in match.group(2):
            jsonb += [{"line": line_of(code, match.start()), "field": k.group(1), "key": k.group(2), "confidence": "high"}
                      for k in JSONB_KEY.finditer(match.group(2))]
    return {
        "consts": consts, "refs": refs, "writes": _writes(nostr, code), "handlers": _handlers(nostr, code, rel),
        "factories": [{"line": line_of(code, m.start()), "kind": "Faraday.new", "target": _faraday_target(m.group(1))}
                      for m in FARADAY.finditer(code)],
        "pagination": [{"line": line_of(nostr, m.start()), "style": style}
                       for style, pattern in PAGINATION for m in pattern.finditer(nostr)],
        "variants": _variants(nostr, rel), "jsonb": jsonb, "txns": _txns(nostr),
    }
