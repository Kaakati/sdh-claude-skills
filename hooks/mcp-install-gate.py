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

Fails OPEN: a bug in this hook must not block every Bash command. The gate is a safeguard on a
deliberate action, not a security boundary — layer 4 (`deniedMcpServers` in managed settings)
is where an org makes it non-optional.
"""

import re

import _hooklib as hooklib

# `claude mcp add <name> -- <cmd>`, `claude mcp add --transport http <name> <url>`,
# `claude mcp add-json <name> '{...}'`. Also `claude mcp add-from-claude-desktop`.
MCP_ADD = re.compile(r"\bclaude\s+mcp\s+add(?:-json|-from-claude-desktop)?\b")
# Removing a server is not dangerous — it reduces capability. Do not gate it.
MCP_READONLY = re.compile(r"\bclaude\s+mcp\s+(list|get|remove)\b")


def _transport(command):
    m = re.search(r"--transport\s+(\w+)", command)
    if m:
        return m.group(1)
    return "stdio" if " -- " in command else "unknown"


def _scope(command):
    m = re.search(r"--scope\s+(\w+)", command)
    # Per the docs, local is the default: the server loads only in this project and stays
    # private to you. `project` writes .mcp.json and ships to every teammate.
    return m.group(1) if m else "local (default)"


def check(event):
    tool = hooklib.tool_name(event)

    # 1. The CLI path.
    if tool == "Bash":
        command = hooklib.tool_input(event).get("command", "")
        if MCP_READONLY.search(command) and not MCP_ADD.search(command):
            return
        if not MCP_ADD.search(command):
            return

        scope = _scope(command)
        shared = "project" in scope
        hooklib.ask(
            "Adding an MCP server — this needs your decision, not mine.\n\n"
            f"- transport: {_transport(command)}\n"
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
        return

    # 2. The config path — writing .mcp.json is adding a server for the whole team, with no
    #    CLI involved. Gating only the CLI would be a gate with a door next to it.
    if tool in ("Write", "Edit"):
        path = hooklib.normalize(hooklib.get_file_path(event))
        if not path.endswith(".mcp.json"):
            return
        content = hooklib.get_content(event) or ""
        if "mcpServers" not in content and hooklib.tool_name(event) == "Write":
            return
        hooklib.ask(
            "Editing `.mcp.json` — this adds MCP servers for EVERY teammate who opens this "
            "repo, and it is checked in.\n\n"
            "Each server's tool descriptions are prompts the model obeys, so this is a "
            "supply-chain change to your team's development process, not a config tweak. "
            "Teammates will see it as `Pending approval` until they accept it — which means "
            "they are being asked to trust your judgement here.\n\n"
            "Confirm you vetted the publisher, pinned the version, and scoped its credentials. "
            "See the `mcp-advisor` skill."
        )


if __name__ == "__main__":
    hooklib.run_pre_blocker(check, fail_closed=False, gate_label="mcp-install-gate")
