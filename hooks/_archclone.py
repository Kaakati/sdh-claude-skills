#!/usr/bin/env python3
"""Cross-file copy-paste detection (DK6), for on-demand scans and CI only.

Owner decision D (round 3): no edit-time clone cache in this release, so nothing here is called by
a hook and no fingerprint is stored in the index. Scans tokenize the files in memory.

Tokens are language-aware: Python through the stdlib `tokenize`, Ruby and TS/JS through small
regex lexers (comments dropped; strings, numbers, identifiers, punctuation kept). Identifiers and
literals are normalized for Type-2 (renamed) clones; keywords stay. 25-token k-grams are hashed with
a rolling hash and winnowed with a window of `min_tokens - K + 1`, which guarantees that any shared
run of `min_tokens` tokens shares at least one fingerprint. Candidate pairs are then extended token
by token, and a run counts when it spans at least `min_tokens` tokens and `min_lines` lines. The
same family of technique as jscpd's and PMD CPD's Rabin-Karp matching.

Memory: a file keeps three compact arrays (normalized token ids, raw token ids, line numbers), with each
distinct token string stored once in a vocabulary, and only subjects keep their fingerprint lists. Texts
may arrive one at a time as (path, text) pairs, so a repository's source is never held at once.
"""
import array
import collections
import hashlib
import io
import keyword
import re
import tokenize

K = 25
MIN_TOKENS = 70
MIN_LINES = 8
MAX_POSTINGS = 64  # a fingerprint shared by more places is boilerplate (repeated idioms), not evidence of a copy
_MOD = (1 << 61) - 1
_BASE = 1000003
RB_KEYWORDS = frozenset("alias and begin break case class def defined? do else elsif end ensure false for if in "
                        "module next nil not or redo rescue retry return self super then true undef unless until "
                        "when while yield".split())
JS_KEYWORDS = frozenset("async await break case catch class const continue debugger default delete do else export "
                        "extends false finally for from function if import in instanceof let new null of return "
                        "static super switch this throw true try typeof undefined var void while with yield type "
                        "interface enum implements as".split())
_LEXERS = {
    "rb": re.compile(r"(?P<c>#[^\n]*)|(?P<s>\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|:\w+)|(?P<n>\d[\d_.]*)"
                     r"|(?P<i>[A-Za-z_]\w*[?!]?|@@?\w+|\$\w+)|(?P<p>\S)"),
    "js": re.compile(r"(?P<c>//[^\n]*|/\*.*?\*/)|(?P<s>\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*'|`(?:\\.|[^`\\])*`)"
                     r"|(?P<n>\d[\w.]*)|(?P<i>[A-Za-z_$][\w$]*)|(?P<p>\S)", re.S),
}
_SKIP_PY = frozenset((tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT,
                      tokenize.ENDMARKER, getattr(tokenize, "ENCODING", -1)))


def language(path):
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return {"py": "py", "rb": "rb", "ts": "js", "tsx": "js", "js": "js", "jsx": "js"}.get(ext)


def _python_tokens(text):
    out = []
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type in _SKIP_PY:
            continue
        if tok.type == tokenize.NAME:
            norm = tok.string if keyword.iskeyword(tok.string) else "I"
        elif tok.type in (tokenize.NUMBER, tokenize.STRING):
            norm = "L"
        else:
            norm = tok.string
        out.append((norm, tok.string, tok.start[0]))
    return out


def _regex_tokens(text, lang):
    keywords = RB_KEYWORDS if lang == "rb" else JS_KEYWORDS
    out, line, last = [], 1, 0
    for match in _LEXERS[lang].finditer(text):
        line += text.count("\n", last, match.start())
        last = match.start()
        kind, raw = match.lastgroup, match.group(0)
        if kind == "c":
            continue
        if kind == "i":
            norm = raw if raw in keywords else "I"
        else:
            norm = "L" if kind in ("s", "n") else raw
        out.append((norm, raw, line))
    return out


def tokens(text, lang):
    """[(normalized, raw, line)] for one file; Python falls back to the regex lexer on a tokenize error."""
    if lang == "py":
        try:
            return _python_tokens(text)
        except (tokenize.TokenError, IndentationError, SyntaxError):
            return _regex_tokens(text, "rb")
    return _regex_tokens(text, lang) if lang in _LEXERS else []


def kgram_hashes(ids, k=K):
    if len(ids) < k:
        return []
    power = pow(_BASE, k - 1, _MOD)
    value = 0
    for item in ids[:k]:
        value = (value * _BASE + item) % _MOD
    hashes = [value]
    for i in range(k, len(ids)):
        value = ((value - ids[i - k] * power) * _BASE + ids[i]) % _MOD
        hashes.append(value)
    return hashes


def winnow(hashes, window):
    """{position: hash} of the rightmost minimum in every window of `window` consecutive hashes."""
    picked, queue = {}, collections.deque()
    for i, value in enumerate(hashes):
        while queue and hashes[queue[-1]] >= value:
            queue.pop()
        queue.append(i)
        if queue[0] <= i - window:
            queue.popleft()
        if i >= window - 1 or i == len(hashes) - 1:
            picked[queue[0]] = hashes[queue[0]]
    return picked


def _extend(a_ids, i, b_ids, j):
    """(start in a, start in b, length) of the maximal equal run through a[i:i+K] == b[j:j+K]."""
    back = 0
    while i - back > 0 and j - back > 0 and a_ids[i - back - 1] == b_ids[j - back - 1]:
        back += 1
    ahead = K
    while i + ahead < len(a_ids) and j + ahead < len(b_ids) and a_ids[i + ahead] == b_ids[j + ahead]:
        ahead += 1
    return i - back, j - back, back + ahead


class _Corpus(object):
    def __init__(self, min_tokens, subjects=None):
        self.window, self.subjects = max(1, min_tokens - K + 1), subjects
        self.ids, self.raws, self.lines, self.prints, self.index = {}, {}, {}, {}, {}
        self.vocab, self.raw_vocab, self._words = {}, {}, []

    def add(self, path, text):
        lang = language(path)
        toks = tokens(text, lang) if lang else []
        self.ids[path] = array.array("I", [self.vocab.setdefault(norm, len(self.vocab)) for norm, _, _ in toks])
        self.raws[path] = array.array("I", [self.raw_vocab.setdefault(raw, len(self.raw_vocab)) for _, raw, _ in toks])
        self.lines[path] = array.array("I", [line for _, _, line in toks])
        prints = winnow(kgram_hashes(self.ids[path]), self.window)
        for pos, value in prints.items():
            self.index.setdefault(value, []).append((path, pos))
        if self.subjects is None or path in self.subjects:
            self.prints[path] = sorted(prints.items())

    def words(self):
        """Normalized token strings by id (for the clone digest)."""
        if len(self._words) != len(self.vocab):
            self._words = [None] * len(self.vocab)
            for word, token_id in self.vocab.items():
                self._words[token_id] = word
        return self._words


def build_corpus(texts, min_tokens=MIN_TOKENS, subjects=None):
    """A corpus over `texts`: a {path: text} dict or an iterable of (path, text) pairs consumed one at a time.
    Only `subjects` (all paths when None) keep fingerprint lists to search from."""
    corpus = _Corpus(min_tokens, None if subjects is None else set(subjects))
    for path, text in (texts.items() if hasattr(texts, "items") else texts):
        corpus.add(path, text)
    return corpus


def _record(corpus, a, b, run):
    start_a, start_b, length = run
    raw_equal = corpus.raws[a][start_a:start_a + length] == corpus.raws[b][start_b:start_b + length]
    words = corpus.words()
    digest = hashlib.sha1("\x1f".join(words[i] for i in corpus.ids[a][start_a:start_a + length]).encode("utf-8")).hexdigest()
    lines_a, lines_b = corpus.lines[a], corpus.lines[b]
    return {"a": a, "a_start": lines_a[start_a], "a_end": lines_a[start_a + length - 1],
            "b": b, "b_start": lines_b[start_b], "b_end": lines_b[start_b + length - 1],
            "tokens": length, "kind": "exact" if raw_equal else "renamed", "hash": digest}


def clones_for(corpus, path, limits):
    """Maximal clone runs from `path` into other files, as (min_tokens, min_lines) allow. Positions are visited in
    order, so a position inside a run already extended into the same other file is skipped (`reach`)."""
    min_tokens, min_lines = limits
    a_ids, a_lines, reach, found = corpus.ids[path], corpus.lines[path], {}, []
    for pos, value in corpus.prints.get(path, ()):
        postings = corpus.index.get(value, ())
        if len(postings) > MAX_POSTINGS:
            continue
        for other, opos in postings:
            if other == path or pos < reach.get(other, -1) or a_ids[pos:pos + K] != corpus.ids[other][opos:opos + K]:
                continue
            run = _extend(a_ids, pos, corpus.ids[other], opos)
            reach[other] = run[0] + run[2]
            if run[2] >= min_tokens and a_lines[run[0] + run[2] - 1] - a_lines[run[0]] + 1 >= min_lines:
                found.append(_record(corpus, path, other, run))
    return found


def dedupe(clones):
    """One entry per pair of clone starts (a run found from both of its files is one clone)."""
    seen, unique = set(), []
    for clone in clones:
        key = tuple(sorted([(clone["a"], clone["a_start"]), (clone["b"], clone["b_start"])]))
        if key not in seen:
            seen.add(key)
            unique.append(clone)
    return unique


def find_clones(subjects, texts, min_tokens=MIN_TOKENS, min_lines=MIN_LINES):
    """Clones between each subject path and any other file in `texts` ({path: text} or (path, text) pairs)."""
    corpus = build_corpus(texts, min_tokens, subjects)
    clones = [c for path in sorted(subjects) if path in corpus.ids for c in clones_for(corpus, path, (min_tokens, min_lines))]
    return dedupe(clones)
