# Hook Development & Debugging

How to write, test, and debug the `sdh` plugin's hooks. Based on *The Governed Agent* Ch. 9 (the
development workflow), Ch. 22 (the fixture harness as standing audit), and Ch. 25 (debugging).

---

## The development loop

**Hooks written blind and tested in a live session are how you get defects.** Do this instead:

### 1. Capture a real event — don't guess at the schema

```jsonc
// temporarily, in your project's .claude/settings.json
{"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
  {"type": "command", "command": "bash hooks/run-python.sh hooks/capture-event.py"}]}]}}
```

Trigger the tool once → a real fixture lands in `hooks/tests/fixtures/`.

### 2. Develop against the fixture, not the session

```bash
python hooks/my-gate.py < hooks/tests/fixtures/PreToolUse-Bash-1784092811.json; echo "exit: $?"
```

A sub-second loop. The alternative — edit, start a session, trigger the tool, squint at the output
— is a minute-long loop you will run fifty times.

### 3. Decide the fail stance *consciously*

Before writing the logic, answer: **when this hook crashes, what should happen?** See the stance
table in [`hooks/README.md`](../hooks/README.md). Security gates fail **closed**; advisory hooks
fail **open** — but never *silently* (see below).

### 4. Write it against `_hooklib`

```python
import _hooklib as hooklib

def check(event):
    if hooklib.tool_name(event) != "Bash":
        return
    ...
    hooklib.deny("BLOCKED: X is not allowed. Do Y instead.")   # ALWAYS name the remedy

if __name__ == "__main__":
    hooklib.run_pre_blocker(check, fail_closed=True, gate_label="my-gate")
```

Advisory checkers use `check(event) -> list[str]` + `hooklib.run_post_checker(check)`, and are
dispatched in-process by `post-edit-dispatch.py` (add the filename to its `CHECKERS` list).

### 5. Test it — hooks are code

Add cases to `hooks/tests/run-all.py` and run:

```bash
bash hooks/run-python.sh hooks/tests/run-all.py
```

A guarantee that isn't tested is a guarantee that decays. The harness is also a **standing audit**:
it enforces that fail-open paths stay visible, that every deny reason names a remedy, and that the
sentinel detects a stale floor.

---

## The first move when something is wrong: observe, don't guess

> Most "the agent ignored my rule" reports are really "my rule never loaded" or "my hook never ran"
> — different bugs, different fixes than the ones people reach for.

1. **Check what's registered.** `/hooks` shows the actually-loaded configuration. Configuration you
   wrote but haven't confirmed loaded is configuration you're *imagining*. Half of hook debugging
   ends here: registered under the wrong event, or silently dropped by a JSON syntax error.
2. **Run the hook by hand.** The single most useful diagnostic:
   ```bash
   echo '{"tool_name":"Bash","tool_input":{"command":"terraform destroy"}}' \
     | bash hooks/run-python.sh hooks/terraform-command-gate.py; echo "exit: $?"
   ```
   Right decision by hand ⇒ the bug is in **registration or matching**. Wrong decision ⇒ the bug is
   in the **script**.
3. **Read the agent definition, not your memory of it.** *"The tool list you remember writing and
   the tool list on disk diverge more often than pride admits."*

---

## Symptom → cause

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| **Hook never fires** | Not registered, wrong event, or the `matcher` doesn't match the tool. In this plugin, hooks live in `hooks/hooks.json` — **not** `.claude/settings.json`. | `/hooks` to confirm it loaded; check the matcher (`Bash`, `Edit\|Write`); confirm the command uses `${CLAUDE_PLUGIN_ROOT}`. |
| **Hook fires but never blocks** | **The most serious symptom — the system *looks* protected.** A PreToolUse gate must emit `permissionDecision: deny` JSON; exiting non-zero does not block. | Run by hand and inspect stdout. Confirm it routes through `hooklib.deny()`. Check the fixture-harness `assert_blocked` cases. |
| **Gate blocks everything** | The inverse emergency: a **fail-closed** gate crashing on every event (schema change, missing binary, a bug). Because it fails closed *correctly*, everything denies. | Run it by hand against a *normal* event. The deny reason will name the gate and the exception (`the … hook errored and is failing closed`). |
| **A checker enforces nothing, but everything looks green** | A dead gate masquerading as a green one. This is why fail-open paths here emit `HOOK ERROR: <checker> failed …` — a swallowed exception is indistinguishable from a pass. | Grep the session output for `HOOK ERROR`. Never re-introduce a bare `except: pass` in a checker. |
| **The model argues with a denial / retries variations** | The reason names *what* is forbidden but not *what to do instead*. **"Denied" invites retries; "denied because X, do Y instead" invites Y.** | Rewrite the reason to name the remedy. Guarded by the `[deny reasons must name a remedy]` test. |
| **An agent edited what it shouldn't** | The **read-only lie**: the agent has `Bash`, which *is* edit access (`sed -i`, `echo >`). A "review-only" agent with Bash is theater. | Remove `Bash` from the tool list, or constrain it with permission rules. Note `permissionMode` is **silently ignored** for plugin-shipped agents — the tool list is the real control. |
| **A deny that should fire doesn't** | The **permission layer was never copied** — a plugin cannot ship `permissions`, so the floor may be absent or **stale**. | The SessionStart sentinel names the exact missing rules. Re-copy the `permissions` block from the plugin's `.claude/settings.json`. |
| **Skill won't load / loads for everything** | Its `paths:` glob is wrong, too narrow, or too broad. Detection here is wrapper-agnostic — globs match canonical structure (`**/app/**/*.rb`), not a folder name. | Check the skill's frontmatter `paths:`. CI's tier-discipline job catches unindexed rules and broken references. |
| **Sessions feel slow** | Per-edit hook cost. The 12 advisory checkers run in **one** process via `post-edit-dispatch.py`; `auto-format` is separate because formatters are slow. | Don't re-split the dispatcher. Check whether a checker reads large files. `CLAUDE_HOOKS_DEBUG=1` shows the interpreter the launcher picked. |

---

## Gotchas specific to this plugin

- **`${CLAUDE_PLUGIN_ROOT}`** — hook commands in `hooks/hooks.json` must use it; a bare
  `hooks/…` path only works when the cwd happens to be the plugin root. CI enforces this.
- **Windows** — `run-python.sh` forces `PYTHONUTF8=1` (Python otherwise emits cp1252 and Claude
  Code reads UTF-8, producing `�`), skips the broken Microsoft Store `python3` stub, and **must**
  keep LF line endings (`.gitattributes` pins it; CRLF gives `bad interpreter: …^M`).
- **MSYS paths** — Git Bash `/tmp/...` paths are not resolvable by Windows-native Python. When
  writing fixtures by hand, use Windows-form paths (`E:/...`) or the tests will silently read empty
  files and pass for the wrong reason.
- **`json.load(sys.stdin)` outside a try** is the classic crash. Use `hooklib.load_event()`.
