#!/usr/bin/env python3
"""
Hook test harness — runs all hook test cases and reports results.

Usage:
  python .claude/hooks/tests/run-all.py

Each test sends simulated tool_input JSON to a hook script via stdin
and asserts on the exit code and stdout output.
"""
import json
import subprocess
import sys
import os

HOOKS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PASS = 0
FAIL = 0


def run_hook(hook_script, tool_name, tool_input):
    """Run a hook script with simulated input and return (exit_code, stdout)."""
    data = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
    result = subprocess.run(
        [sys.executable, os.path.join(HOOKS_DIR, hook_script)],
        input=data,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return result.returncode, result.stdout.strip()


def run_prompt_hook(hook_script, prompt):
    """Run a UserPromptSubmit hook with simulated prompt and return (exit_code, stdout)."""
    data = json.dumps({"prompt": prompt})
    result = subprocess.run(
        [sys.executable, os.path.join(HOOKS_DIR, hook_script)],
        input=data,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return result.returncode, result.stdout.strip()


def assert_allowed(name, hook_script, tool_name, tool_input):
    """Assert the hook allows the action (exit 0, no deny output)."""
    global PASS, FAIL
    code, stdout = run_hook(hook_script, tool_name, tool_input)
    if code == 0 and "deny" not in stdout.lower():
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name} — exit={code}, output={stdout[:200]}")


def assert_blocked(name, hook_script, tool_name, tool_input):
    """Assert the hook blocks the action (deny in output or exit != 0)."""
    global PASS, FAIL
    code, stdout = run_hook(hook_script, tool_name, tool_input)
    if "deny" in stdout.lower() or code != 0:
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name} — expected block, got exit={code}, output={stdout[:200]}")


def assert_warns(name, hook_script, tool_name, tool_input):
    """Assert the hook produces a warning (ask in output)."""
    global PASS, FAIL
    code, stdout = run_hook(hook_script, tool_name, tool_input)
    if "ask" in stdout.lower() or "warn" in stdout.lower():
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name} — expected warning, got exit={code}, output={stdout[:200]}")


def assert_silent(name, hook_script, tool_name, tool_input):
    """Assert the hook exits 0 with no output (silent skip)."""
    global PASS, FAIL
    code, stdout = run_hook(hook_script, tool_name, tool_input)
    if code == 0 and stdout == "":
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name} — expected silent exit, got exit={code}, output={stdout[:200]}")


def assert_output_contains(name, hook_script, tool_name, tool_input, substring):
    """Assert the hook output contains a specific substring."""
    global PASS, FAIL
    code, stdout = run_hook(hook_script, tool_name, tool_input)
    if code == 0 and substring.lower() in stdout.lower():
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name} — expected '{substring}' in output, got exit={code}, output={stdout[:200]}")


def test_dangerous_command_blocker():
    print("\n[dangerous-command-blocker.py]")
    assert_blocked("blocks rm -rf /", "dangerous-command-blocker.py", "Bash",
                   {"command": "rm -rf /"})
    assert_blocked("blocks DROP TABLE", "dangerous-command-blocker.py", "Bash",
                   {"command": "psql -c 'DROP TABLE users;'"})
    assert_blocked("blocks sudo rm", "dangerous-command-blocker.py", "Bash",
                   {"command": "sudo rm -rf /var/data"})
    assert_blocked("blocks chmod 777", "dangerous-command-blocker.py", "Bash",
                   {"command": "chmod 777 /etc/passwd"})
    assert_allowed("allows safe git commands", "dangerous-command-blocker.py", "Bash",
                   {"command": "git status"})
    assert_allowed("allows npm commands", "dangerous-command-blocker.py", "Bash",
                   {"command": "npm run test"})
    assert_allowed("skips non-Bash tools", "dangerous-command-blocker.py", "Read",
                   {"file_path": "/etc/passwd"})


def test_migration_validator():
    print("\n[migration-validator.py]")
    assert_warns("warns on up without down", "migration-validator.py", "Write", {
        "file_path": "backend/db/migrate/20240101_add_column.rb",
        "content": "class AddColumn < ActiveRecord::Migration\n  def up\n    add_column :users, :age, :integer\n  end\nend"
    })
    assert_warns("warns on remove_column in change", "migration-validator.py", "Write", {
        "file_path": "backend/db/migrate/20240102_remove_field.rb",
        "content": "class RemoveField < ActiveRecord::Migration\n  def change\n    remove_column :users, :legacy_field\n  end\nend"
    })
    assert_warns("warns on SQL interpolation", "migration-validator.py", "Write", {
        "file_path": "backend/db/migrate/20240103_custom.rb",
        "content": 'class Custom < ActiveRecord::Migration\n  def up\n    execute "UPDATE users SET name = \'#{value}\'"\n  end\nend'
    })
    assert_allowed("allows safe migration", "migration-validator.py", "Write", {
        "file_path": "backend/db/migrate/20240104_safe.rb",
        "content": "class Safe < ActiveRecord::Migration\n  def change\n    add_column :users, :nickname, :string\n  end\nend"
    })
    assert_allowed("skips non-migration files", "migration-validator.py", "Write", {
        "file_path": "backend/app/models/user.rb",
        "content": "class User < ApplicationRecord\nend"
    })


def test_deployment_gate():
    print("\n[deployment-gate.py]")
    assert_warns("warns on git push to main", "deployment-gate.py", "Bash",
                 {"command": "git push origin main"})
    assert_warns("warns on force push", "deployment-gate.py", "Bash",
                 {"command": "git push -f origin feature"})
    # Terraform is owned by terraform-command-gate.py, not this hook — two hooks deciding
    # the same command meant a double prompt (approval fatigue) and, on -auto-approve,
    # contradictory decisions (ask vs deny).
    assert_silent("delegates terraform entirely to the three-tier gate", "deployment-gate.py",
                  "Bash", {"command": "terraform apply -auto-approve"})
    assert_warns("warns on vercel deploy", "deployment-gate.py", "Bash",
                 {"command": "vercel deploy --prod"})
    assert_warns("warns on docker push", "deployment-gate.py", "Bash",
                 {"command": "docker push myregistry/myapp:latest"})
    assert_allowed("allows safe commands", "deployment-gate.py", "Bash",
                   {"command": "npm run build"})
    assert_allowed("allows terraform plan", "deployment-gate.py", "Bash",
                   {"command": "terraform plan"})


def test_pre_commit_check():
    print("\n[pre-commit-check.py]")
    # Note: pre-commit-check.py behavior depends on implementation
    assert_allowed("allows non-git commands", "pre-commit-check.py", "Bash",
                   {"command": "npm test"})


def test_accessibility_checker():
    print("\n[accessibility-checker.py]")

    # --- Silent skips for non-matching files ---
    assert_silent("skips markdown files", "accessibility-checker.py", "Edit",
                  {"file_path": "README.md"})
    assert_silent("skips JSON config", "accessibility-checker.py", "Edit",
                  {"file_path": ".claude/settings.json"})
    assert_silent("skips Ruby files", "accessibility-checker.py", "Edit",
                  {"file_path": "backend/app/models/user.rb"})
    assert_silent("skips Python files", "accessibility-checker.py", "Edit",
                  {"file_path": ".claude/hooks/test-runner.py"})
    assert_silent("skips tsx outside web/next/frontend", "accessibility-checker.py", "Edit",
                  {"file_path": "mobile/src/components/Button.tsx"})
    assert_silent("skips empty input", "accessibility-checker.py", "Edit",
                  {"file_path": ""})

    # --- Warnings on matching files ---
    # Create temp test files for detection tests
    import tempfile, os
    tmpdir = tempfile.mkdtemp()
    web_dir = os.path.join(tmpdir, "web", "src", "components")
    os.makedirs(web_dir)

    # Test: div onClick detection
    div_click_file = os.path.join(web_dir, "BadButton.tsx")
    with open(div_click_file, "w") as f:
        f.write('<div onClick={() => handleClick()}>Click me</div>')
    assert_output_contains("warns on div onClick", "accessibility-checker.py", "Edit",
                           {"file_path": div_click_file}, "non-semantic")

    # Test: span onClick detection
    span_click_file = os.path.join(web_dir, "BadSpan.tsx")
    with open(span_click_file, "w") as f:
        f.write('<span onClick={toggle} className="link">Toggle</span>')
    assert_output_contains("warns on span onClick", "accessibility-checker.py", "Edit",
                           {"file_path": span_click_file}, "non-semantic")

    # Test: img without alt
    img_file = os.path.join(web_dir, "BadImage.tsx")
    with open(img_file, "w") as f:
        f.write('<img src="/logo.png" width={100} />')
    assert_output_contains("warns on img without alt", "accessibility-checker.py", "Edit",
                           {"file_path": img_file}, "alt text")

    # Test: Image (next/image) without alt
    next_dir = os.path.join(tmpdir, "next", "app", "components")
    os.makedirs(next_dir)
    next_img_file = os.path.join(next_dir, "Hero.tsx")
    with open(next_img_file, "w") as f:
        f.write('<Image src="/hero.jpg" width={800} height={400} />')
    assert_output_contains("warns on next/image without alt", "accessibility-checker.py", "Edit",
                           {"file_path": next_img_file}, "alt text")

    # Test: input without label
    input_file = os.path.join(web_dir, "BadForm.tsx")
    with open(input_file, "w") as f:
        f.write('<input type="text" id="email" placeholder="Email" />')
    assert_output_contains("warns on input without label", "accessibility-checker.py", "Edit",
                           {"file_path": input_file}, "label")

    # Test: outline:none
    outline_file = os.path.join(web_dir, "BadFocus.tsx")
    with open(outline_file, "w") as f:
        f.write('const style = { outline: none };\n<button style={style}>Go</button>')
    assert_output_contains("warns on outline:none", "accessibility-checker.py", "Edit",
                           {"file_path": outline_file}, "focus indicator")

    # Test: aria-hidden with onClick
    aria_file = os.path.join(web_dir, "BadAria.tsx")
    with open(aria_file, "w") as f:
        f.write('<div aria-hidden="true" onClick={close}>X</div>')
    assert_output_contains("warns on aria-hidden with onClick", "accessibility-checker.py", "Edit",
                           {"file_path": aria_file}, "hidden from assistive")

    # Test: clean file passes silently
    clean_file = os.path.join(web_dir, "GoodButton.tsx")
    with open(clean_file, "w") as f:
        f.write('<button onClick={handleClick}>Click me</button>\n<img src="/logo.png" alt="Company logo" />')
    assert_silent("no warnings on clean file", "accessibility-checker.py", "Edit",
                  {"file_path": clean_file})

    # Cleanup temp files
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


def test_api_design_checker():
    print("\n[api-design-checker.py]")

    # --- Silent skips for non-matching files ---
    assert_silent("skips markdown files", "api-design-checker.py", "Edit",
                  {"file_path": "README.md"})
    assert_silent("skips settings JSON", "api-design-checker.py", "Edit",
                  {"file_path": ".claude/settings.json"})
    assert_silent("skips model files", "api-design-checker.py", "Edit",
                  {"file_path": "backend/app/models/user.rb"})
    assert_silent("skips view files", "api-design-checker.py", "Edit",
                  {"file_path": "web/src/components/Button.tsx"})
    assert_silent("skips empty input", "api-design-checker.py", "Edit",
                  {"file_path": ""})

    # --- Warnings on matching files ---
    import tempfile, os
    tmpdir = tempfile.mkdtemp()
    ctrl_dir = os.path.join(tmpdir, "backend", "app", "controllers")
    os.makedirs(ctrl_dir)

    # Test: verb in route path
    verb_file = os.path.join(ctrl_dir, "routes.rb")
    with open(verb_file, "w") as f:
        f.write("get '/api/getUsers', to: 'users#index'\n")
    assert_output_contains("warns on verb in URL path", "api-design-checker.py", "Edit",
                           {"file_path": verb_file}, "verb")

    # Test: unwrapped array response (Rails)
    array_file = os.path.join(ctrl_dir, "users_controller.rb")
    with open(array_file, "w") as f:
        f.write("render json: [user1, user2, user3]\n")
    assert_output_contains("warns on unwrapped array (Rails)", "api-design-checker.py", "Edit",
                           {"file_path": array_file}, "data key")

    # Test: error response missing code/request_id
    error_file = os.path.join(ctrl_dir, "orders_controller.rb")
    with open(error_file, "w") as f:
        f.write('render json: { error: "Not found" }, status: :not_found\n')
    assert_output_contains("warns on error missing code/request_id", "api-design-checker.py", "Edit",
                           {"file_path": error_file}, "error response missing")

    # Test: POST create returning 200
    post_file = os.path.join(ctrl_dir, "items_controller.rb")
    with open(post_file, "w") as f:
        f.write("def create\n  item = Item.create!(params)\n  render json: item, status: :ok\nend\n")
    assert_output_contains("warns on POST returning 200", "api-design-checker.py", "Edit",
                           {"file_path": post_file}, "201")

    # Test: JS API unwrapped array
    api_dir = os.path.join(tmpdir, "mobile", "src", "api")
    os.makedirs(api_dir)
    js_array_file = os.path.join(api_dir, "users.ts")
    with open(js_array_file, "w") as f:
        f.write("res.json([user1, user2])\n")
    assert_output_contains("warns on unwrapped array (JS)", "api-design-checker.py", "Edit",
                           {"file_path": js_array_file}, "data key")

    # Test: clean controller passes silently
    clean_file = os.path.join(ctrl_dir, "clean_controller.rb")
    with open(clean_file, "w") as f:
        f.write("def index\n  render json: { data: users, meta: { total: count } }\nend\n")
    assert_silent("no warnings on clean controller", "api-design-checker.py", "Edit",
                  {"file_path": clean_file})

    # Cleanup temp files
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


def test_vague_request_detector():
    print("\n[vague-request-detector.py]")
    global PASS, FAIL

    # --- Vague requests should trigger interactive prompt ---
    def assert_interactive(name, prompt, expected_substring):
        global PASS, FAIL
        code, stdout = run_prompt_hook("vague-request-detector.py", prompt)
        if code == 0 and expected_substring.lower() in stdout.lower():
            PASS += 1
            print(f"  PASS: {name}")
        else:
            FAIL += 1
            print(f"  FAIL: {name} — expected '{expected_substring}' in output, got exit={code}, output={stdout[:200]}")

    def assert_no_trigger(name, prompt):
        global PASS, FAIL
        code, stdout = run_prompt_hook("vague-request-detector.py", prompt)
        if code == 0 and stdout == "":
            PASS += 1
            print(f"  PASS: {name}")
        else:
            FAIL += 1
            print(f"  FAIL: {name} — expected silent exit, got exit={code}, output={stdout[:200]}")

    # Vague requests that should trigger
    assert_interactive(
        "triggers on 'we need a feature'",
        "we need a notification feature",
        "AskUserQuestion",
    )
    assert_interactive(
        "triggers on 'make it better'",
        "make it better and faster",
        "AskUserQuestion",
    )
    assert_interactive(
        "triggers on 'like uber app'",
        "build something like uber app",
        "AskUserQuestion",
    )
    assert_interactive(
        "triggers on one-word feature",
        "add notifications",
        "AskUserQuestion",
    )
    assert_interactive(
        "includes requirements-consultant routing",
        "we want a chat system module",
        "requirements-consultant",
    )

    # Clear requests that should NOT trigger
    assert_no_trigger(
        "skips short prompts",
        "fix bug",
    )
    assert_no_trigger(
        "skips slash commands",
        "/code-reviewer check my PR",
    )
    assert_no_trigger(
        "skips explicit requirements work",
        "help me clarify requirements for the auth system",
    )
    assert_no_trigger(
        "skips user stories request",
        "write user stories for the checkout flow",
    )
    assert_no_trigger(
        "skips specific implementation request",
        "Add a created_at index to the orders table in the backend migration",
    )


def test_terraform_command_gate():
    """Ch. 10 Pattern 3 — the three-tier command gate: DENY the never-legitimate,
    ASK the serious-but-real, ALLOW (fall through) the read-only surface. Fail-closed."""
    print("\n[terraform-command-gate.py — three-tier command gate]")

    # Tier 1 — DENY the irreversible
    for name, cmd in [
        ("denies terraform destroy", "terraform destroy"),
        ("denies tofu destroy (OpenTofu)", "tofu destroy"),
        ("denies destroy with flags before subcommand", "terraform -chdir=prod destroy"),
        ("denies state rm (state surgery)", "terraform state rm aws_db_instance.main"),
        ("denies state mv", "terraform state mv a b"),
        ("denies state push", "terraform state push new.tfstate"),
        ("denies force-unlock", "terraform force-unlock 1234"),
        ("denies apply -auto-approve", "terraform apply -auto-approve"),
        ("denies apply --auto-approve", "terraform apply --auto-approve"),
    ]:
        assert_blocked(name, "terraform-command-gate.py", "Bash", {"command": cmd})

    # Tier 2 — ASK on a real apply
    assert_warns("asks on terraform apply (human confirms)", "terraform-command-gate.py", "Bash",
                 {"command": "terraform apply"})
    assert_output_contains("apply ask carries the review checklist", "terraform-command-gate.py",
                           "Bash", {"command": "terraform apply"}, "plan")

    # Tier 3 — ALLOW the read-only surface (must fall through silently)
    for name, cmd in [
        ("allows terraform plan", "terraform plan"),
        ("allows plan -destroy (a PREVIEW, not a destroy)", "terraform plan -destroy"),
        ("allows validate", "terraform validate"),
        ("allows fmt", "terraform fmt -check"),
        ("allows output", "terraform output -json"),
        ("allows state list (read-only)", "terraform state list"),
        ("allows state show (read-only)", "terraform state show aws_vpc.main"),
        ("ignores non-terraform commands", "npm run build"),
        ("ignores non-Bash tools", None),
    ]:
        if cmd is None:
            assert_silent(name, "terraform-command-gate.py", "Edit", {"file_path": "main.tf"})
        else:
            assert_silent(name, "terraform-command-gate.py", "Bash", {"command": cmd})


def test_fail_open_is_not_silent():
    """Ch. 9: "Silent failure is invisible failure." Advisory hooks fail OPEN (a crash
    must never block the edit) but must NOT fail silently — a swallowed exception makes
    a dead gate indistinguishable from a passing one. Every fail-open path must emit an
    actionable HOOK ERROR line naming the checker."""
    print("\n[fail-open visibility — dead gates must not look green]")
    global PASS, FAIL
    import tempfile, os, json as _json

    def run(script, event):
        r = subprocess.run([sys.executable, script], input=_json.dumps(event),
                           capture_output=True, text=True, timeout=15)
        return r.returncode, r.stdout

    ev = {"tool_name": "Write", "tool_input": {"file_path": "x.rb", "content": "x"}}

    def assert_visible(name, body, expect_token):
        global PASS, FAIL
        probe = os.path.join(HOOKS_DIR, "_failvis_probe.py")
        with open(probe, "w", encoding="utf-8") as f:
            f.write(body)
        try:
            code, out = run(probe, ev)
            ok = code == 0 and "HOOK ERROR" in out and expect_token in out
            if ok:
                PASS += 1; print(f"  PASS: {name}")
            else:
                FAIL += 1
                print(f"  FAIL: {name} — exit={code} stdout={out[:120]!r}")
        finally:
            if os.path.exists(probe):
                os.remove(probe)

    # a checker that raises must still exit 0 (fail-open) AND announce itself
    assert_visible(
        "crashing checker reports HOOK ERROR and still exits 0",
        'import _hooklib as hooklib\n'
        'def check(event):\n'
        '    raise RuntimeError("boom")\n'
        'if __name__ == "__main__":\n'
        '    hooklib.run_post_checker(check)\n',
        "boom",
    )
    # the error names the failing script so it is actionable
    assert_visible(
        "HOOK ERROR names the failing checker",
        'import _hooklib as hooklib\n'
        'def check(event):\n'
        '    raise ValueError("bad regex")\n'
        'if __name__ == "__main__":\n'
        '    hooklib.run_post_checker(check)\n',
        "_failvis_probe.py",
    )
    # a healthy checker stays quiet — the signal must not be noise
    probe = os.path.join(HOOKS_DIR, "_failvis_ok.py")
    with open(probe, "w", encoding="utf-8") as f:
        f.write('import _hooklib as hooklib\n'
                'def check(event):\n'
                '    return []\n'
                'if __name__ == "__main__":\n'
                '    hooklib.run_post_checker(check)\n')
    try:
        code, out = run(probe, ev)
        if code == 0 and out.strip() == "":
            PASS += 1; print("  PASS: healthy checker emits nothing (no false alarms)")
        else:
            FAIL += 1; print(f"  FAIL: healthy checker emitted {out[:80]!r}")
    finally:
        if os.path.exists(probe):
            os.remove(probe)

    # the dispatcher must report a broken checker rather than skipping it silently
    disp = os.path.join(HOOKS_DIR, "post-edit-dispatch.py")
    src = open(disp, encoding="utf-8").read()
    if "hook_error" in src and "except Exception as exc" in src:
        PASS += 1; print("  PASS: dispatcher reports a failing checker instead of skipping silently")
    else:
        FAIL += 1; print("  FAIL: dispatcher still swallows checker exceptions silently")

    # A GAP IN THE AUDIT TRAIL MUST ANNOUNCE ITSELF. A silent logging failure leaves
    # invisible holes plus false confidence the trail is complete — worse than no trail.
    import shutil
    root = tempfile.mkdtemp()
    try:
        # make .claude a FILE so both makedirs() and the append fail
        with open(os.path.join(root, ".claude"), "w") as f:
            f.write("not a dir")
        r = subprocess.run([sys.executable, os.path.join(HOOKS_DIR, "audit-logger.py")],
                           input=_json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}}),
                           capture_output=True, text=True, cwd=root, timeout=15)
        if r.returncode == 0 and "HOOK ERROR" in r.stdout and "gap" in r.stdout.lower():
            PASS += 1; print("  PASS: unwritable audit trail reports a gap (and never blocks)")
        else:
            FAIL += 1; print(f"  FAIL: audit trail gap was silent — exit={r.returncode} out={r.stdout[:90]!r}")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # a malformed event must not produce a raw traceback at the user
    r = subprocess.run([sys.executable, os.path.join(HOOKS_DIR, "vague-request-detector.py")],
                       input='{"prompt":', capture_output=True, text=True, timeout=15)
    if r.returncode == 0 and "Traceback" not in r.stdout + r.stderr and "HOOK ERROR" in r.stdout:
        PASS += 1; print("  PASS: malformed event reports one line, not a traceback")
    else:
        FAIL += 1; print(f"  FAIL: malformed event — exit={r.returncode} err={r.stderr[:80]!r}")


def test_permission_sentinel():
    """Layer-4 sentinel (the 'plugin trap'): a plugin cannot ship `permissions`, so
    the SessionStart hook must verify the deny floor was copied into the consuming
    project and warn loudly when it wasn't. Silent absence -> visible warning."""
    print("\n[session-start-check.py — permission sentinel]")
    global PASS, FAIL
    import tempfile, os, shutil, json as _json

    def run_session_start(cwd):
        result = subprocess.run(
            [sys.executable, os.path.join(HOOKS_DIR, "session-start-check.py")],
            input=_json.dumps({"cwd": cwd}),
            capture_output=True, text=True, timeout=15,
        )
        return result.returncode, result.stdout

    def case(name, deny, expect_gap, write_settings=True, raw=None):
        global PASS, FAIL
        root = tempfile.mkdtemp()
        try:
            if write_settings:
                os.makedirs(os.path.join(root, ".claude"))
                p = os.path.join(root, ".claude", "settings.json")
                with open(p, "w", encoding="utf-8") as f:
                    if raw is not None:
                        f.write(raw)
                    else:
                        _json.dump({"permissions": {"deny": deny}}, f)
            code, out = run_session_start(root.replace("\\", "/"))
            got_gap = "GOVERNANCE GAP" in out
            if code == 0 and got_gap == expect_gap:
                PASS += 1
                print(f"  PASS: {name}")
            else:
                FAIL += 1
                print(f"  FAIL: {name} — exit={code} gap={got_gap} expected_gap={expect_gap}")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    full = ["Read(**/.env)", "Read(**/secrets/**)", "Bash(sudo:*)", "Bash(curl * | bash)"]
    case("silent when the full permission floor is present", full, expect_gap=False)
    case("warns when a sentinel deny is missing", full[:2], expect_gap=True)
    case("warns when the deny list is empty", [], expect_gap=True)
    case("warns when .claude/settings.json is absent", None, expect_gap=True, write_settings=False)
    case("warns when settings.json is unparseable", None, expect_gap=True, raw="{ not json")
    # never blocks the session
    case("exits 0 even on a gap (informational, never blocks)", [], expect_gap=True)


def test_hooklib_primitives():
    """Unit-test the wrapper-agnostic matching primitives in _hooklib directly."""
    print("\n[_hooklib primitives]")
    global PASS, FAIL
    sys.path.insert(0, HOOKS_DIR)
    import _hooklib as h

    def check(name, got, want):
        global PASS, FAIL
        if got == want:
            PASS += 1
            print(f"  PASS: {name}")
        else:
            FAIL += 1
            print(f"  FAIL: {name} — got {got!r} want {want!r}")

    check("under matches standard wrapper", h.under("backend/app/models/u.rb", "app/models"), True)
    check("under matches non-standard wrapper", h.under("api/app/models/u.rb", "app/models"), True)
    check("under matches repo root", h.under("app/models/u.rb", "app/models"), True)
    check("under rejects partial segment", h.under("myapp/models/u.rb", "app/models"), False)
    check("replace_first_segment preserves wrapper",
          h.replace_first_segment("api/app/models/u.rb", "app", "spec"), "api/spec/models/u.rb")
    check("replace_first_segment src->tests",
          h.replace_first_segment("frontend/src/x.tsx", "src", "tests"), "frontend/tests/x.tsx")
    check("detect_framework path fallback (rails)", h.detect_framework("zz/app/models/u.rb"), "rails")
    check("detect_framework path fallback (react-native)", h.detect_framework("zz/src/screens/H.tsx"), "react-native")
    check("detect_framework path fallback (vite)", h.detect_framework("zz/src/pages/D.tsx"), "vite")


def test_wrapper_agnostic():
    """Conventions must auto-load regardless of the wrapper directory name.
    The SAME canonical structure under a NON-STANDARD wrapper (api/, server/,
    frontend/, platform/, ...) must trigger the same checkers as the standard
    layout. Each fixture is rooted at an isolated temp dir with a .git sentinel
    so detect_framework's ancestor walk does not leak markers between cases."""
    print("\n[wrapper-agnostic detection]")
    import tempfile, os, shutil

    def fixture(files):
        """Create an isolated project root (.git sentinel) with the given
        {relpath: content} files. Returns (root, {relpath: abs_forward_path})."""
        root = tempfile.mkdtemp()
        os.makedirs(os.path.join(root, ".git"))
        paths = {}
        for rel, content in files.items():
            full = os.path.join(root, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(content)
            paths[rel] = full.replace("\\", "/")
        return root, paths

    LOG_RB = 'class XController\n  def show\n    Rails.logger.info "hi"\n  end\nend\n'
    LONG_MODEL = "class User\n" + "\n".join("  # c%d" % i for i in range(205)) + "\nend\n"
    IMG = '<img src="/logo.png" width={100} />\n'

    # monitoring-checker: Rails controller under api/ (not backend/)
    root, p = fixture({"api/app/controllers/x_controller.rb": LOG_RB})
    assert_output_contains("monitoring warns under api/ wrapper", "monitoring-checker.py",
                           "Write", {"file_path": p["api/app/controllers/x_controller.rb"]}, "request_id")
    shutil.rmtree(root, ignore_errors=True)

    # code-quality-checker: 201-line Rails model under server/ (200-line model limit)
    root, p = fixture({"server/app/models/user.rb": LONG_MODEL})
    assert_output_contains("code-quality warns on long model under server/", "code-quality-checker.py",
                           "Write", {"file_path": p["server/app/models/user.rb"]}, "200-line")
    shutil.rmtree(root, ignore_errors=True)

    # api-design-checker: verb-in-path controller under api/
    root, p = fixture({"api/app/controllers/users_controller.rb": "get '/api/getUsers', to: 'users#index'\n"})
    assert_output_contains("api-design warns under api/ wrapper", "api-design-checker.py",
                           "Write", {"file_path": p["api/app/controllers/users_controller.rb"]}, "verb")
    shutil.rmtree(root, ignore_errors=True)

    # accessibility-checker: Vite web (vite.config marker) under frontend/ IS checked
    root, p = fixture({"frontend/vite.config.ts": "export default {}\n",
                       "frontend/src/components/Hero.tsx": IMG})
    assert_output_contains("accessibility warns for Vite under frontend/", "accessibility-checker.py",
                           "Write", {"file_path": p["frontend/src/components/Hero.tsx"]}, "alt text")
    shutil.rmtree(root, ignore_errors=True)

    # accessibility-checker: React Native (react-native + metro markers) IS skipped
    root, p = fixture({"client/package.json": '{"dependencies":{"react-native":"0.74.0"}}',
                       "client/metro.config.js": "module.exports = {}\n",
                       "client/src/components/Hero.tsx": IMG})
    assert_silent("accessibility skips React Native (marker-detected)", "accessibility-checker.py",
                  "Write", {"file_path": p["client/src/components/Hero.tsx"]})
    shutil.rmtree(root, ignore_errors=True)

    # test-coverage-checker: source under platform/ wrapper warns when no test exists
    root, p = fixture({"platform/src/utils/helpers.ts": "export const f = () => 1;\n"})
    assert_output_contains("test-coverage warns under platform/ wrapper", "test-coverage-checker.py",
                           "Write", {"file_path": p["platform/src/utils/helpers.ts"]}, "No test file")
    shutil.rmtree(root, ignore_errors=True)

    # negative: a model (not controller/job) stays silent for monitoring under any wrapper
    root, p = fixture({"api/app/models/user.rb": 'Rails.logger.info "x"\n'})
    assert_silent("monitoring silent for non-controller under api/", "monitoring-checker.py",
                  "Write", {"file_path": p["api/app/models/user.rb"]})
    shutil.rmtree(root, ignore_errors=True)


def main():
    print("=" * 60)
    print("Hook Test Harness")
    print("=" * 60)

    test_dangerous_command_blocker()
    test_migration_validator()
    test_deployment_gate()
    test_pre_commit_check()
    test_accessibility_checker()
    test_api_design_checker()
    test_terraform_command_gate()
    test_fail_open_is_not_silent()
    test_permission_sentinel()
    test_hooklib_primitives()
    test_wrapper_agnostic()
    test_vague_request_detector()

    print("\n" + "=" * 60)
    print(f"Results: {PASS} passed, {FAIL} failed")
    print("=" * 60)

    sys.exit(1 if FAIL > 0 else 0)


if __name__ == "__main__":
    main()
