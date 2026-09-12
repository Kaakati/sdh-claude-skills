#!/usr/bin/env python3
"""The audit trail: credential redaction, where the log lives, and one append per record.

Split out of `_hooklib.py` by responsibility; `_hooklib` re-exports every name here. audit-logger.py
writes one line per tool call, and every gate's deny/ask is appended through `_hooklib._decision`,
because PostToolUse never fires for a call a hook denied.
"""

import json
import os
import re

from _hookpaths import _CURRENT_EVENT, _read_text, normalize

# A flag's value inside one command: quoted (spaces allowed) or one bare word.
_VALUE = r"(?:\"[^\"]*\"|'[^']*'|[^\s;&|'\"]+)"
# At most 12 words between a program and its flag, never past `;`, `&`, `|` or a newline. The bound
# keeps each program-scoped rule linear: an unbounded scan from every program name is quadratic.
_WORDS = r"(?:[ \t]+[^\s;&|]+){0,12}?"
_NO_WORD_BEFORE = r"(?<![\w.-])"


def _flag_after(program, flags, separator=r"(?:[ \t]+|=)", value=_VALUE):
    """`<program> ... <flag><separator><value>` in one command; group 1 is everything before the value.

    Scoped to the program because a flag that carries a password to one tool is harmless to the
    next: `-p` is a port to psql, ssh and `docker run`, and a password to mysql, sshpass and
    `docker login`; `-b` is a branch to git and a secret's body to `gh secret set`."""
    return re.compile("(" + _NO_WORD_BEFORE + "(?:" + program + r")(?![\w.-])" + _WORDS
                      + r"[ \t]+(?:" + flags + ")" + separator + ")" + value)


_REDACTIONS = (
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)"),
     "[REDACTED PRIVATE KEY]"),
    # Any scheme word (Bearer, Basic, Token, ApiKey, AWS4-HMAC-SHA256), then the credential.
    (re.compile(r"(?i)\b((?:proxy-)?authorization[\"']?\s*[:=]\s*[\"']?(?:[A-Za-z][\w-]*[ \t]+)?)[^\s'\"]+"),
     r"\1[REDACTED]"),
    (re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]{8,}"), r"\1[REDACTED]"),
    # A Cookie header carries session credentials; only a `name=value` body counts, so a commit
    # message that says "cookie: handle expiry" is left alone.
    (re.compile(r"(?i)\b((?:set-)?cookie[\"']?\s*:\s*[\"']?)[^'\"\n=]{0,512}=[^'\"\n]*"), r"\1[REDACTED]"),
    (re.compile(r"(://[^/@\s:'\"]+:)[^/@\s'\"]+@"), r"\1[REDACTED]@"),
    # NAME=value. The lookbehind, not `\b`, starts the name only at the start of a run: `\b` tried
    # every `-`/`.` boundary inside a long base64url run, which took quadratic time and ran the
    # audit hook past its timeout, so the call went unrecorded with no gap notice.
    (re.compile(r"(?i)" + _NO_WORD_BEFORE + r"([\w.-]*(?:password|passwd|pwd|secret|token|key|credentials?)"
                r"[\"']?\s*[=:]\s*)(\"[^\"]*\"|'[^']*'|[^\s'\"&;|,}]+)"), r"\1[REDACTED]"),
    (re.compile(r"((?<![\w-])--(?:password|passwd|token|secret|api-key|apikey|api-token|access-token"
                r"|auth-token|client-secret)(?:[ \t]+|=))" + _VALUE), r"\1[REDACTED]"),
    (_flag_after(r"mysql|mariadb|mysqldump|mysqladmin|mysqlimport|mysqlshow|mysqlcheck", "-p", ""),
     r"\1[REDACTED]"),  # attached only: `mysql -p mydb` prompts, and `mydb` is the database
    (_flag_after("sshpass", "-p", r"[ \t]*"), r"\1[REDACTED]"),
    (_flag_after(r"docker[ \t]+login", "-p", r"(?:[ \t]+|=)?"), r"\1[REDACTED]"),
    (_flag_after("redis-cli", "-a|--pass"), r"\1[REDACTED]"),
    (_flag_after(r"gh[ \t]+(?:secret|variable)[ \t]+set", "--body|-b", r"(?:=|[ \t]*)"), r"\1[REDACTED]"),
    # curl -u user:password keeps the user; a quoted pair may hold spaces.
    (_flag_after("curl", "-u|--user", r"(?:=|[ \t]*)(\")?(')?[^\s:;&|'\"]+:",
                 r"(?(2)[^\"]*|(?(3)[^']*|[^\s;&|'\"]+))"), r"\1[REDACTED]"),
    (_flag_after("curl", "-b|--cookie", value=r"(?:\"[^\"=]*=[^\"]*\"|'[^'=]*=[^']*'|[^\s;&|'\"=]+=[^\s;&|'\"]*)"),
     r"\1[REDACTED]"),
    (re.compile(r"(?i)(" + _NO_WORD_BEFORE + r"aws[ \t]+configure[ \t]+set" + _WORDS
                + r"[ \t]+[^\s;&|]{0,64}(?:secret|token|key)[^\s;&|]{0,64}[ \t]+)" + _VALUE), r"\1[REDACTED]"),
    (re.compile(r"((?<![\w-])-pass(?:in|out)?[ \t]+pass:)" + _VALUE), r"\1[REDACTED]"),
    (re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "[REDACTED]"),
    (re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})"), "[REDACTED]"),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"), "[REDACTED]"),
    (re.compile(r"\b(?:sk|rk|pk)[-_](?:live|test|proj|ant)[-_][A-Za-z0-9_-]{8,}"), "[REDACTED]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"), "[REDACTED]"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), "[REDACTED]"),
    # A JWT only at the start of a run, for the reason NAME=value uses a lookbehind: `\b` restarted
    # at every `-` inside a long `eyJ-...` run and backtracked to its end each time.
    (re.compile(r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "[REDACTED]"),
)


def redact(text):
    """`text` with credentials replaced by [REDACTED], for anything written to disk.

    The audit log kept the first 500 characters of every shell command in plaintext — bearer tokens,
    PGPASSWORD=, passwords inside connection-string URLs, `mysql -p<password>`, `curl -u user:pass`.
    It redacts common credential formats, not every possible one. Redact the WHOLE text first, THEN
    truncate: a cut can split a secret past its pattern, and a shortened redaction can shift a
    fragment into the kept prefix.
    """
    out = text if isinstance(text, str) else str(text)
    for pattern, replacement in _REDACTIONS:
        out = pattern.sub(replacement, out)
    return out


def audit_dir(event=None):
    """`<project>/.claude/audit` — anchored to the project, not to the handler's working directory.

    CLAUDE_PROJECT_DIR stays put; the event's `cwd` follows Claude into a `cd` or a worktree; the
    process cwd is wherever the handler happened to start (a monorepo package, so the trail
    splintered). A linked worktree logs into its MAIN checkout: a teammate's worktree, and any log
    inside it, is deleted when the teammate finishes.
    """
    event = event if isinstance(event, dict) else _CURRENT_EVENT[0]
    base = os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd()
    return os.path.join(_main_checkout(base), ".claude", "audit")


def _main_checkout(base):
    """The main working tree when `base` is a linked worktree (`.git` is a gitdir file)."""
    dotgit = os.path.join(base, ".git")
    if not os.path.isfile(dotgit):
        return base
    first = _read_text(dotgit).strip()
    if not first.startswith("gitdir:"):
        return base
    gitdir = normalize(os.path.join(base, first[len("gitdir:"):].strip()))
    cut = gitdir.rfind("/.git/worktrees/")
    return gitdir[:cut] if cut > 0 else base


def append_audit(event, record):
    """Append one JSON line to the audit trail. Returns None, or the error text for a gap notice.

    Never raises: logging must not block a tool — and must not pretend it logged.
    """
    from datetime import datetime, timezone

    event = event if isinstance(event, dict) else {}
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(),
             "session_id": event.get("session_id", "unknown")}
    entry.update(record)
    try:
        directory = audit_dir(event)
        _ensure_audit_dir(directory)
        _append_line(os.path.join(directory, "audit.log"), json.dumps(entry))
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"
    return None


def _ensure_audit_dir(directory):
    """Create the audit dir with its own ignore-everything .gitignore (no consumer doc said to)."""
    os.makedirs(directory, exist_ok=True)
    ignore = os.path.join(directory, ".gitignore")
    if not os.path.exists(ignore):
        with open(ignore, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("# sdh audit trail: a local compliance record, never committed\n*\n")


def _append_line(path, line):
    """One append per record (atomic under O_APPEND); owner-only permissions on POSIX."""
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(line + "\n")
