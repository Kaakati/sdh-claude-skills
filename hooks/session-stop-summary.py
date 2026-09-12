#!/usr/bin/env python3
"""
Stop hook: tell the DEVELOPER the working tree's state when Claude stops responding.

Contract (https://code.claude.com/docs/en/hooks): Stop "runs when the main Claude Code agent has
finished responding", so every turn, not only at session end. On exit 0 "Claude Code writes stdout
to the debug log and doesn't show it in the transcript" for every event except UserPromptSubmit,
UserPromptExpansion, SessionStart and PostModelSwitch. The old plain `print` therefore reached
nobody. `systemMessage` is the documented "warning message shown to the user". additionalContext and
`decision: "block"` are both wrong here, because both keep the conversation going.

One lock-free `git status --porcelain=v2 --branch` call (`_teamgate.run_git`, shared with the team
gates and SessionStart) gives the staged/modified/untracked counts and the ahead count. The old code
made up to four calls, and its strip() of the whole output turned a first-line ' M' (modified, not
staged) into "1 staged". The summary is emitted only when it differs from the last one shown in this
session, so an unchanged tree stays quiet turn after turn.

Always exits 0 (a missing or broken shared module exits 1: a visible, non-blocking hook error).
"""
import hashlib
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _teamgate as teamgate  # noqa: E402


def git_status(cwd):
    """Porcelain v2 output for `cwd`, or None outside a work tree or when git cannot run."""
    code, out = teamgate.run_git(cwd, ["status", "--porcelain=v2", "--branch"], timeout=5)
    return out if code == 0 else None


def parse_counts(status):
    counts = {"staged": 0, "modified": 0, "untracked": 0, "ahead": 0, "upstream": ""}
    for line in status.splitlines():
        if line.startswith("# branch.upstream "):
            counts["upstream"] = line[len("# branch.upstream "):]
        elif line.startswith("# branch.ab "):
            ahead = line.split()[2].lstrip("+") if len(line.split()) > 2 else ""
            counts["ahead"] = int(ahead) if ahead.isdigit() else 0
        elif line[:2] in ("1 ", "2 ", "u ") and len(line) > 3:
            counts["staged"] += line[2] != "."
            counts["modified"] += line[3] != "."
        elif line.startswith("? "):
            counts["untracked"] += 1
    return counts


def summary_text(counts):
    notes = []
    tree = [f"{counts[key]} {key}" for key in ("staged", "modified", "untracked") if counts[key]]
    if tree:
        notes.append("Working tree: " + ", ".join(tree))
    if counts["upstream"] and counts["ahead"]:
        notes.append(f"Unpushed: {counts['ahead']} commit(s) ahead of {counts['upstream']}")
    return ("Session summary: " + ". ".join(notes) + ".") if notes else ""


def changed_since_last_stop(data, text):
    """True when `text` differs from the summary recorded at this session's previous Stop.

    Records the new value either way (a clean tree records "", so returning to a dirty state is
    reported again). Without a session id, or with an unwritable marker, it answers True: a
    repeated summary is visible and harmless, a swallowed one is neither."""
    session = str(data.get("session_id") or "")
    if not session:
        return True
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session)
    marker = os.path.join(tempfile.gettempdir(), "sdh-hook-notices", f"stop-summary-{safe}")
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
    try:
        with open(marker, encoding="utf-8") as handle:
            previous = handle.read().strip()
    except OSError:
        previous = None
    try:
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        with open(marker, "w", encoding="utf-8") as handle:
            handle.write(digest)
    except OSError:
        return True
    return previous != digest


def main():
    try:
        data = json.load(sys.stdin)
    except (ValueError, OSError):
        data = {}
    data = data if isinstance(data, dict) else {}
    if data.get("stop_hook_active"):
        sys.exit(0)  # Claude is continuing because a Stop hook asked it to; the turn is not over
    status = git_status(str(data.get("cwd") or os.getcwd()))
    if status is None:
        sys.exit(0)
    text = summary_text(parse_counts(status))
    if changed_since_last_stop(data, text) and text:
        print(json.dumps({"systemMessage": text}))
    sys.exit(0)


if __name__ == "__main__":
    main()
