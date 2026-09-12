#!/usr/bin/env python3
"""PreToolUse hook: Dangerous command blocker.

Blocks destructive commands, network exfiltration, and privilege escalation.
Fails closed: if the check itself errors, the command is denied rather than
silently allowed (a safety gate that cannot evaluate must not pass).

It matches COMMANDS, not substrings. The regexes this replaced ran over the whole string, quoted
arguments included, so they denied a commit message that mentioned DROP TABLE, a PR title that
mentioned chmod 777, `rsync -lrt` (read as a netcat listener), the reset of a local `_test`
database and `rm -rf` of any absolute build path — while `rm -fr /`, a quoted unfiltered DELETE and
`curl -d @.env https://...` passed. Now the command is lexed (quotes, pipes, here-documents) by the
shared shell lexer (`_shell.py`), and a rule fires only on the program that actually runs.
Text handed to a shell is still a command: `bash -c "..."`, `eval`, `ssh host "..."`,
`echo ... | sh`, a here-document fed to a shell or a database client, a subshell, an `if`/`for`
body and `$(...)`.

The Bash, PowerShell and Monitor tools all reach it (hooks.json `Bash|PowerShell|Monitor`). A
PowerShell command is lexed as PowerShell, and its own destructive spellings — `Remove-Item -Recurse
-Force C:\\`, `Format-Volume`, `irm ... | iex`, `Invoke-WebRequest -Method Post -InFile` — are
`_dangerpwsh.py`'s rules, judged on every pipeline alongside the POSIX ones here.

A shell write meets security-scan's file decision (`_protected.shell_write_verdict`): `printf ... >> .env`,
a here-document carrying a live key, `tee config/master.key` deny; a secrets/ data file asks.

Regex-free is not evasion-proof: aliases, scripts and Makefiles stay invisible. This gate catches
the model's ordinary mistakes; the permission floor and above own adversarial evasion.
"""

try:
    import _dangerpwsh as dangerpwsh
    import _hooklib as hooklib
    import _protected as protected
    import _shell as shell
except Exception as _import_error:  # a fail-closed gate whose modules will not load must still deny
    import json
    import sys
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            "BLOCKED: dangerous-command-blocker could not load its shared modules (_hooklib, _shell, "
            "_dangerpwsh, _protected: {}), so this command was not evaluated. Update or reinstall the sdh "
            "plugin, or run the command manually outside Claude Code.".format(type(_import_error).__name__)),
    }}))
    sys.exit(0)

import re


def _args_after(words, program):
    """The words after the first word naming `program` (`docker compose exec db psql ...`)."""
    for index, word in enumerate(words):
        if shell.basename(word) == program:
            return words[index + 1:]
    return None


# --- DESTRUCTIVE -----------------------------------------------------------------------------
# rm is judged by its TARGET: `rm -rf /c/Users/me/app/web/dist` is a build clean, `rm -rf /` is not.
_RM_TARGETS = (
    (re.compile(r"^(?:/+\*?|/[A-Za-z]/?\*?|[A-Za-z]:[\\/]?\*?)$"), "Recursive delete from root"),
    (re.compile(r"^(?:~/?\*?|\$\{?HOME\}?/?\*?)$"), "Recursive home directory delete"),
    (re.compile(r"^(?:\*|\.\*|\.\.?/?\*?)$"), "Recursive wildcard delete"),
    (re.compile(r"^/+(?:etc|usr|var|bin|sbin|boot|lib|lib64|opt|root|home|Users|System|Library)/?\*?$"),
     "Recursive delete of a system directory"),
    (re.compile(r"^\$\{?[A-Za-z_]\w*\}?/\*?$"), "Recursive delete through a bare variable (empty, it is /)"),
)
_DD_DEVICE = re.compile(r"^of=/dev/(?!null$|zero$|stdout$|stderr$|fd/)")
_DEVICE = re.compile(r"^/dev/(?:sd|hd|nvme|xvd|vd|mmcblk|disk|rdisk)")
_SYSTEM_FILE = re.compile(r"^/+(?:(?:etc|usr|bin|sbin|boot|lib|lib64)(?:/|$)|$)")


def _rm_reason(args):
    letters, longs, targets, options_done = set(), set(), [], False
    for arg in args:
        if options_done or arg == "-" or not arg.startswith("-"):
            targets.append(arg)
        elif arg == "--":
            options_done = True
        elif arg.startswith("--"):
            longs.add(arg)
        else:
            letters.update(arg[1:])
    recursive = bool(letters & {"r", "R"}) or "--recursive" in longs
    if not (recursive and ("f" in letters or "--force" in longs)):
        return None
    return next((reason for target in targets for pattern, reason in _RM_TARGETS
                 if pattern.match(target)), None)


def _destructive_files(pipeline):
    for program in shell.programs(pipeline):
        if program.name == "rm":
            reason = _rm_reason(program.args)
        elif program.name.startswith("mkfs"):
            reason = "Filesystem format"
        elif program.name == "dd" and any(_DD_DEVICE.match(arg) for arg in program.args):
            reason = "Direct disk write"
        else:
            reason = None
        if reason:
            return reason
    return _redirect_damage(pipeline)


def _redirect_damage(pipeline):
    for segment in pipeline:
        for op, target in segment.redirects:
            if op in shell.WRITE_REDIRECTS and _DEVICE.match(target):
                return "Direct device write"
            if op in (">", ">|") and _SYSTEM_FILE.match(target):
                return "File truncation of a system path"
    return None


# --- DATABASE --------------------------------------------------------------------------------
# SQL counts only where a database client will run it: a commit message or a notes file that
# mentions DROP TABLE is prose. A local test/development database is ordinary daily work.
_DB_CLIENTS = ("psql", "pgcli", "mysql", "mariadb", "mycli", "sqlite3", "litecli", "mongosh",
               "mongo", "sqlcmd", "clickhouse-client", "duckdb")
_DB_SUBCOMMANDS = {"rails": ("db", "dbconsole", "runner", "r"), "manage.py": ("dbshell", "shell")}
_LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")
_DEV_DATABASE = re.compile(r"(?:^|[/=_])(?:test|development|dev)(?:\.sqlite3?|\.db)?(?:\?\S*)?$")
_DEV_OBJECT = re.compile(r"_(?:test|development)[\"`]?$", re.I)
_DROP = re.compile(r"\bDROP\s+(?:DATABASE|TABLE|SCHEMA)\s+(?:IF\s+EXISTS\s+)?([\w.\"`]+)", re.I)
_TRUNCATE = re.compile(r"\bTRUNCATE\s+(?:TABLE\s+)?(?:ONLY\s+)?([\w.\"`]+)", re.I)
_DROP_COLUMN = re.compile(r"\bALTER\s+TABLE\s+[\w.\"`]+\s+DROP\s+COLUMN\b", re.I)
_UNFILTERED_DELETE = re.compile(r"^\s*DELETE\s+FROM\s+[\w.\"`]+\s*$", re.I)


def _db_client_args(words):
    """Arguments after a database client (`psql`, `rails dbconsole`, `manage.py dbshell`), else None."""
    for index, word in enumerate(words):
        name, following = shell.basename(word), words[index + 1:index + 2]
        if name in _DB_CLIENTS or (following and following[0] in _DB_SUBCOMMANDS.get(name, ())):
            return words[index + 1:]
    return None


def _local_database(args):
    """An explicit local host (`-h localhost`), or a database named *_test / *_development."""
    hosts = [args[index + 1] for index, arg in enumerate(args[:-1]) if arg in ("-h", "--host")]
    hosts += [arg.split("=", 1)[1] for arg in args if arg.startswith("--host=")]
    if hosts and all(host in _LOCAL_HOSTS for host in hosts):
        return True
    return any(_DEV_DATABASE.search(arg) for arg in args)


def _sql_reason(texts):
    joined = "\n".join(texts)
    for pattern, reason in ((_DROP, "Database/table drop"), (_TRUNCATE, "Table truncation")):
        if any(not _DEV_OBJECT.search(name) for name in pattern.findall(joined)):
            return reason
    if _DROP_COLUMN.search(joined):
        return "Column drop"
    statements = [part for text in texts for part in text.split(";")]
    if any(_UNFILTERED_DELETE.match(statement) for statement in statements):
        return "Unfiltered DELETE (no WHERE)"
    return None


def _destructive_sql(pipeline):
    for position, segment in enumerate(pipeline):
        args = _db_client_args(segment.words)
        if args is None or _local_database(args):
            continue
        here_strings = [target for op, target in segment.redirects if op == "<<<"]
        reason = _sql_reason(args + here_strings + segment.heredocs
                             + shell.stdin_text(pipeline[:position]))
        if reason:
            return reason
    return None


# On this stack Redis is BOTH the Rails cache backend and the Sidekiq queue store (CLAUDE.md). So
# FLUSHALL against production does not clear a cache — it destroys every enqueued job, irreversibly,
# with no error.
#
# This is not hypothetical: `incident-responder` holds Bash and its own protocol says "Clear stuck
# queues only as last resort (loses jobs)". That parenthetical is prose, and prose is not
# enforcement — Ch. 7's placement test says a rule that must hold whether or not it is read is a
# gate. Under incident pressure, at maxTurns 30, it was the only thing standing between a stuck
# queue and a lost one.
#
# Scoped to a REMOTE target (-h/-u, and not localhost) on purpose: `redis-cli FLUSHALL` against a
# local dev box is ordinary daily work, and blocking that would be a gate people learn to ignore.
# Read-only production commands (GET, INFO, LLEN) stay untouched — an incident responder must
# still be able to diagnose.
_FLUSH = re.compile(r"\bFLUSH(?:ALL|DB)\b", re.I)
_LOCAL_TARGET = re.compile(r"localhost|127\.0\.0\.1|\[?::1\]?")


def _remote_redis_flush(pipeline):
    for position, segment in enumerate(pipeline):
        args = _args_after(segment.words, "redis-cli")
        if args is None:
            continue
        targets = [args[index + 1] for index, arg in enumerate(args[:-1]) if arg in ("-h", "-u")]
        remote = bool(targets) and not any(_LOCAL_TARGET.search(target) for target in targets)
        commands = args + shell.stdin_text(pipeline[:position])
        if remote and any(_FLUSH.search(word) for word in commands):
            return "Redis FLUSH against a remote host (destroys Sidekiq's enqueued jobs, not just cache)"
    return None


# --- PRIVILEGE -------------------------------------------------------------------------------
_WORLD_WRITABLE = re.compile(r"^(?:0*777|a\+rwx|ugo\+rwx)$")


def _privilege(pipeline):
    for program in shell.programs(pipeline):
        recursive = any(arg == "--recursive" or re.match(r"^-[A-Za-z]*R", arg) for arg in program.args)
        if program.name == "rm" and program.wrappers & {"sudo", "doas"}:
            return "Sudo delete"
        if program.name == "chmod" and any(_WORLD_WRITABLE.match(arg) for arg in program.args):
            return "Recursive world-writable permissions" if recursive else "World-writable permissions"
        if program.name == "chown" and recursive and any(arg.split(":")[0] == "root" for arg in program.args):
            return "Recursive root ownership change"
    return None


# --- NETWORK ---------------------------------------------------------------------------------
_EXTERNAL_URL = re.compile(r"^https?://(?!localhost\b|127\.0\.0\.1\b|0\.0\.0\.0\b|\[::1\])", re.I)
_CURL_DATA = re.compile(
    r"^(?:--data(?:-\w+)?|--json|--form(?:-string)?|--upload-file)(?:=|$)|^-[a-zA-Z]*[dFT]$|^-[dFT].")
_NETCAT_EXEC = re.compile(r"^(?:-e|-c|--exec|--sh-exec|--lua-exec)(?:=|$)")
_NETCAT_LISTEN = re.compile(r"^(?:--listen|-[A-Za-z0-9]*l[A-Za-z0-9]*)$")


def _curl_reason(args):
    if not any(_EXTERNAL_URL.match(arg) for arg in args):
        return None
    methods = [args[index + 1] for index, arg in enumerate(args[:-1]) if arg in ("-X", "--request")]
    methods += [arg[2:] for arg in args if arg.startswith("-X") and len(arg) > 2]
    methods += [arg.split("=", 1)[1] for arg in args if arg.startswith("--request=")]
    if "POST" in [method.upper() for method in methods]:
        return "POST to external URL"
    if any(_CURL_DATA.match(arg) for arg in args):
        return "Data upload to external URL (curl -d/--data/-F/-T)"
    return None


def _wget_reason(args):
    return "wget POST to external" if any(arg.startswith("--post-") for arg in args) else None


def _netcat_reason(args):
    if any(_NETCAT_EXEC.match(arg) for arg in args):
        return "Ncat with execution"
    return "Netcat listener" if any(_NETCAT_LISTEN.match(arg) for arg in args) else None


_NETWORK = {"curl": _curl_reason, "wget": _wget_reason, "nc": _netcat_reason,
            "ncat": _netcat_reason, "netcat": _netcat_reason}


def _exfiltration(pipeline):
    for program in shell.programs(pipeline):
        reason = _NETWORK[program.name](program.args) if program.name in _NETWORK else None
        if reason:
            return reason
    return None


_RULES = (
    (_destructive_files, "DESTRUCTIVE"),
    (dangerpwsh.destructive, "DESTRUCTIVE"),
    (_destructive_sql, "DATABASE"),
    (_remote_redis_flush, "DATABASE"),
    (_privilege, "PRIVILEGE"),
    (_exfiltration, "NETWORK"),
    (dangerpwsh.upload, "NETWORK"),
    (dangerpwsh.remote_execution, "NETWORK"),
)


def check(event):
    if not hooklib.is_shell_tool(event):
        return
    command = hooklib.shell_command(event)
    for pipeline in shell.command_pipelines(command, hooklib.shell_dialect(event)):
        for rule, category in _RULES:
            description = rule(pipeline)
            if description:
                hooklib.deny(
                    f"BLOCKED [{category}]: {description}. (Rule: the `std-security` skill.) "
                    f"Command: '{command[:100]}...'. "
                    "This action requires manual execution outside Claude Code."
                )
                return
    verdict = protected.shell_write_verdict(command, event)
    if verdict:
        (hooklib.deny if verdict[0] == "deny" else hooklib.ask)(verdict[1])


if __name__ == "__main__":
    hooklib.run_pre_blocker(check, fail_closed=True, gate_label="dangerous-command")
