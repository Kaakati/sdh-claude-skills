#!/usr/bin/env python3
"""Words and segments: the core of the shell lexer behind `_shell.py`.

`_shell.py` is the API the gates call. This module holds what its two dialects share: the Segment
and Program shapes, the Builder that turns pieces into words and segments, how a segment's program
is found (`command_index`, `programs`), and the POSIX lexer. The PowerShell lexer is `_shellpwsh.py`.

Ordinary shell syntax runs commands too, so the POSIX lexer reads it the way bash does:
  * `(`, `)` end a segment, and `{`, `}` do at command position: `(cd infra && terraform destroy)`
    runs `terraform`, not `(cd`;
  * reserved words are not programs: `then rm -rf "$DIR"/` runs `rm`, `! rm` runs `rm`;
  * `$(...)` and backticks, bare or inside double quotes, are lexed as command lines of their own
    (`out=$(terraform apply -auto-approve)`), while single quotes stay prose
    (`git commit -m 'mentions $(rm -rf /)'`). The substitution's source text stays in its word, so a
    heredoc commit message is still read from `-m "$(cat <<'EOF' ... EOF)"`.
Pure string work: no event, file or environment.
"""

import collections
import re

Segment = collections.namedtuple("Segment", "words redirects heredocs piped")
Program = collections.namedtuple("Program", "name args segment wrappers")

BASH, POWERSHELL = "bash", "powershell"
WRITE_REDIRECTS = (">", ">>", ">|", "&>", "&>>")
SHELLS = ("sh", "bash", "zsh", "dash", "ksh")
MAX_DEPTH = 8  # nested substitutions lexed; deeper text stays literal

_ARITHMETIC = r"\$\(\((?:[^()]|\([^()]*\))*\)\)"
_PIECE = re.compile(
    r"(?P<space>[ \t\r]+|\\\n)"
    r"|(?P<newline>\n)"
    r"|(?P<redirect>\d*(?:<<<|<<-|<<|>>|>&|<&|&>>|&>|>\||<>|[<>]))"
    r"|(?P<op>&&|\|\||;;&?|;&|\|&|[;&|()])"
    r"|(?P<single>'[^']*'?)"
    r"|(?P<ansi>\$'(?:[^'\\]|\\.)*'?)"
    r"|(?P<double>\")"
    r"|(?P<script>\$\((?!\()|`)"
    r"|(?P<bare>(?:" + _ARITHMETIC + r"|\$\{[^}]*\}|[^\s;&|<>()'\"\\`$]|\\.|\$(?!\())+|[\\$])",
    re.S,
)
_DOUBLE = re.compile(
    r"(?P<end>\")|(?P<script>\$\((?!\()|`)|(?P<escape>\\[\\\"$`\n])"
    r"|(?P<text>" + _ARITHMETIC + r"|[^\"\\$`]+|[\\$])",
    re.S,
)
_ANSI_ESCAPES = {"n": "\n", "t": "\t", "r": "\r"}  # `$'...'`: the escapes a command line uses
_ASSIGNMENT = re.compile(r"^[A-Za-z_]\w*=")
_RESERVED = frozenset(("!", "{", "}", "(", ")", "if", "then", "elif", "else", "fi", "do", "done",
                       "while", "until", "esac"))
_NOT_A_COMMAND = frozenset(("for", "select", "case", "function"))  # a name or a word list follows
_POWERSHELL_ASSIGNMENT = ("=", "+=", "-=", "*=", "/=", "%=", "??=")
_WRAPPERS = {  # wrapper -> its options that take a value
    "sudo": ("-u", "-g", "-h", "-p", "-C", "-D", "-r", "-t", "-U", "-T"),
    "doas": ("-u", "-C"), "env": ("-u", "-C", "-S"), "nice": ("-n",),
    "ionice": ("-c", "-n", "-p"), "timeout": ("-s", "-k"),
    "xargs": ("-I", "-n", "-P", "-L", "-d", "-a", "-E", "-s"),
    "nohup": (), "time": (), "command": (), "exec": (), "builtin": (), "stdbuf": (),
}


class Builder(object):
    """Pieces -> words -> segments. A script run from inside a word (`$(...)`, backticks, a
    PowerShell group) is lexed on its own; its segments wait until the pipeline ends and then follow
    it, so a pipeline is never split by a command one of its words expands."""

    def __init__(self, reserved=()):
        self.reserved, self.segments, self.nested, self.pending = reserved, [], [], []
        self.word, self.quoted, self.redirect_op = None, False, None
        self.words, self.redirects, self.heredocs = [], [], []

    def add(self, text, quoted=False):
        self.word = (self.word or "") + text
        self.quoted = self.quoted or quoted

    def redirect(self, op):
        self.end_word()
        self.redirect_op = op

    def nest(self, segments):
        self.nested.extend(segments)

    def end_word(self):
        word, quoted, self.word, self.quoted = self.word, self.quoted, None, False
        if word is None:
            return
        opens_body = self.redirect_op is None and self.words[:1] in ([], ["function"])
        if opens_body and not quoted and word in self.reserved:  # `{ ...; }`, `function f { ...; }`
            self.end_segment(False)
            return
        if self.redirect_op is None:
            self.words.append(word)
            return
        op, self.redirect_op = self.redirect_op, None
        self.redirects.append((op, word))
        if op in ("<<", "<<-"):
            self.pending.append((word, op == "<<-", self.heredocs))

    def end_segment(self, piped):
        self.end_word()
        self.redirect_op = None
        if self.words or self.redirects:
            self.segments.append(Segment(self.words, self.redirects, self.heredocs, piped))
            self.words, self.redirects, self.heredocs = [], [], []
        if not piped:
            self.segments.extend(self.nested)
            self.nested = []


def _unquote(kind, piece):
    """The text a single-quoted, `$'...'` (ANSI-C) or bare (backslash-escaped) piece stands for."""
    if kind == "single":
        return piece[1:-1] if len(piece) > 1 and piece.endswith("'") else piece[1:]
    if kind == "ansi":
        closed = len(piece) > 2 and piece.endswith("'") and not piece.endswith("\\'")
        inner = piece[2:-1] if closed else piece[2:]
        return re.sub(r"\\(.)", lambda match: _ANSI_ESCAPES.get(match.group(1), match.group(1)), inner, flags=re.S)
    return re.sub(r"\\(.)", r"\1", piece.replace("\\\n", ""), flags=re.S)


def _heredoc_body(text, start, delimiter, strip_tabs):
    """(body, resume position) for a here-document whose lines begin at `start`."""
    position = start
    while position < len(text):
        end = text.find("\n", position)
        end = len(text) if end < 0 else end
        line = text[position:end].rstrip("\r")
        if (line.lstrip("\t") if strip_tabs else line) == delimiter:
            return text[start:position], end + 1
        position = end + 1
    return text[start:], len(text)


def _backtick_end(text, start):
    """Index of the backtick that closes a backtick script (len(text) when none does)."""
    index = start
    while index < len(text) and text[index] != "`":
        index += 2 if text[index] == "\\" else 1
    return min(index, len(text))


class _Lexer(Builder):
    """One left-to-right pass over a POSIX command line (or the inside of one `$(...)`)."""

    def __init__(self, text, depth=0):
        Builder.__init__(self, ("{", "}"))
        self.text, self.pos, self.depth, self.closing, self.parens = text, 0, depth, False, 0

    def run(self):
        while self.pos < len(self.text):
            match = _PIECE.match(self.text, self.pos)
            if match is None:
                self.pos += 1
                continue
            self.pos = match.end()
            if self._take(match.lastgroup, match.group()):
                break
        self.end_segment(False)
        return self.segments

    def _take(self, kind, piece):
        """Consume one piece; True when it is the `)` that closes this substitution."""
        if kind in ("single", "ansi", "bare"):
            self._piece(kind, piece)
        elif kind == "double":
            self._double()
        elif kind == "script":
            self.add(self._script(piece))
        elif kind == "redirect":
            self.redirect(piece.lstrip("0123456789"))
        elif kind == "op":
            return self._operator(piece)
        elif kind == "newline":
            self.end_segment(False)
            self._read_heredocs()
        else:
            self.end_word()
        return False

    def _piece(self, kind, piece):
        if kind == "bare" and self.word is None and piece.startswith("#"):
            end = self.text.find("\n", self.pos)  # a comment runs to the end of the line
            self.pos = len(self.text) if end < 0 else end
            return
        self.add(_unquote(kind, piece), kind != "bare" or "\\" in piece)

    def _operator(self, piece):
        if piece == ")" and self.closing and not self.parens:
            return True
        self.parens = self.parens + 1 if piece == "(" else max(0, self.parens - (piece == ")"))
        self.end_segment(piece in ("|", "|&"))
        return False

    def _double(self):
        """A double-quoted piece; each `$(...)` or backtick script inside it is lexed as a script."""
        parts = []
        while self.pos < len(self.text):
            match = _DOUBLE.match(self.text, self.pos)
            self.pos, kind, piece = match.end(), match.lastgroup, match.group()
            if kind == "end":
                break
            parts.append(self._script(piece) if kind == "script"
                         else piece[1:].replace("\n", "") if kind == "escape" else piece)
        self.add("".join(parts), True)

    def _script(self, opener):
        """Lex the command line `$(` or a backtick opens; return its source text for the word."""
        start = self.pos - len(opener)
        if self.depth >= MAX_DEPTH:
            return opener
        if opener == "`":
            end = _backtick_end(self.text, self.pos)
            inner = re.sub(r"\\([\\$`])", r"\1", self.text[self.pos:end])
            self.pos = min(end + 1, len(self.text))
            self.nest(_Lexer(inner, self.depth + 1).run())
        else:
            sub = _Lexer(self.text, self.depth + 1)
            sub.pos, sub.closing = self.pos, True
            self.nest(sub.run())
            self.pos = sub.pos
        return self.text[start:self.pos]

    def _read_heredocs(self):
        for delimiter, strip_tabs, bodies in self.pending:
            body, self.pos = _heredoc_body(self.text, self.pos, delimiter, strip_tabs)
            bodies.append(body)
        self.pending = []


def bash_segments(command):
    """Segments of a POSIX command line, in order (see `_shell.shell_segments`)."""
    return _Lexer(command).run()


def pipelines(segments):
    """Group segments into pipelines (runs joined by `|`)."""
    groups, current = [], []
    for segment in segments:
        current.append(segment)
        if not segment.piped:
            groups.append(current)
            current = []
    return groups + ([current] if current else [])


def basename(word):
    """The program a word names, case-blind and without `.exe`: `/usr/bin/psql` -> `psql`,
    `hashicorp/terraform:1.9` -> `terraform`, `C:\\tools\\Terraform.exe` -> `terraform`. PowerShell,
    NTFS and default APFS all resolve `Git` to git."""
    name = word.replace("\\", "/").rsplit("/", 1)[-1].split(":")[0].lower()
    return name[:-4] if name.endswith(".exe") else name


def command_index(words):
    """Index of the program a segment runs, past `VAR=x` and `$x =` assignments, reserved words
    (`then`, `do`, `!`) and wrappers (`sudo -u x`); None when it runs nothing (`for x in a b`)."""
    index = 0
    while index < len(words):
        word = words[index]
        if _ASSIGNMENT.match(word) or word in _RESERVED:
            index += 1
        elif word.startswith("$") and words[index + 1:index + 2] and words[index + 1] in _POWERSHELL_ASSIGNMENT:
            index += 2
        elif basename(word) in _WRAPPERS:
            index = _past_wrapper(words, index + 1, basename(word))
        else:
            return None if word in _NOT_A_COMMAND else index
    return None


def _past_wrapper(words, index, name):
    while index < len(words) and words[index].startswith("-"):
        index += 2 if words[index] in _WRAPPERS[name] else 1
    return index + 1 if name == "timeout" and index < len(words) else index


def programs(segments):
    """Program(name, args, segment, wrapper words) for each segment that runs something."""
    found = []
    for segment in segments:
        start = command_index(segment.words)
        if start is not None:
            wrappers = {basename(word) for word in segment.words[:start]}
            found.append(Program(basename(segment.words[start]), segment.words[start + 1:],
                                 segment, wrappers))
    return found
