#!/usr/bin/env python3
"""Duplicated-knowledge primitives: name normalization, synonyms, column keys, Jaccard, exclusions.

Names (design §1.3): CamelCase/kebab -> snake_case; namespaces stripped (`Billing::Invoice` ->
`invoice`); the prefixes `tbl_`, `app_` and a declared context prefix stripped; the last word
singularized with conservative rules plus an irregulars table. The suffixes _record, _entity,
_model, _data, _info, _details are recorded, never stripped: a match after removing one is a
`near-name` match.

Columns: a key is (name, type family). Infrastructure columns are removed; a foreign key counts as
`fk:<parent>`; address and money value columns fold into one `value:address` / `value:money` key.
`jaccard` is |A∩B| / |A∪B| over those keys.

Excluded by convention (scans list them at info, hooks never show them): join tables, declared
read models (views, unmanaged or `read_model` models), history/audit, partitions, staging/import,
translations, and the one-table-per-type shape (`project_members` / `group_members`).
"""
import re

RECORDED_SUFFIXES = ("_record", "_entity", "_model", "_data", "_info", "_details", "_detail")
STRIP_PREFIXES = ("tbl_", "app_")
HOUSE_SYNONYMS = (("customer", "client"), ("invoice", "bill"), ("organization", "company", "org"),
                  ("vendor", "supplier"), ("employee", "staff_member"))
INFRA_COLUMNS = frozenset(("id", "created_at", "updated_at", "deleted_at", "discarded_at", "lock_version",
                           "organization_id", "tenant_id"))
VALUE_GROUPS = (
    ("address", frozenset(("line1", "line2", "address_line1", "address_line2", "street", "street_address",
                           "city", "state", "region", "province", "postal_code", "zip", "zip_code",
                           "postcode", "country", "country_code"))),
    ("money", frozenset(("amount", "currency", "amount_cents", "price_cents", "currency_code", "total_cents"))),
)
IRREGULAR = {
    "people": "person", "men": "man", "women": "woman", "children": "child", "mice": "mouse",
    "geese": "goose", "feet": "foot", "teeth": "tooth", "criteria": "criterion", "analyses": "analysis",
    "indices": "index", "matrices": "matrix", "vertices": "vertex", "statuses": "status", "buses": "bus",
    "campuses": "campus", "aliases": "alias", "viruses": "virus", "bonuses": "bonus", "quizzes": "quiz",
    "leaves": "leaf", "lives": "life", "wives": "wife", "knives": "knife", "halves": "half",
    "shelves": "shelf", "caches": "cache", "niches": "niche", "oxen": "ox", "axes": "axis",
}
UNCOUNTABLE = frozenset(("series", "species", "news", "data", "metadata", "media", "equipment",
                         "information", "status", "address", "analysis", "access", "business", "class"))
_FAMILIES = (
    ("other", re.compile(r"ts_?vector|bytea|binary|blob")),
    ("uuid", re.compile(r"uuid")),
    ("json", re.compile(r"json|hstore")),
    ("vector", re.compile(r"vector")),
    ("geo", re.compile(r"geo|point|polygon|line_?string|^st_")),
    ("bool", re.compile(r"bool")),
    ("time", re.compile(r"date|time|interval|duration")),
    ("decimal", re.compile(r"decimal|numeric|float|double|real|money")),
    ("int", re.compile(r"int|serial|autofield")),
    ("enum", re.compile(r"enum")),
    ("text", re.compile(r"char|text|string|email|slug|url|unicode|inet|ipaddress")),
)
_HISTORY = re.compile(r"^(?:versions|.+_versions|.+_history|.+_histories|.+_audits|.+_snapshots|.+_archives?)$")
_STAGING = re.compile(r"^(?:staging_.+|raw_.+|.+_imports)$")
_PARTITION = re.compile(r"_y\d{4}m\d{2}$")
_TRANSLATION = re.compile(r"_translations$")
_NUMBERED = re.compile(r"^([a-z][a-z_]*?[a-z])_?(\d{1,2})$")
_NUMBER_TRAP = re.compile(r"^(?:sha|utf|md|base|v|h|x|ipv|iso|s|ec|oauth)_?\d+$|_p\d{2,3}$")  # hashes, versions, percentiles


def snake(name):
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(name or ""))
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", text)
    return re.sub(r"[-\s.]+", "_", text).strip("_").lower()


def last_segment(name):
    return re.split(r"::|\.|/", str(name or ""))[-1]


def _singular_word(word):
    if word in IRREGULAR:
        return IRREGULAR[word]
    if word in UNCOUNTABLE or len(word) <= 3:
        return word
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith(("sses", "xes", "zes", "ches", "shes")):
        return word[:-2]
    if word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def singular(name):
    parts = str(name or "").split("_")
    parts[-1] = _singular_word(parts[-1])
    return "_".join(parts)


def pluralize(word):
    """Rails-style table name for a singular model word (the inverse of the rules above)."""
    reverse = {v: k for k, v in IRREGULAR.items()}
    if word in reverse:
        return reverse[word]
    if re.search(r"[^aeiou]y$", word):
        return word[:-1] + "ies"
    if re.search(r"(?:s|x|z|ch|sh)$", word):
        return word + "es"
    return word + "s"


def normalize_name(name, context_prefixes=()):
    """(norm, near): the normalized singular name, and the same with a recorded suffix removed."""
    base = snake(last_segment(name))
    for prefix in STRIP_PREFIXES + tuple(snake(p) + "_" for p in context_prefixes if p):
        if base.startswith(prefix) and len(base) > len(prefix):
            base = base[len(prefix):]
    norm = singular(base)
    near = norm
    for suffix in RECORDED_SUFFIXES:
        if norm.endswith(suffix) and len(norm) > len(suffix):
            near = norm[:-len(suffix)]
            break
    return norm, near


def synonym_groups(extra=()):
    """House synonym groups plus project groups, each a frozenset of normalized words."""
    groups = []
    for group in tuple(HOUSE_SYNONYMS) + tuple(extra or ()):
        words = frozenset(normalize_name(w)[0] for w in group if isinstance(w, str) and w.strip())
        if len(words) >= 2:
            groups.append(words)
    return groups


def name_match(a, b, groups):
    """'exact' | 'near-name' | 'synonym' | None for two (norm, near) pairs."""
    if a[0] == b[0]:
        return "exact"
    if a[1] == b[1] or a[1] == b[0] or a[0] == b[1]:
        return "near-name"
    words_a, words_b = {a[0], a[1]}, {b[0], b[1]}
    for group in groups:
        if words_a & group and words_b & group:
            return "synonym"
    return None


def column_family(type_name):
    text = str(type_name or "").lower()
    for family, pattern in _FAMILIES:
        if pattern.search(text):
            return family
    return "other"


def value_group(column_name):
    for group, names in VALUE_GROUPS:
        if column_name in names:
            return group
    return None


def column_keys(columns):
    """{key: column name} for live columns: infrastructure removed, FKs and value groups folded."""
    keys = {}
    for column in columns:
        name = str(column.get("name") or "").lower()
        if not name or name in INFRA_COLUMNS or column.get("op") == "remove":
            continue
        if column.get("fk_table"):
            key = "fk:" + normalize_name(column["fk_table"])[0]
        else:
            group = value_group(name)
            key = "value:" + group if group else "%s:%s" % (name, column.get("family") or "other")
        keys.setdefault(key, name)
    return keys


def jaccard(keys_a, keys_b):
    """(J rounded to 2 places, shared keys sorted, shared non-FK key count)."""
    a, b = set(keys_a), set(keys_b)
    union = a | b
    shared = sorted(a & b)
    facts = len([k for k in shared if not k.startswith("fk:")])
    return (round(len(shared) / float(len(union)), 2) if union else 0.0), shared, facts


def fk_parents(table):
    parents = set()
    for column in table.get("columns") or []:
        name = str(column.get("name") or "").lower()
        if column.get("fk_table"):
            parents.add(normalize_name(column["fk_table"])[0])
        elif name.endswith("_id") and name not in INFRA_COLUMNS:
            parents.add(singular(name[:-3]))
    return parents


def is_join_table(table):
    live = [c for c in table.get("columns") or [] if str(c.get("name") or "").lower() not in INFRA_COLUMNS]
    fks = [c for c in live if c.get("fk_table") or str(c.get("name") or "").endswith("_id")]
    return len(fks) == 2 and len(live) - 2 <= 2


def exclusion(table):
    """The §1.3 convention that excludes a table from duplicate warnings, or None."""
    name = str(table.get("name") or "").lower()
    if table.get("kind") in ("view", "matview") or table.get("read_model"):
        return "read-model"
    if table.get("kind") == "partition" or _PARTITION.search(name):
        return "partition"
    if _HISTORY.match(name):
        return "history"
    if _STAGING.match(name):
        return "staging"
    if _TRANSLATION.search(name):
        return "translation"
    return "join" if is_join_table(table) else None


def per_type_pair(a, b):
    """True for the one-table-per-type shape GitLab prescribes instead of polymorphism."""
    wa, wb = str(a.get("name") or "").lower().split("_"), str(b.get("name") or "").lower().split("_")
    if len(wa) < 2 or len(wb) < 2 or wa[-1] != wb[-1] or wa[:-1] == wb[:-1]:
        return False
    pa, pb = fk_parents(a), fk_parents(b)
    return bool(pa) and bool(pb) and pa != pb


def repeating_groups(columns):
    """{stem: [numbers]} for three or more sibling columns sharing one stem and numbered in one unbroken run
    from 0 or 1 (DK4): phone1..phone3 is a group; latency_p50..latency_p99 (percentiles, each its own
    meaning) and any gapped set are not."""
    stems = {}
    for column in columns:
        name = str(column.get("name") or "").lower()
        match = _NUMBERED.match(name)
        if match and not _NUMBER_TRAP.search(name) and column.get("op") != "remove":
            stems.setdefault(match.group(1), set()).add(int(match.group(2)))
    return {stem: sorted(numbers) for stem, numbers in stems.items()
            if len(numbers) >= 3 and min(numbers) <= 1 and max(numbers) - min(numbers) + 1 == len(numbers)}


_EAV_KEYS = ("key", "attribute", "attr", "attribute_name", "field", "field_name", "property", "property_name", "name")
_EAV_VALUES = ("value", "val", "value_text", "string_value", "text_value", "attribute_value", "field_value")
_FLAG_TABLES = frozenset(("flipper_gates", "flipper_features", "feature_flags", "waffle_flag", "waffle_switch"))


def eav_shape(table):
    """{"entity", "key", "value"} when a table stores entity/attribute/value rows (MF3), else None."""
    name = str(table.get("name") or "").lower()
    names = {str(c.get("name") or "").lower() for c in table.get("columns") or [] if c.get("op") != "remove"}
    if _TRANSLATION.search(name) or name in _FLAG_TABLES:
        return None
    typed = sorted(n for n in names if n.endswith("_type") and n[:-5] + "_id" in names)
    generic = [n for n in ("content_type_id", "content_type") if n in names and "object_id" in names]
    entity = (typed or generic or [n for n in ("entity_id",) if n in names] or [None])[0]
    key = next((k for k in _EAV_KEYS if k in names), None)
    value = next((v for v in _EAV_VALUES if v in names), None)
    if entity and key and value and key != value:
        return {"entity": entity, "key": key, "value": value}
    return None
