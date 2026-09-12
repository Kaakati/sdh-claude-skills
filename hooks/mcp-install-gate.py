#!/usr/bin/env python3
"""PreToolUse hook: adding an MCP server is a human decision.

An MCP server is not a library — it is an **instruction source**. Its tool descriptions are
prompts the model obeys, and a server that fetches external content can feed the session text
an attacker wrote. Claude Code's own docs put it plainly:

    "Verify you trust each server before connecting it. Servers that fetch external content can
     expose you to prompt injection risk."

So connecting one is a supply-chain decision with the blast radius of a dependency you cannot
read, and the person accountable for it must be the one who says yes. That is layer 6, and the
skill (`mcp-advisor`) cannot guarantee it: guidance only works if it is read. This gate holds
whether or not anyone read anything (Ch. 7's placement test), which is why it is a hook.

`ask`, never `deny`: MCP servers are legitimate and useful. The point is that a **human** picks
them, not that nobody does. A deny here would just get the plugin disabled.

The ask must tell the truth about scope, because scope is the fact it exists to surface. It reads
the CLI's own flag forms — `-s project`, `-sproject`, `--scope project`, `--scope=project`, and the
same for `-t/--transport` — through the shared shell lexer (`_shell.py`), from the Bash, PowerShell
and Monitor tools alike. Reading only `--scope project` told the human a team-wide add was "local
(default)".

Doors other than `claude mcp add`: `shadcn mcp init` in any runner (npx, pnpm dlx, bunx, yarn dlx),
which writes MCP configuration from inside that CLI; writing `.mcp.json` (every teammate) or
`~/.claude.json` (your local and user-scope servers) with Write/Edit, an MCP file writer named by
`_hooklib.MCP_FILE_WRITE_MATCHER` (its `path`, the `destination` of a move, or each `files[]` entry
GitHub `push_files` commits), or a shell redirect/tee/heredoc/`Set-Content`. And approving servers
wholesale: `enableAllProjectMcpServers: true`, or a new `enabledMcpjsonServers` name, written to a
`.claude/settings.json` or `.claude/settings.local.json` (project or user). The settings reference:
those keys approve a project's `.mcp.json` servers "without a prompt" — the very `Pending approval`
step the `.mcp.json` ask points teammates to. `disabledMcpjsonServers` only rejects servers and is
never asked about. Names are compared case-insensitively — `.MCP.json` is the same file on NTFS and
default macOS volumes.

Fails OPEN: a bug in this hook must not block every Bash command. The gate is a safeguard on a
deliberate action, not a security boundary — layer 4 (`deniedMcpServers` in managed settings)
is where an org makes it non-optional. The lexer is imported at the top, so a missing or broken
`_shell.py` exits 1 — a visible hook error, never a silent allow.
"""

import json
import os
import re

import _hooklib as hooklib
import _shell as shell

_MCP_HINT = re.compile(r"mcp|claude\.json", re.I)
# `claude mcp add <name> -- <cmd>`, `claude mcp add --transport http <name> <url>`,
# `claude mcp add-json <name> '{...}'`, `claude mcp add-from-claude-desktop`.
# Removing, listing or getting a server is not gated: that reduces or inspects capability.
_ADD_SUBCOMMANDS = ("add", "add-json", "add-from-claude-desktop")
_CONFIG_FILES = (".mcp.json", ".claude.json")
_SETTINGS = "settings"
_SETTINGS_FILE = re.compile(r"(?:^|/)\.claude/settings(?:\.local)?\.json$", re.I)
_SERVER_KEYS = re.compile(r"mcpServers|\"command\"\s*:|\"url\"\s*:")
_ENABLE_ALL = re.compile(r"\"enableAllProjectMcpServers\"\s*:\s*true")
_ENABLED_LIST = re.compile(r"\"enabledMcpjsonServers\"\s*:\s*\[([^\]]*)\]?")
# A shell write shows only its command text: `printf '{"enableAllProjectMcpServers": true}' > ...`,
# `jq '.enabledMcpjsonServers += ["x"]'`, PowerShell's `enableAllProjectMcpServers = $true`.
_APPROVAL_COMMAND = re.compile(r"enableAllProjectMcpServers\W{0,3}[:=]\s*\$?true|enabledMcpjsonServers", re.I)


def _flag(args, short, long_flag):
    """`-s x`, `-sx`, `--scope x` or `--scope=x` among the CLI's own options (they end at `--`)."""
    for index, arg in enumerate(args):
        if arg == "--":
            return None
        if arg in (short, long_flag):
            return args[index + 1] if index + 1 < len(args) else None
        if arg.startswith(long_flag + "="):
            return arg[len(long_flag) + 1:]
        if arg.startswith(short) and len(arg) > 2 and not arg.startswith("--"):
            return arg[2:]
    return None


def _mcp_add(segments):
    """(subcommand, its arguments) for the first `claude mcp add*` the command runs, else None."""
    for segment in segments:
        words = segment.words
        for index in range(len(words) - 2):
            named = shell.basename(words[index]) in ("claude", "claude-code") and words[index + 1] == "mcp"
            if named and words[index + 2] in _ADD_SUBCOMMANDS:
                return words[index + 2], words[index + 3:]
    return None


def _shadcn_mcp_init(segments):
    """True when a segment runs the shadcn CLI's `mcp init`: `npx shadcn@latest mcp init`,
    `pnpm dlx shadcn mcp init`, `bunx --bun shadcn --cwd web mcp init`, a local bin."""
    for segment in segments:
        words = segment.words
        for index, word in enumerate(words):
            if shell.basename(word).split("@")[0] != "shadcn":
                continue
            operands = [arg for arg in words[index + 1:] if not arg.startswith("-")]
            if any(operands[at:at + 2] == ["mcp", "init"] for at in range(len(operands))):
                return True
    return False


def _target_kind(path):
    """`.mcp.json`, `.claude.json`, "settings" for a `.claude/settings(.local).json`, else None."""
    norm = hooklib.normalize(path if isinstance(path, str) else "")
    name = norm.rsplit("/", 1)[-1].lower()
    if name in _CONFIG_FILES:
        return name
    return _SETTINGS if _SETTINGS_FILE.search(norm) else None


def _ask_cli(subcommand, args):
    scope = _flag(args, "-s", "--scope") or "local (default)"
    json_type = re.search(r"\"type\"\s*:\s*\"(\w+)\"", " ".join(args))
    transport = _flag(args, "-t", "--transport") or (json_type and json_type.group(1)) or "stdio (default)"
    if subcommand == "add-from-claude-desktop":
        transport = "as configured in Claude Desktop"
    shared = "project" in scope
    hooklib.ask(
        "Adding an MCP server — this needs your decision, not mine.\n\n"
        f"- transport: {transport}\n"
        f"- scope: {scope}{' — this writes .mcp.json and ships to EVERY teammate' if shared else ''}\n\n"
        "An MCP server is an instruction source, not a library: its tool descriptions are "
        "prompts I will obey, and a server that fetches external content can feed this "
        "session text an attacker wrote. The docs are explicit: \"Verify you trust each "
        "server before connecting it.\"\n\n"
        "Before approving, satisfy yourself that: (1) you know who publishes it — prefer "
        "the reviewed Anthropic Directory (https://claude.ai/directory); (2) it is pinned, "
        "not floating on latest; (3) its scope matches its blast radius; (4) any token it "
        "gets is scoped to what it actually needs. See the `mcp-advisor` skill.\n\n"
        "Approve to run it as written, or reject and tell me what to change."
    )


def _ask_shadcn_init():
    hooklib.ask(
        "Running `shadcn mcp init` — the shadcn CLI writes MCP server configuration itself, so "
        "this adds an MCP server with no `claude mcp add` prompt, and the configuration it writes "
        "runs the unpinned `shadcn@latest mcp`.\n\n"
        "An MCP server is an instruction source, not a library: its tool descriptions are prompts "
        "I will obey. The house default is no shadcn MCP server: the CLI's `docs`, `view`, "
        "`search` and `add --dry-run` already answer every lookup (the `std-shadcn-ui` skill). A "
        "team that wants the official server adds it through the `mcp-advisor` skill: pinned to a "
        "version, project scope, chosen by a human.\n\n"
        "Approve to run it as written, or reject and tell me what to change."
    )


def _ask_config(name):
    if name == ".mcp.json":
        hooklib.ask(
            "Editing `.mcp.json` — this adds MCP servers for EVERY teammate who opens this "
            "repo, and it is checked in.\n\n"
            "Each server's tool descriptions are prompts the model obeys, so this is a "
            "supply-chain change to your team's development process, not a config tweak. "
            "Teammates will see it as `Pending approval` until they accept it — unless their "
            "settings already approve project servers (`enableAllProjectMcpServers`, or the "
            "server's name in `enabledMcpjsonServers`), which connects it with no prompt. Either "
            "way, they are trusting your judgement here.\n\n"
            "Confirm you vetted the publisher, pinned the version, and scoped its credentials. "
            "See the `mcp-advisor` skill."
        )
        return
    hooklib.ask(
        "Editing `~/.claude.json` — it holds your local- and user-scope MCP servers, so a server "
        "added here loads into your sessions with no `claude mcp add` prompt.\n\n"
        "Private to you is not the same as safe: each server's tool descriptions are prompts the "
        "model obeys. Confirm you vetted the publisher, pinned the version, and scoped its "
        "credentials — or add it with `claude mcp add` instead. See the `mcp-advisor` skill."
    )


def _ask_approval():
    hooklib.ask(
        "Approving project MCP servers — this write sets `enableAllProjectMcpServers` to true or adds "
        "a name to `enabledMcpjsonServers` in a Claude Code settings file. The settings reference says "
        "those keys approve a project's `.mcp.json` servers \"without a prompt\": each server named "
        "— or, with `enableAllProjectMcpServers`, every server that file holds now or gains later — "
        "connects with no per-server `Pending approval` step.\n\n"
        "Where it applies: your user `~/.claude/settings.json` in every folder; a project's "
        "`.claude/settings.json` or `.claude/settings.local.json` once the folder is trusted (a "
        "committed `.claude/settings.json` is ignored in an untrusted folder).\n\n"
        "Each server's tool descriptions are prompts the model obeys. Confirm you vetted every server "
        "this approves — publisher, pinned version, scoped credentials — or approve servers one at a "
        "time in Claude Code's own approval dialog instead. See the `mcp-advisor` skill."
    )


def _ask_target(kind):
    if kind == _SETTINGS:
        _ask_approval()
    else:
        _ask_config(kind)


def _check_command(command, dialect):
    if not _MCP_HINT.search(command):
        return
    segments = shell.executed_segments(command, dialect)
    add = _mcp_add(segments)
    if add is not None:
        _ask_cli(*add)
        return
    if _shadcn_mcp_init(segments):
        _ask_shadcn_init()
        return
    kinds = [kind for kind in map(_target_kind, shell.written_files(segments)) if kind]
    kinds = [kind for kind in kinds if kind != _SETTINGS or _APPROVAL_COMMAND.search(command)]
    if kinds:
        _ask_target(kinds[0])


def _approvals(text):
    """What settings text approves: "*" for `enableAllProjectMcpServers: true`, and each
    `enabledMcpjsonServers` name. Text that is not a JSON object (an edit fragment) is read by pattern."""
    try:
        data = json.loads(text) if text.strip() else {}
    except (ValueError, RecursionError):
        data = None
    if isinstance(data, dict):
        names = data.get("enabledMcpjsonServers")
        found = {name for name in names if isinstance(name, str)} if isinstance(names, list) else set()
        return found | ({"*"} if data.get("enableAllProjectMcpServers") is True else set())
    found = {name for block in _ENABLED_LIST.findall(text) for name in re.findall(r"\"([^\"]*)\"", block)}
    return found | ({"*"} if _ENABLE_ALL.search(text) else set())


def _apply_edit(text, edit):
    """`text` after one old/new replacement. A replacement whose old text is absent is appended, so a
    fragment that approves servers is still seen when the file cannot be read."""
    old = edit.get("old_string", edit.get("oldText")) if isinstance(edit, dict) else None
    new = edit.get("new_string", edit.get("newText")) if isinstance(edit, dict) else None
    if not isinstance(old, str) or not isinstance(new, str):
        return text
    if not old or old not in text:
        return text + "\n" + new
    return text.replace(old, new) if edit.get("replace_all") else text.replace(old, new, 1)


def _after_write(data, before):
    """The settings text once this Write, Edit, MultiEdit or MCP write, edit or move lands."""
    if isinstance(data.get("content"), str):
        return data["content"]
    if isinstance(data.get("source"), str) and data.get("destination"):
        return hooklib.read_file(data["source"])
    text = before
    for edit in data["edits"] if isinstance(data.get("edits"), list) else [data]:
        text = _apply_edit(text, edit)
    return text


def _approves(event, path, content):
    """True when a settings file approves a `.mcp.json` server after this write that it did not
    approve before. `content` is a `files[]` entry's (new remote content: nothing approved before)."""
    if content is not None:
        return bool(_approvals(content))
    before = hooklib.read_file(path) if os.path.isfile(path) else ""
    return bool(_approvals(_after_write(hooklib.tool_input(event), before)) - _approvals(before))


def _needs_human(event, kind, path, content):
    """True when a write adds MCP servers or approves project servers. `content` is a `files[]`
    entry's; None for the event's own target."""
    if kind == _SETTINGS:
        return _approves(event, path, content)
    data = hooklib.tool_input(event) if content is None else {}
    text = hooklib.get_content(event) if content is None else content
    mentions = "mcpServers" in text if kind == ".mcp.json" else bool(_SERVER_KEYS.search(text))
    edits_servers_file = kind == ".mcp.json" and content is None and (
        hooklib.tool_name(event) in ("Edit", "MultiEdit") or bool(data.get("edits")))
    return mentions or edits_servers_file or bool(data.get("destination"))


def _check_config_write(event):
    """The event's own target, then each `files[]` entry (GitHub `push_files`)."""
    for path, content in [(hooklib.get_file_path(event), None)] + hooklib.get_file_entries(event):
        kind = _target_kind(path)
        if kind and _needs_human(event, kind, path, content):
            _ask_target(kind)
            return


def check(event):
    tool = hooklib.tool_name(event)

    # 1. The CLI path, from the Bash, PowerShell and Monitor tools.
    if hooklib.is_shell_tool(event):
        _check_command(hooklib.shell_command(event) or "", hooklib.shell_dialect(event))
    # 2. The config path — writing .mcp.json is adding a server for the whole team, with no
    #    CLI involved. Gating only the CLI would be a gate with a door next to it. (MultiEdit is
    #    absent from the current tools reference; it stays for releases that still ship it.) An MCP
    #    tool counts when it is one of the file writers hooks.json registers this gate for.
    elif tool in ("Write", "Edit", "MultiEdit") or hooklib.is_mcp_file_write(tool):
        _check_config_write(event)


if __name__ == "__main__":
    hooklib.run_pre_blocker(check, fail_closed=False, gate_label="mcp-install-gate")
