#!/usr/bin/env python3
"""TS/JS code facts and Terraform blocks, for the boundary, mechanism and scan-only detectors.

TS/JS (comments blanked, strings kept so specifiers and URLs survive):
    refs        import / export-from / require / dynamic import specifiers (`_archgraph.IMPORT_OF`,
                the regex clean-architecture-checker uses); `import type` / `export type` are type-only
    factories   `axios.create(...)`, `ky.create(...)`, `new ApolloClient(...)` with their base URL
    handlers    exported functions returning an object literal with error, code and requestId
    pagination  `?cursor=` / `?page=` / `?offset=` in URLs and `params: { cursor | page | offset }`
    variants    component style (class components vs function components) in .tsx/.jsx
Terraform: `module` blocks with `source` / `version`, and `resource "type" "name"` headers.
JS config files (ESLint flat config, dependency-cruiser) are never evaluated.
"""
import re

import _archgraph
from _archparse_db import line_of, url_host

_COMMENT_OR_STRING = re.compile(r"(//[^\n]*|/\*.*?\*/)|\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*'|`(?:\\.|[^`\\])*`", re.S)
IMPORT_SPEC = re.compile("(" + _archgraph.IMPORT_OF + r")([^'\"\n]+)['\"]")
EXPORT_FROM = re.compile(r"\bexport\s+(type\s+)?(?:\*(?:\s+as\s+\w+)?|\{[^}]*\})\s*from\s*['\"]([^'\"\n]+)['\"]")
FACTORY = re.compile(r"\b(axios\.create|ky\.create|ky\.extend|new\s+ApolloClient)\s*\(")
BASE_ENV = re.compile(r"(?:baseURL|baseUrl|prefixUrl|uri)\s*:\s*(?:import\.meta\.env|process\.env)\.(\w+)")
BASE_HOST = re.compile(r"(?:baseURL|baseUrl|prefixUrl|uri)\s*:\s*[`'\"]https?://([^/`'\"$]+)")
BASE_ATTR = re.compile(r"(?:baseURL|baseUrl|prefixUrl|uri)\s*:\s*([A-Za-z_$][\w$.]*)")
EXPORTED = re.compile(r"\bexport\s+(?:default\s+)?(?:async\s+)?(?:function\s+(\w+)|const\s+(\w+)\s*=)")
ENVELOPE_OBJECT = re.compile(r"\{[^{}]{0,300}\}", re.S)
URL_PAGINATION = re.compile(r"[?&](cursor|page|offset)=")
PARAMS_PAGINATION = re.compile(r"\bparams\s*:\s*\{[^}]*?\b(cursor|page|offset)\b")
CLASS_COMPONENT = re.compile(r"\bclass\s+\w+\s+extends\s+(?:React\.)?(?:Pure)?Component\b")
JSX_RETURN = re.compile(r"(?:return|=>)\s*\(?\s*<[A-Za-z>]")
STYLES = {"cursor": "cursor", "page": "page-number", "offset": "limit-offset"}
TF_MODULE = re.compile(r"^\s*module\s+\"([\w-]+)\"\s*\{", re.M)
TF_RESOURCE = re.compile(r"^\s*resource\s+\"([\w-]+)\"\s+\"([\w-]+)\"", re.M)


def blank_comments(text):
    return _COMMENT_OR_STRING.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)) if m.group(1) else m.group(0), text)


def balanced(text, open_at, limit=2000):
    """Text inside the bracket opening at `open_at` (bounded by `limit` characters)."""
    pairs, depth = {"(": ")", "{": "}", "[": "]"}, 0
    closer = pairs.get(text[open_at], ")")
    for i in range(open_at, min(len(text), open_at + limit)):
        depth += 1 if text[i] == text[open_at] else -1 if text[i] == closer else 0
        if depth == 0:
            return text[open_at + 1:i]
    return text[open_at + 1:open_at + limit]


def _refs(code):
    refs = [{"line": line_of(code, m.start()), "symbol": m.group(2).strip(), "scope": "", "lang": "js",
             "type_only": bool(re.match(r"import\s+type\b", m.group(1)))} for m in IMPORT_SPEC.finditer(code)]
    refs += [{"line": line_of(code, m.start()), "symbol": m.group(2).strip(), "scope": "", "lang": "js",
              "type_only": bool(m.group(1))} for m in EXPORT_FROM.finditer(code)]
    return refs


def _factory_target(args):
    for pattern, prefix in ((BASE_ENV, "env:"), (BASE_HOST, "host:"), (BASE_ATTR, "attr:")):
        match = pattern.search(args)
        if match:
            return prefix + (url_host(match.group(1)) if prefix == "host:" else match.group(1))
    return ""


def _factories(code):
    return [{"line": line_of(code, m.start()), "kind": re.sub(r"\s+", " ", m.group(1)),
             "target": _factory_target(balanced(code, m.end() - 1))} for m in FACTORY.finditer(code)]


def _envelope_builders(code):
    builders = []
    exports = list(EXPORTED.finditer(code))
    for index, match in enumerate(exports):
        end = exports[index + 1].start() if index + 1 < len(exports) else min(len(code), match.end() + 2000)
        body = code[match.end():end]
        for obj in ENVELOPE_OBJECT.finditer(body):
            literal = obj.group(0)
            if all(re.search(r"\b%s\b\s*[:,}]" % key, literal) for key in ("error", "code", "requestId")):
                builders.append({"line": line_of(code, match.start()), "kind": "envelope-builder", "exception": ""})
                break
    return builders


def _pagination(code):
    styles = [(line_of(code, m.start()), STYLES[m.group(1)]) for m in URL_PAGINATION.finditer(code)]
    styles += [(line_of(code, m.start()), STYLES[m.group(1)]) for m in PARAMS_PAGINATION.finditer(code)]
    return [{"line": line, "style": style} for line, style in sorted(set(styles))]


def _variants(code, rel):
    if not rel.endswith((".tsx", ".jsx")):
        return []
    match = CLASS_COMPONENT.search(code)
    if match:
        return [{"line": line_of(code, match.start()), "kind": "component-style", "variant": "class"}]
    return [{"line": 1, "kind": "component-style", "variant": "function"}] if JSX_RETURN.search(code) else []


def parse_js(text, rel):
    code = blank_comments(text)
    return {"refs": _refs(code), "factories": _factories(code), "handlers": _envelope_builders(code),
            "pagination": _pagination(code), "variants": _variants(code, rel)}


def parse_tf(text):
    blocks = []
    for match in TF_MODULE.finditer(text):
        body = balanced(text, match.end() - 1, limit=20000)
        source = re.search(r"^\s*source\s*=\s*\"([^\"]+)\"", body, re.M)
        version = re.search(r"^\s*version\s*=\s*\"([^\"]+)\"", body, re.M)
        blocks.append({"line": line_of(text, match.start()), "block": "module", "type": None, "name": match.group(1),
                       "source": source.group(1) if source else None, "version": version.group(1) if version else None})
    blocks += [{"line": line_of(text, m.start()), "block": "resource", "type": m.group(1), "name": m.group(2),
                "source": None, "version": None} for m in TF_RESOURCE.finditer(text)]
    return blocks
