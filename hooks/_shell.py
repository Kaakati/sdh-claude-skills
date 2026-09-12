#!/usr/bin/env python3
"""Shell lexer shared by the shell gates.

`pre-commit-check`, `deployment-gate`, `dangerous-command-blocker`, `terraform-command-gate` and
`mcp-install-gate` read a command the way the shell will: quotes, pipes, redirects, here-documents,
subshells and brace groups, `if`/`for` bodies, `$(...)` and backticks, and the scripts `bash -c`,
`bash <<<`, `eval`, `ssh host "..."`, `| sh`, `pwsh -Command`, `Invoke-Expression`, `cmd /c` or
`wsl` will execute. A regex over the raw string denies a commit message that MENTIONS `DROP TABLE`
and misses `rm -fr /`.

Two dialects, one Segment shape: POSIX (`_shellcore.py`) for the Bash and Monitor tools, PowerShell
(`_shellpwsh.py`) for the PowerShell tool, and a script one hands the other is read in its own
dialect. Imported normally: the fail-closed gates import it inside their guarded import (a failure
denies) and the fail-open gates at the top (a failure exits 1: a visible hook error). The git push
parser built on it is `_gitpush.py`. Everything here is pure string work: no event, file or
environment.
"""

import _shellcore as core
import _shellpwsh as pwsh
from _shellcore import (  # noqa: F401  re-exported: the gates call these as shell.<name>
    BASH, POWERSHELL, SHELLS, WRITE_REDIRECTS, Program, Segment, basename, command_index, pipelines,
    programs,
)

POWERSHELLS = pwsh.POWERSHELLS
_COPIES = ("cp", "mv", "install", "copy-item", "copy", "cpi", "move-item", "move", "mi")
_SSH_VALUE_FLAGS = "BbcDEeFIiJLlmOoPpQRSWw"


def shell_segments(command, dialect=BASH):
    """Segments in order: Segment(words, redirects [(op, target)], heredoc bodies, piped).

    A quoted argument is ONE word, and a here-document body is data attached to its segment, never
    words — so `git commit -m "rm -rf /"` runs `git`, and nothing else. A command a word expands
    (`$(...)`, backticks, a PowerShell group) follows its pipeline as segments of its own."""
    text = command or ""
    return pwsh.segments(text) if dialect == POWERSHELL else core.bash_segments(text)


def command_pipelines(command, dialect=BASH, depth=0):
    """Every pipeline the command runs: its own, then those of each script it hands a shell."""
    found = pipelines(shell_segments(command, dialect))
    if depth < 3:
        for pipeline in list(found):
            for script_dialect, script in _scripts(pipeline):
                found.extend(command_pipelines(script, script_dialect, depth + 1))
    return found


def executed_segments(command, dialect=BASH):
    """`command_pipelines`, flattened."""
    return [segment for pipeline in command_pipelines(command, dialect) for segment in pipeline]


def shell_payloads(pipeline):
    """Scripts a pipeline hands a shell: `bash -c "..."`, `bash <<< '...'`, `eval ...`,
    `ssh host "..."`, a here-document fed to a shell, `echo ... | sh`, `pwsh -Command "..."`,
    `iex "..."`, `cmd /c ...`, `wsl ...`."""
    return [script for _dialect, script in _scripts(pipeline)]


def _scripts(pipeline):
    """(dialect, script) for each script in `shell_payloads`."""
    found = []
    for position, segment in enumerate(pipeline):
        found.extend(_segment_scripts(segment))
        reader = _stdin_reader(segment) if position else None
        if reader:
            found.extend((reader, text) for text in stdin_text(pipeline[:position]))
    return [(dialect, text) for dialect, text in found if isinstance(text, str) and text.strip()]


def _segment_scripts(segment):
    words, found = segment.words, []
    for index, word in enumerate(words):
        if basename(word) in SHELLS:
            found.extend((BASH, script) for script in _dash_c(words[index + 1:]))
    start = command_index(words)
    name, args = (basename(words[start]), words[start + 1:]) if start is not None else ("", [])
    if name == "eval":
        found.append((BASH, " ".join(args)))
    elif name == "ssh":
        found.append((BASH, _ssh_command(args)))
    found.extend(pwsh.scripts(name, args))
    fed = segment.heredocs + [target for op, target in segment.redirects if op == "<<<"]
    if name == "ssh" or any(basename(word) in SHELLS for word in words):
        found.extend((BASH, text) for text in fed)
    elif name in POWERSHELLS:
        found.extend((POWERSHELL, text) for text in fed)
    return found


def _dash_c(args):
    """The script given with `-c` among a shell's options (`bash -lc "..."`, `bash -c -- "..."`)."""
    index = 0
    while index < len(args) and args[index][:1] in ("-", "+"):
        flag = args[index]
        if not flag.startswith("--") and "c" in flag[1:]:
            script = index + 2 if args[index + 1:index + 2] == ["--"] else index + 1
            return args[script:script + 1]
        index += 2 if flag[-1:] in ("o", "O") and not flag.startswith("--") else 1
    return []


def _ssh_command(args):
    """The remote command of `ssh [options] host command...` ("" when it only opens a shell)."""
    index = 0
    while index < len(args) and args[index].startswith("-"):
        flag = args[index]
        index += 2 if len(flag) == 2 and flag[1] in _SSH_VALUE_FLAGS else 1
    return " ".join(args[index + 1:])


def _stdin_reader(segment):
    """The dialect a segment runs a script piped to it in (`| sh`, `| ssh host`, `| iex`), else None."""
    start = command_index(segment.words)
    if start is None:
        return None
    name, args = basename(segment.words[start]), segment.words[start + 1:]
    if name in SHELLS + ("ssh",):
        return None if _dash_c(args) else BASH
    return pwsh.stdin_dialect(name, args)


def stdin_text(upstream):
    """What upstream segments feed down a pipeline: `echo`/`printf`/`Write-Output` arguments, a
    lone string literal (PowerShell's `'...' | iex`), and here-documents."""
    texts = [" ".join(program.args) for program in programs(upstream)
             if program.name in ("echo", "printf", "write-output")]
    texts += [segment.words[0] for segment in upstream if len(segment.words) == 1 and " " in segment.words[0]]
    return texts + [body for segment in upstream for body in segment.heredocs]


def written_files(segments):
    """Files segments write through a redirect, `tee`, the destination of `cp`/`mv`/`Copy-Item`, or
    `Set-Content`/`Out-File`/`New-Item`."""
    targets = [target for segment in segments for op, target in segment.redirects
               if op in WRITE_REDIRECTS]
    for program in programs(segments):
        operands = [arg for arg in program.args if not arg.startswith("-")]
        if program.name in ("tee", "tee-object"):
            targets.extend(operands)
        elif program.name in _COPIES and len(operands) > 1:
            targets.append(operands[-1])
        else:
            targets.extend(pwsh.written_by(program.name, program.args))
    return targets
