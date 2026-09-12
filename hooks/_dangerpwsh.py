#!/usr/bin/env python3
"""PowerShell's destructive forms, for dangerous-command-blocker.

The blocker's POSIX rules read `rm -rf /` and `curl -d @.env https://...`. PowerShell spells the same
damage differently: `Remove-Item -Recurse -Force C:\\` (or its aliases `rm -r -fo`, `ri`, `del`,
`rd`), `rd /s /q C:\\` through `cmd /c`, `Format-Volume`, `irm https://... | iex`, and
`Invoke-WebRequest -Method Post -InFile .env https://...`. Commands arrive as segments from the shared
lexer (`_shell.py`) in either dialect, so `pwsh -Command "..."` inside a Bash call is judged too.

PowerShell binds a parameter by any unambiguous prefix, case-blind, and accepts `-Name:value`: `-r`,
`-Rec` and `-Recurse:$true` are all `-Recurse`, while `-f` (Filter or Force) binds nothing and the
command fails. Ordinary PowerShell stays allowed: a build directory, `-WhatIf`, a filtered delete, a
download saved with `-OutFile`, a POST to localhost. Pure string work: no event, file or environment.
"""

import re

import _shellcore as core
import _shellpwsh as pwsh

_DASHES = "-\u2013\u2014\u2015"  # PowerShell reads an en dash, em dash or horizontal bar as `-`
_COMMON = dict({name: True for name in (
    "erroraction", "warningaction", "informationaction", "errorvariable", "warningvariable",
    "informationvariable", "outvariable", "outbuffer", "pipelinevariable", "progressaction")},
    verbose=False, debug=False, whatif=False, confirm=False)
_ALIASES = {"lp": "literalpath", "pspath": "literalpath", "wi": "whatif", "cf": "confirm", "vb": "verbose",
            "db": "debug", "ea": "erroraction", "wa": "warningaction", "infa": "informationaction",
            "ev": "errorvariable", "wv": "warningvariable", "iv": "informationvariable",
            "ov": "outvariable", "ob": "outbuffer", "pv": "pipelinevariable", "proga": "progressaction"}
_REMOVE_ITEM = dict(_COMMON, path=True, literalpath=True, filter=True, include=True, exclude=True,
                    credential=True, stream=True, recurse=False, force=False, deletekey=False)
_WEB_REQUEST = dict(_COMMON, **dict({name: True for name in (
    "uri", "method", "custommethod", "body", "form", "infile", "outfile", "headers", "contenttype",
    "useragent", "websession", "sessionvariable", "credential", "certificatethumbprint", "certificate",
    "authentication", "token", "sslprotocol", "proxy", "proxycredential", "timeoutsec",
    "connectiontimeoutseconds", "operationtimeoutseconds", "maximumredirection", "maximumretrycount",
    "retryintervalsec", "unixsocket", "transferencoding", "httpversion", "maximumfollowrellink",
    "responseheadersvariable", "statuscodevariable")}, **{name: False for name in (
        "usedefaultcredentials", "allowunencryptedauthentication", "skipcertificatecheck",
        "proxyusedefaultcredentials", "preservehttpmethodonredirect", "preserveauthorizationonredirect",
        "disablekeepalive", "noproxy", "skipheadervalidation", "skiphttperrorcheck", "resume",
        "passthru", "usebasicparsing", "followrellink", "allowinsecureredirect")}))

_REMOVERS = ("remove-item", "ri", "rm", "rmdir", "rd", "del", "erase")
_CMD_REMOVERS = ("rmdir", "rd", "del", "erase")  # cmd.exe's spellings take /s (recursive) and /q
_CMD_SWITCH = re.compile(r"^/[A-Za-z](?::\S*)?$")
_FORMATS = {"format-volume": "Volume format", "clear-disk": "Disk wipe", "remove-partition": "Partition removal"}
_DRIVE = r"(?:[A-Za-z]:|\$\{?env:(?:SystemDrive|HOMEDRIVE)\}?|%(?:SystemDrive|HOMEDRIVE)%)"
_HOME = (r"(?:~|\$\{?HOME\}?|\$\{?env:(?:USERPROFILE|HOME)\}?|%USERPROFILE%|%HOMEDRIVE%%HOMEPATH%)")
_SYSTEM_DIR = (r"(?:(?:[A-Za-z]:)?[\\/]+(?:Windows(?:[\\/]+System32)?|Users|Program Files(?: \(x86\))?"
               r"|ProgramData|etc|usr|var|bin|sbin|boot|lib|lib64|opt|root|home|System|Library)"
               r"|\$\{?env:(?:SystemRoot|windir|ProgramFiles|ProgramData|ALLUSERSPROFILE)\}?"
               r"|%(?:SystemRoot|windir|ProgramFiles|ProgramData|ALLUSERSPROFILE)%)")
_TARGETS = (  # (pattern, reason, needs -Force and no -Filter/-Include/-Exclude)
    (re.compile(r"^(?:" + _DRIVE + r"[\\/]*|[\\/]+)\*?$", re.I), "Recursive delete from a drive root", False),
    (re.compile(r"^" + _HOME + r"[\\/]*\*?$", re.I), "Recursive home directory delete", False),
    (re.compile(r"^" + _SYSTEM_DIR + r"[\\/]*\*?$", re.I), "Recursive delete of a system directory", False),
    (re.compile(r"^(?:\*(?:\.\*)?|\.\.?[\\/]*\*?)$"), "Recursive wildcard delete", True),
    (re.compile(r"^\$(?!env:)\{?[A-Za-z_]\w*\}?[\\/]+\*?$", re.I),
     "Recursive delete through a bare variable (empty, it is the drive root)", True),
)

_WEB = ("invoke-webrequest", "iwr", "invoke-restmethod", "irm")
_DOWNLOADERS = _WEB + ("curl", "wget", "start-bitstransfer")
_DOWNLOAD_TEXT = re.compile(
    r"(?<![\w-])(?:iwr|irm|invoke-webrequest|invoke-restmethod|curl|wget|start-bitstransfer"
    r"|downloadstring|downloaddata|downloadfile)(?![\w-])", re.I)
_GROUP_WORD = re.compile(r"^[$@]?\(")
_EXTERNAL_URL = re.compile(r"^https?://(?!localhost\b|127\.0\.0\.1\b|0\.0\.0\.0\b|\[::1\])", re.I)
_REMOTE = "Remote script execution (a download run through Invoke-Expression or piped to PowerShell)"
_UPLOAD = ("Data upload to external URL (Invoke-WebRequest/Invoke-RestMethod -Method Post, -Body, "
           "-Form or -InFile)")


def _parameter(word, table):
    """(canonical name, attached value or None) for a parameter word; None for an argument. PowerShell
    binds any unambiguous prefix, case-blind; an ambiguous or unknown one binds nothing ("")."""
    if len(word) < 2 or word[0] not in _DASHES or word[1] in _DASHES:
        return None
    typed, colon, value = word[1:].partition(":")
    typed = typed.lower()
    prefixed = [name for name in table if name.startswith(typed)]
    name = _ALIASES.get(typed) or (typed if typed in table else prefixed[0] if len(prefixed) == 1 else "")
    return name, (value if colon else None)


def _bind(args, table):
    """({parameter: value, or True for a bare switch}, [positional words]) — PowerShell's binding of
    `args` against `table` (parameter name -> whether it takes a value)."""
    named, positional, index = {}, [], 0
    while index < len(args):
        parameter, index = _parameter(args[index], table), index + 1
        if parameter is None:
            positional.append(args[index - 1])
        elif parameter[1] is None and table.get(parameter[0]) and index < len(args):
            named[parameter[0]], index = args[index], index + 1
        else:
            named[parameter[0]] = True if parameter[1] is None else parameter[1]
    return named, positional


def _on(value):
    """A switch's state: `-Recurse` and `-Recurse:$true` are on, `-Recurse:$false` is off."""
    return value is True or (isinstance(value, str) and value.lower() not in ("$false", "false", "0"))


def _preview(args):
    """`-WhatIf` (`-wh`, `-wi`, ...): PowerShell only reports what the command would do."""
    for word in args:
        parameter = _parameter(word, _COMMON)
        if parameter and parameter[0] == "whatif":
            return _on(True if parameter[1] is None else parameter[1])
    return False


def _removal(program):
    """Why a Remove-Item (or `rd /s`, `del /s`) call is catastrophic, else None."""
    named, positional = _bind(program.args, _REMOVE_ITEM)
    cmd_style = program.name in _CMD_REMOVERS and any(word.lower() == "/s" for word in program.args)
    if _preview(program.args) or not (cmd_style or _on(named.get("recurse"))):
        return None
    if program.name in _CMD_REMOVERS:
        positional = [word for word in positional if not _CMD_SWITCH.match(word)]
    loose = (cmd_style or _on(named.get("force"))) and not set(named) & {"filter", "include", "exclude"}
    paths = positional + [value for key, value in named.items()
                          if key in ("path", "literalpath") and isinstance(value, str)]
    targets = [part.strip() for word in paths for part in word.split(",")]
    return next((reason for target in targets for pattern, reason, needs_force in _TARGETS
                 if pattern.match(target) and (loose or not needs_force)), None)


def destructive(pipeline):
    """A PowerShell or Windows destructive form in the pipeline, else None."""
    for program in core.programs(pipeline):
        if program.name in _REMOVERS:
            reason = _removal(program)
        else:
            reason = None if _preview(program.args) else _FORMATS.get(program.name)
        if reason:
            return reason
    return None


def remote_execution(pipeline):
    """A download run as a script: `irm https://... | iex`, `iex (iwr ...)`, `iwr ... | pwsh -`."""
    found = core.programs(pipeline)
    for position, program in enumerate(found):
        inline = program.name in pwsh.EXECUTORS and any(
            _GROUP_WORD.match(word) and _DOWNLOAD_TEXT.search(word) for word in program.args)
        fed = any(upstream.name in _DOWNLOADERS for upstream in found[:position])
        if inline or (fed and pwsh.stdin_dialect(program.name, program.args)):
            return _REMOTE
    return None


def upload(pipeline):
    """Invoke-WebRequest or Invoke-RestMethod sending data to an external URL."""
    for program in core.programs(pipeline):
        if program.name not in _WEB:
            continue
        named, positional = _bind(program.args, _WEB_REQUEST)
        urls = [named.get("uri")] + positional[:1]
        if not any(isinstance(url, str) and _EXTERNAL_URL.match(url) for url in urls):
            continue
        method = str(named.get("method") or named.get("custommethod") or "").lower()
        if method == "post" or set(named) & {"body", "form", "infile"}:
            return _UPLOAD
    return None
