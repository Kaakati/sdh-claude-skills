#!/usr/bin/env python3
"""A restricted TOML reader for pyproject.toml, tach.toml and [tool.importlinter].

`tomllib` (Python 3.11+) is used when present unless `force_subset`; otherwise this subset parser
reads what the index needs: tables, array tables, dotted and quoted keys, basic/literal/multi-line
strings, numbers, booleans, dates (kept as strings), arrays (multi-line, trailing commas, comments)
and inline tables. A line it cannot read is skipped and reported in `errors`, never guessed.
"""
import re

_BARE_KEY = re.compile(r"[A-Za-z0-9_-]+")
_SCALAR = re.compile(r"[^\s,\]\}#]+")
_NUMBER = re.compile(r"[+-]?(?:\d[\d_]*)(?:\.\d[\d_]*)?(?:[eE][+-]?\d+)?$")
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "b": "\b", "f": "\f"}


class TomlError(ValueError):
    pass


def parse_toml(text, force_subset=False):
    """(data, errors). errors is a list of "line N: message" strings (empty with tomllib)."""
    if not force_subset:
        try:
            import tomllib
            return tomllib.loads(text), []
        except ImportError:
            pass
        except Exception as exc:
            return {}, ["tomllib: %s" % exc]
    parser = _Parser(text)
    return parser.document(), parser.errors


class _Parser(object):
    def __init__(self, text):
        self.text, self.pos, self.errors = text, 0, []
        self.root = {}
        self.current = self.root

    def line(self):
        return self.text.count("\n", 0, self.pos) + 1

    def document(self):
        while True:
            self.skip(newlines=True)
            if self.pos >= len(self.text):
                return self.root
            start = self.pos
            try:
                self.statement()
            except TomlError as exc:
                self.errors.append("line %d: %s" % (self.line(), exc))
                self.pos = max(start + 1, self.text.find("\n", start) + 1 or len(self.text))

    def statement(self):
        if self.text.startswith("[[", self.pos):
            self.pos += 2
            path = self.key_path("]]")
            parent = self.walk(path[:-1])
            items = parent.setdefault(path[-1], [])
            if not isinstance(items, list):
                raise TomlError("array table %s redefines a key" % ".".join(path))
            items.append({})
            self.current = items[-1]
        elif self.text.startswith("[", self.pos):
            self.pos += 1
            self.current = self.walk(self.key_path("]"))
        else:
            path = self.key_path("=")
            self.skip()
            self.walk(path[:-1], self.current)[path[-1]] = self.value()
        self.end_of_line()

    def walk(self, path, base=None):
        node = self.root if base is None else base
        for part in path:
            child = node.setdefault(part, {})
            node = child[-1] if isinstance(child, list) and child else child
            if not isinstance(node, dict):
                raise TomlError("key %s is not a table" % part)
        return node

    def key_path(self, closer):
        parts = []
        while True:
            self.skip()
            parts.append(self.key())
            self.skip()
            if self.text.startswith(closer, self.pos):
                self.pos += len(closer)
                return parts
            if not self.text.startswith(".", self.pos):
                raise TomlError("expected %r" % closer)
            self.pos += 1

    def key(self):
        if self.text[self.pos:self.pos + 1] in ('"', "'"):
            return self.string()
        match = _BARE_KEY.match(self.text, self.pos)
        if not match:
            raise TomlError("bad key")
        self.pos = match.end()
        return match.group(0)

    def skip(self, newlines=False):
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch == "#":
                end = self.text.find("\n", self.pos)
                self.pos = len(self.text) if end < 0 else end
            elif ch in " \t\r" or (newlines and ch == "\n"):
                self.pos += 1
            else:
                return

    def end_of_line(self):
        self.skip()
        if self.pos < len(self.text) and self.text[self.pos] != "\n":
            raise TomlError("unexpected text after value")

    def value(self):
        ch = self.text[self.pos:self.pos + 1]
        if ch in ('"', "'"):
            return self.string()
        if ch == "[":
            return self.array()
        if ch == "{":
            return self.inline_table()
        return self.scalar()

    def string(self):
        quote = self.text[self.pos]
        if self.text.startswith(quote * 3, self.pos):
            end = self.text.find(quote * 3, self.pos + 3)
            if end < 0:
                raise TomlError("unterminated multi-line string")
            raw, self.pos = self.text[self.pos + 3:end], end + 3
            return self.unescape(raw.lstrip("\n")) if quote == '"' else raw.lstrip("\n")
        end = self.pos + 1
        while end < len(self.text) and self.text[end] != quote:
            end += 2 if quote == '"' and self.text[end] == "\\" else 1
        if end >= len(self.text) or self.text[end] == "\n":
            raise TomlError("unterminated string")
        raw, self.pos = self.text[self.pos + 1:end], end + 1
        return self.unescape(raw) if quote == '"' else raw

    @staticmethod
    def unescape(raw):
        def swap(match):
            code = match.group(1)
            if code[0] in "uU":
                return chr(int(code[1:], 16))
            return _ESCAPES.get(code, code)
        return re.sub(r"\\(u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8}|.)", swap, raw)

    def array(self):
        self.pos += 1
        items = []
        while True:
            self.skip(newlines=True)
            if self.text.startswith("]", self.pos):
                self.pos += 1
                return items
            items.append(self.value())
            self.skip(newlines=True)
            if self.text.startswith(",", self.pos):
                self.pos += 1
            elif not self.text.startswith("]", self.pos):
                raise TomlError("expected , or ] in array")

    def inline_table(self):
        self.pos += 1
        table = {}
        while True:
            self.skip()
            if self.text.startswith("}", self.pos):
                self.pos += 1
                return table
            path = self.key_path("=")
            self.skip()
            self.walk(path[:-1], table)[path[-1]] = self.value()
            self.skip()
            if self.text.startswith(",", self.pos):
                self.pos += 1

    def scalar(self):
        match = _SCALAR.match(self.text, self.pos)
        if not match:
            raise TomlError("missing value")
        self.pos = match.end()
        token = match.group(0)
        if token in ("true", "false"):
            return token == "true"
        if _NUMBER.match(token):
            cleaned = token.replace("_", "")
            return float(cleaned) if any(c in cleaned for c in ".eE") else int(cleaned)
        return token
