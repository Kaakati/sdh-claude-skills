#!/usr/bin/env python3
"""PowerShell for the shell gates: its lexer, and the forms that run a script or write a file.

Claude Code's PowerShell tool sends its command in `tool_input.command`: "The fields match the Bash
tool, with the command string in `command`" (hooks reference, PowerShell), and on Windows it is the
primary shell wherever it is enabled. PowerShell is not POSIX: a backslash is a path character and
the backtick escapes; `''` inside single quotes is one quote; `@'...'@` is a here-string; `(...)`,
`$(...)`, `@(...)` and `{...}` hold statements that run; `#` and `<# #>` are comments. Read as POSIX,
`C:\\Windows` becomes `C:Windows` and a here-string commit message becomes `@`. So this lexer yields
the same Segment shape as the POSIX one (`_shellcore.py`), and `_shell.py` picks the dialect.

It also knows the programs that hand a script on (`pwsh -Command`, `Invoke-Expression`, `cmd /c`,
`wsl`) and the cmdlets that write a file (`Set-Content`, `Out-File`, `New-Item`). Pure string work.
"""

import re

import _shellcore as core

POWERSHELLS = ("pwsh", "powershell")
EXECUTORS = ("invoke-expression", "iex")
_Q1, _Q2 = "'\u2018\u2019\u201a\u201b", "\"\u201c\u201d\u201e"  # PowerShell accepts typographic quotes
_PIECE = re.compile(
    r"(?P<space>[ \t\r\f\v]+|`\r?\n)"
    r"|(?P<newline>\n)"
    r"|(?P<comment><#.*?(?:#>|\Z))"
    r"|(?P<herestring>@[" + _Q1 + _Q2 + r"][ \t]*\r?\n)"
    r"|(?P<redirect>[1-6*]?>>?(?:&[12])?|<)"
    r"|(?P<op>&&|\|\||[;|&])"
    r"|(?P<single>[" + _Q1 + r"](?:[^" + _Q1 + r"]|[" + _Q1 + r"]{2})*[" + _Q1 + r"]?)"
    r"|(?P<double>[" + _Q2 + r"])"
    r"|(?P<group>\$\(|@[({]|[({])"
    r"|(?P<close>[)}])"
    r"|(?P<bare>(?:\$\{[^}]*\}|`.|[^\s;&|<>(){}`$@" + _Q1 + _Q2 + r"]|\$(?!\()|@(?![({" + _Q1 + _Q2
    + r"]))+|[`$@])",
    re.S,
)
_DOUBLE = re.compile(
    r"(?P<quote>[" + _Q2 + r"]{2})|(?P<end>[" + _Q2 + r"])|(?P<escape>`.)|(?P<group>\$\()"
    r"|(?P<text>[^`$" + _Q2 + r"]+|[`$])",
    re.S,
)
_ESCAPES = {"n": "\n", "r": "\r", "t": "\t", "0": "\0", "a": "\a", "b": "\b", "e": "\x1b", "f": "\f",
            "v": "\v"}
_POWERSHELL_VALUE_OPTIONS = ("executionpolicy", "ep", "ex", "windowstyle", "w", "workingdirectory", "wd",
                             "wo", "inputformat", "inp", "if", "outputformat", "o", "of", "version", "v",
                             "configurationname", "config", "settingsfile", "settings", "custompipename")
_ENCODED = ("encodedcommand", "enc", "e", "ec", "encodedarguments", "ea")
_CMD_RUN = ("/c", "/k", "/r", "//c", "//k")
_WSL_VALUE_OPTIONS = ("-d", "--distribution", "-u", "--user", "--cd", "--shell-type", "--distribution-id")
_WRITERS = ("set-content", "sc", "add-content", "ac", "out-file", "new-item", "ni")
_PATH_PARAMETERS = ("path", "literalpath", "lp", "pspath", "filepath", "name")
_VALUE_PARAMETERS = ("value", "itemtype", "type", "encoding", "stream", "width", "credential", "filter",
                     "include", "exclude", "inputobject", "target")


def _single_text(piece):
    """A single-quoted string's text: `''` inside it is one quote."""
    inner = piece[1:]
    if (len(inner) - len(inner.rstrip(_Q1))) % 2:
        inner = inner[:-1]
    return re.sub("[" + _Q1 + "]{2}", "'", inner)


class _Lexer(core.Builder):
    """One left-to-right pass over PowerShell text (or the inside of one group)."""

    def __init__(self, text, depth=0):
        core.Builder.__init__(self)
        self.text, self.pos, self.depth, self.closer = text, 0, depth, None

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
        """Consume one piece; True when it closes this group."""
        if kind in ("single", "bare"):
            self._word(kind, piece)
        elif kind == "double":
            self.add(self._double(), True)
        elif kind == "herestring":
            self.add(self._herestring(piece), True)
        elif kind == "group":
            self.add(self._group(piece))
        elif kind == "close" and piece == self.closer:
            return True
        elif kind == "redirect" and not piece.endswith(("&1", "&2")):  # 2>&1 merges streams, names no file
            self.redirect(piece.lstrip("123456*"))
        elif kind in ("op", "newline"):
            self.end_segment(piece == "|")
        else:
            self.end_word()
        return False

    def _word(self, kind, piece):
        if kind == "bare" and self.word is None and piece.startswith("#"):
            end = self.text.find("\n", self.pos)  # a comment runs to the end of the line
            self.pos = len(self.text) if end < 0 else end
            return
        if kind == "single":
            self.add(_single_text(piece), True)
        else:
            self.add(re.sub(r"`(.)", r"\1", piece, flags=re.S), "`" in piece)

    def _double(self):
        """A double-quoted string's text; each `$(...)` inside it is lexed as statements."""
        parts = []
        while self.pos < len(self.text):
            match = _DOUBLE.match(self.text, self.pos)
            self.pos, kind, piece = match.end(), match.lastgroup, match.group()
            if kind == "end":
                break
            parts.append(self._group(piece) if kind == "group"
                         else _ESCAPES.get(piece[1], piece[1]) if kind in ("escape", "quote") else piece)
        return "".join(parts)

    def _group(self, opener):
        """Lex the statements a `(`, `$(`, `@(`, `{` or `@{` group holds; return its source text."""
        start = self.pos - len(opener)
        if self.depth >= core.MAX_DEPTH:
            return opener
        sub = _Lexer(self.text, self.depth + 1)
        sub.pos, sub.closer = self.pos, ")" if opener.endswith("(") else "}"
        self.nest(sub.run())
        self.pos = sub.pos
        return self.text[start:self.pos]

    def _herestring(self, opener):
        """A here-string's body: `@'` ... `'@` is literal; `@"` ... `"@` also runs its `$(...)`."""
        closing = re.compile(r"\r?\n[" + (_Q1 if opener[1] in _Q1 else _Q2) + r"]@")
        match = closing.search(self.text, self.pos)
        end = match.start() if match else len(self.text)
        body, self.pos = self.text[self.pos:end], match.end() if match else len(self.text)
        if opener[1] in _Q2:
            self._expand(body)
        return body

    def _expand(self, body):
        inner, position = _Lexer(body, self.depth), body.find("$(")
        while position >= 0:
            inner.pos = position + 2
            inner._group("$(")
            position = body.find("$(", inner.pos)
        self.nest(inner.nested)


def segments(command):
    """Segments of a PowerShell command, in order, in the `_shellcore.Segment` shape."""
    return _Lexer(command).run()


def _powershell_script(args):
    """The script `pwsh`/`powershell` runs: the words after `-Command`, or a first positional word;
    "" when it reads stdin (no script, or `-Command -`); None for `-File` or an encoded command."""
    index = 0
    while index < len(args):
        word = args[index]
        name = word.lstrip("-/").lower()
        if word[:1] not in ("-", "/"):
            return " ".join(args[index:])
        if name and "command".startswith(name):
            script = " ".join(args[index + 1:])
            return "" if script.strip() == "-" else script
        if name and ("file".startswith(name) or name in _ENCODED):
            return None
        index += 2 if name in _POWERSHELL_VALUE_OPTIONS else 1
    return ""


def _cmd_script(args):
    """The command line `cmd /c` (or `/k`) runs; "" without one."""
    for index, word in enumerate(args):
        if word.lower() in _CMD_RUN:
            return " ".join(args[index + 1:])
    return ""


def _wsl_script(args):
    """The Linux command line `wsl [options] <command>` runs; "" when it runs none."""
    index = 0
    while index < len(args):
        word = args[index]
        if word in ("--", "-e", "--exec"):
            return " ".join(args[index + 1:])
        if not word.startswith("-"):
            return " ".join(args[index:])
        index += 2 if word in _WSL_VALUE_OPTIONS else 1
    return ""


def _expression(args):
    """What `Invoke-Expression` evaluates: its words, past a `-Command` parameter name."""
    if args[:1] and len(args[0]) > 1 and "-command".startswith(args[0].lower()):
        args = args[1:]
    return " ".join(args)


def scripts(name, args):
    """(dialect, script) for each script a program hands on: `pwsh -Command "..."`,
    `Invoke-Expression "..."` and `cmd /c ...` read as PowerShell, `wsl <command>` read as POSIX."""
    if name in POWERSHELLS:
        return [(core.POWERSHELL, _powershell_script(args) or "")]
    if name in EXECUTORS:
        return [(core.POWERSHELL, _expression(args))]
    if name == "cmd":
        return [(core.POWERSHELL, _cmd_script(args))]
    return [(core.BASH, _wsl_script(args))] if name == "wsl" else []


def stdin_dialect(name, args):
    """The dialect a program runs a script piped to it in (`| iex`, `| pwsh -`, `| cmd`), else None."""
    reads = ((name in POWERSHELLS and _powershell_script(args) == "")
             or (name in EXECUTORS and not args) or (name == "cmd" and not _cmd_script(args)))
    return core.POWERSHELL if reads else None


def written_by(name, args):
    """Files a cmdlet writes: Set-Content, Add-Content, Out-File or New-Item's -Path, -LiteralPath,
    -FilePath or -Name, else its first positional argument."""
    if name not in _WRITERS:
        return []
    paths, positional, index = [], [], 0
    while index < len(args):
        word, index = args[index], index + 1
        flag, colon, attached = word[1:].partition(":")
        if word[:1] != "-":
            positional.append(word)
            continue
        if flag.lower() not in _PATH_PARAMETERS + _VALUE_PARAMETERS:
            continue
        value = attached if colon else (args[index] if index < len(args) else "")
        index += 0 if colon else 1
        if flag.lower() in _PATH_PARAMETERS:
            paths.append(value)
    return paths or positional[:1]
