#!/usr/bin/env python3
"""The project declaration file, `.claude/orthogonality.json`: load, validate, match globs, and
answer the suppression questions every detector asks.

Validation errors ({"path": "$.contexts.billing.paths", "message": ...}) make scripts exit 2 and
hooks show one CFG-INVALID line per session; an invalid file declares nothing. Findings about a
valid file are separate: CFG-ADR (an `adr` that names no existing file) and CFG-READMODEL (a
read-model declaration without source_of_truth, refreshed_by and writes). An `until` date in the
past stops suppressing and the finding returns marked expired. `enforce` accepts only "advisory"
in this release ("ask" is reserved for an opt-in gate that does not ship).
"""
import datetime
import functools
import json
import os
import re
import sys

CONFIG_REL = ".claude/orthogonality.json"
RELATIONSHIPS = ("shared-kernel", "customer-supplier", "conformist", "anticorruption-layer",
                 "open-host-service", "published-language", "separate-ways", "partnership")
TOP_KEYS = ("version", "contexts", "shared_kernel", "concepts", "intentional_duplicates", "mechanisms",
            "backfills", "ignore", "clones", "enforce")
GLOB_LISTS = ("shared_kernel", "backfills", "ignore")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _err(path, message):
    return {"path": path, "message": message}


def _is_str_list(value):
    return isinstance(value, list) and all(isinstance(v, str) and v.strip() for v in value)


def _check_date(value, path):
    if value is None:
        return []
    try:
        if not isinstance(value, str) or not _DATE.match(value):
            raise ValueError
        datetime.datetime.strptime(value, "%Y-%m-%d")
        return []
    except ValueError:
        return [_err(path, "must be an ISO date (YYYY-MM-DD)")]


def _check_context(name, body, names):
    path = "$.contexts.%s" % name
    if not isinstance(body, dict):
        return [_err(path, "must be an object")]
    errors = [_err("%s.%s" % (path, k), "must be a list of strings")
              for k in ("paths", "tables", "may_depend_on") if k in body and not _is_str_list(body[k])]
    errors += [_err("%s.may_depend_on" % path, "names unknown context %r" % d)
               for d in body.get("may_depend_on") or [] if isinstance(d, str) and d not in names]
    relationships = body.get("relationships", {})
    if not isinstance(relationships, dict):
        return errors + [_err(path + ".relationships", "must be an object")]
    errors += [_err("%s.relationships.%s" % (path, k), "must be one of " + ", ".join(RELATIONSHIPS))
               for k, v in relationships.items() if v not in RELATIONSHIPS]
    for index, write in enumerate(body.get("writes") or []):
        if not isinstance(write, dict) or not isinstance(write.get("target"), str) or "." not in write.get("target", ""):
            errors.append(_err("%s.writes[%d].target" % (path, index), "must be \"<context>.<table>\""))
    return errors


def _check_entries(data, key, required):
    errors = []
    for index, entry in enumerate(data.get(key) or []):
        path = "$.%s[%d]" % (key, index)
        if not isinstance(entry, dict):
            errors.append(_err(path, "must be an object"))
            continue
        errors += [_err("%s.%s" % (path, r), "is required") for r in required if not isinstance(entry.get(r), str)]
        errors += _check_date(entry.get("until"), path + ".until")
    return errors


def _check_mechanisms(data):
    mechanisms = data.get("mechanisms", {})
    if not isinstance(mechanisms, dict):
        return [_err("$.mechanisms", "must be an object")]
    errors = []
    for key, required in (("house_overrides", ("deployable", "concern", "package", "adr")),
                          ("migrations", ("deployable", "concern", "from", "to", "adr"))):
        errors += [dict(e, path=e["path"].replace("$.", "$.mechanisms.", 1)) for e in _check_entries(mechanisms, key, required)]
    return errors


def validate(data):
    """Every schema violation as {"path", "message"}; [] for a valid declaration file."""
    if not isinstance(data, dict):
        return [_err("$", "must be a JSON object")]
    errors = [_err("$." + k, "unknown key") for k in data if k not in TOP_KEYS]
    if data.get("version") != 1:
        errors.append(_err("$.version", "must be 1"))
    contexts = data.get("contexts", {})
    if not isinstance(contexts, dict):
        errors.append(_err("$.contexts", "must be an object"))
        contexts = {}
    for name, body in contexts.items():
        errors += _check_context(name, body, contexts)
    errors += [_err("$." + k, "must be a list of glob strings") for k in GLOB_LISTS if k in data and not _is_str_list(data[k])]
    synonyms = (data.get("concepts") or {}).get("synonyms", []) if isinstance(data.get("concepts", {}), dict) else None
    if synonyms is None or not all(_is_str_list(g) and len(g) >= 2 for g in synonyms):
        errors.append(_err("$.concepts.synonyms", "must be a list of lists of two or more names"))
    errors += _check_entries(data, "intentional_duplicates", ("id", "subject", "counterpart", "adr"))
    errors += _check_mechanisms(data)
    if data.get("enforce", "advisory") != "advisory":
        errors.append(_err("$.enforce", "only \"advisory\" is accepted in this release"))
    clones = data.get("clones", {})
    if not isinstance(clones, dict) or not isinstance(clones.get("min_tokens", 70), int):
        errors.append(_err("$.clones.min_tokens", "must be an integer"))
    return errors


def load(root, path=None):
    """(config, errors, config path). A missing file is ({}, [], path); an invalid one declares nothing."""
    target = path or os.path.join(root, CONFIG_REL)
    try:
        with open(target, encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except (OSError, IOError):
        return {}, [], target
    except ValueError as exc:
        return {}, [_err("$", "is not valid JSON (%s)" % exc)], target
    errors = validate(data)
    return ({} if errors else data), errors, target


@functools.lru_cache(maxsize=512)
def glob_regex(pattern):
    text = pattern.replace("\\", "/")
    text = text[2:] if text.startswith("./") else text
    out, i = [], 0
    while i < len(text):
        if text.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif text.startswith("**", i):
            out.append(".*")
            i += 2
        else:
            out.append({"*": "[^/]*", "?": "[^/]"}.get(text[i], re.escape(text[i])))
            i += 1
    flags = re.I if os.name == "nt" or sys.platform == "darwin" else 0
    return re.compile("^" + "".join(out) + "$", flags)


def matches(rel, patterns):
    norm = str(rel or "").replace("\\", "/")
    return any(glob_regex(p).match(norm) for p in patterns or () if isinstance(p, str))


def expired(until, today=None):
    if not until:
        return False
    try:
        return datetime.datetime.strptime(until, "%Y-%m-%d").date() < (today or datetime.date.today())
    except (TypeError, ValueError):
        return False


def declaration_findings(config, root):
    """CFG-ADR (missing ADR file) and CFG-READMODEL (incomplete read-model entry) for a valid file."""
    found = []
    for path, entry in _adr_entries(config):
        adr = entry.get("adr")
        if isinstance(adr, str) and not os.path.isfile(os.path.join(root, adr)):
            found.append({"id": "CFG-ADR", "json_path": path, "adr": adr})
    for index, entry in enumerate(config.get("intentional_duplicates") or []):
        missing = [k for k in ("source_of_truth", "refreshed_by", "writes") if not entry.get(k)]
        if entry.get("kind") == "read-model" and missing:
            found.append({"id": "CFG-READMODEL", "json_path": "$.intentional_duplicates[%d]" % index, "missing": missing})
    return found


def _adr_entries(config):
    for index, entry in enumerate(config.get("intentional_duplicates") or []):
        yield "$.intentional_duplicates[%d].adr" % index, entry
    mechanisms = config.get("mechanisms") or {}
    for key in ("house_overrides", "migrations"):
        for index, entry in enumerate(mechanisms.get(key) or []):
            yield "$.mechanisms.%s[%d].adr" % (key, index), entry
    for name, body in (config.get("contexts") or {}).items():
        for index, entry in enumerate(body.get("writes") or []):
            yield "$.contexts.%s.writes[%d].adr" % (name, index), entry


def intentional(config, detector, subject, counterpart):
    """The intentional_duplicates entry covering this pair (either order), or None."""
    pair = {str(subject).lower(), str(counterpart).lower()}
    for entry in config.get("intentional_duplicates") or []:
        names = {str(entry.get("subject")).lower(), str(entry.get("counterpart")).lower()}
        if entry.get("id") == detector and names == pair:
            return entry
    return None


def _same_deployable(entry, deployable):
    return str(entry.get("deployable") or "").strip("/") in (str(deployable or "").strip("/"), "*")


def house_override(config, deployable, concern):
    for entry in (config.get("mechanisms") or {}).get("house_overrides") or []:
        if entry.get("concern") == concern and _same_deployable(entry, deployable):
            return entry
    return None


def migration(config, deployable, concern, packages):
    """The declared migration for this concern and deployable naming one of `packages`, or None."""
    for entry in (config.get("mechanisms") or {}).get("migrations") or []:
        named = entry.get("from") in packages or entry.get("to") in packages
        if entry.get("concern") == concern and _same_deployable(entry, deployable) and named:
            return entry
    return None


def write_exception(config, owner, table):
    """The `writes` declaration letting another context write owner's `table`, or None."""
    for body in (config.get("contexts") or {}).values():
        for entry in body.get("writes") or []:
            if str(entry.get("target", "")).lower() == ("%s.%s" % (owner, table)).lower():
                return entry
    return None
