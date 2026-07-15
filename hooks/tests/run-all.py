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
    assert_warns("warns on remove_column WITHOUT a type (genuinely irreversible)",
                 "migration-validator.py", "Write", {
        "file_path": "backend/db/migrate/20240102_remove_field.rb",
        "content": "class RemoveField < ActiveRecord::Migration[7.1]\n  def change\n    remove_column :users, :legacy_field\n  end\nend"
    })
    # The gate must not fire on the form the db-migration guide recommends. ActiveRecord CAN
    # invert `remove_column` when the type is present, so warning here would flag correct code
    # — and a gate that cries wolf is one people learn to click through.
    assert_allowed("allows remove_column WITH a type (reversible — the recommended form)",
                   "migration-validator.py", "Write", {
        "file_path": "backend/db/migrate/20240102_remove_typed.rb",
        "content": "class RemoveTyped < ActiveRecord::Migration[7.1]\n  def change\n    remove_column :users, :legacy_field, :string\n  end\nend"
    })
    # rename_column is reversible — so it must NOT be called irreversible. It is still risky,
    # for a different reason, and the reason must name the real remedy.
    assert_output_contains("rename_column warns about rolling deploys, not reversibility",
                           "migration-validator.py", "Write", {
        "file_path": "backend/db/migrate/20240105_rename.rb",
        "content": "class Rename < ActiveRecord::Migration[7.1]\n  def change\n    rename_column :users, :name, :full_name\n  end\nend"
    }, "expand/contract")
    assert_allowed("allows drop_table WITH a block (reversible)",
                   "migration-validator.py", "Write", {
        "file_path": "backend/db/migrate/20240106_drop.rb",
        "content": "class Drop < ActiveRecord::Migration[7.1]\n  def change\n    drop_table :legacy do |t|\n      t.string :name\n    end\n  end\nend"
    })
    # Wrapper-agnostic: a repo that does not use `backend/` must still be validated.
    assert_warns("validates migrations under any wrapper (api/db/migrate)",
                 "migration-validator.py", "Write", {
        "file_path": "api/db/migrate/20240107_remove_field.rb",
        "content": "class RemoveField < ActiveRecord::Migration[7.1]\n  def change\n    remove_column :users, :legacy_field\n  end\nend"
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


def test_ci_workflow_is_loadable():
    """Layer 7 must not vanish silently. A workflow file that does not parse is simply
    never run — GitHub reports nothing, every local signal stays green, and the external
    backstop is gone. That is the "dead gate masquerading as a green one" failure one
    layer up, so it gets the same treatment: a test."""
    print("\n[CI workflow — layer 7 must not vanish silently]")
    global PASS, FAIL
    import yaml

    wf = os.path.join(HOOKS_DIR, "..", ".github", "workflows", "ci.yml")
    if not os.path.isfile(wf):
        FAIL += 1
        print("  FAIL: .github/workflows/ci.yml is missing — layer 7 has no CI at all")
        return
    try:
        doc = yaml.safe_load(open(wf, encoding="utf-8"))
    except Exception as exc:
        FAIL += 1
        print(f"  FAIL: ci.yml does not parse — GitHub would silently never run it: {exc}")
        return

    PASS += 1
    print("  PASS: ci.yml parses (GitHub will actually run it)")

    jobs = doc.get("jobs") or {}
    # The gates that must exist for the plugin to practise the discipline it enforces.
    required = ["hook-fixtures", "plugin-manifest", "skills-lint", "sentinel-guard"]
    missing = [j for j in required if j not in jobs]
    if missing:
        FAIL += 1
        print(f"  FAIL: ci.yml lost required job(s): {missing}")
    else:
        PASS += 1
        print(f"  PASS: all required CI jobs present ({len(jobs)} jobs)")

    # Each job's inline python must at least be syntactically valid, or the job fails at
    # runtime for a reason no local check would have caught.
    import ast, re
    bad = []
    raw = open(wf, encoding="utf-8").read()
    for block in re.findall(r"python - <<'EOF'\n(.*?)\n\s*EOF", raw, re.S):
        src = "\n".join(line[10:] if line.startswith(" " * 10) else line.lstrip()
                        for line in block.split("\n"))
        try:
            ast.parse(src)
        except SyntaxError as exc:
            bad.append(str(exc).split("(")[0].strip())
    if bad:
        FAIL += 1
        print(f"  FAIL: inline CI python has syntax errors: {bad}")
    else:
        PASS += 1
        print("  PASS: every inline CI python block parses")


def test_deny_reasons_name_a_remedy():
    """Ch. 25 — "the model argues with a denial". Root cause: the reason names what is
    forbidden but not what to do INSTEAD. "Denied" invites retries; "denied because X,
    do Y instead" invites Y. Every deny reason must therefore name a remedy."""
    print("\n[deny reasons must name a remedy]")
    global PASS, FAIL
    import re, glob

    # A remedy tells the agent what to DO: an alternative action, or where to go.
    REMEDY = re.compile(
        r"instead|manual|prefer|revert|review it|open a pr|expected:|"
        r"use `|run `|`git |plan first|outside claude code",
        re.I,
    )
    checked = 0
    for path in sorted(glob.glob(os.path.join(HOOKS_DIR, "*.py"))):
        src = open(path, encoding="utf-8").read()
        for m in re.finditer(r'hooklib\.deny\(\s*((?:\s*(?:f?"[^"]*"|\'[^\']*\')\s*)+)', src):
            reason = " ".join(re.findall(r'"([^"]*)"', m.group(1)))
            if not reason.strip():
                continue
            checked += 1
            name = os.path.basename(path)
            if REMEDY.search(reason):
                PASS += 1
                print(f"  PASS: {name} deny names a remedy — {reason[:44].strip()}…")
            else:
                FAIL += 1
                print(f"  FAIL: {name} deny states a prohibition with NO remedy — {reason[:70]!r}")
    if checked == 0:
        FAIL += 1
        print("  FAIL: found no deny reasons to audit (regex drifted?)")


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

    # The authoritative floor is the plugin's own reference settings — so the check is
    # self-maintaining and detects a STALE floor, not just an absent one.
    ref = _json.load(open(os.path.join(HOOKS_DIR, "..", ".claude", "settings.json"),
                          encoding="utf-8"))["permissions"]["deny"]

    case("silent when the CURRENT floor is copied in full", ref, expect_gap=False)
    case("warns when the deny list is empty", [], expect_gap=True)
    case("warns when .claude/settings.json is absent", None, expect_gap=True, write_settings=False)
    case("warns when settings.json is unparseable", None, expect_gap=True, raw="{ not json")
    case("exits 0 even on a gap (informational, never blocks)", [], expect_gap=True)

    # STALENESS: a floor copied from an older plugin version is silently incomplete.
    # A hardcoded sample can prove a floor is ABSENT but never that it is CURRENT.
    stale = [r for r in ref if "terraform" not in r and "tofu" not in r]

    def stale_case(name, deny, expect_stale_wording):
        global PASS, FAIL
        root = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(root, ".claude"))
            with open(os.path.join(root, ".claude", "settings.json"), "w", encoding="utf-8") as f:
                _json.dump({"permissions": {"deny": deny}}, f)
            code, out = run_session_start(root.replace("\\", "/"))
            ok = code == 0 and ("STALE" in out) == expect_stale_wording
            if ok:
                PASS += 1; print(f"  PASS: {name}")
            else:
                FAIL += 1; print(f"  FAIL: {name} — out={out[:110]!r}")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    import shutil
    stale_case("detects a STALE floor (older copy, missing newer denies)", stale, True)
    stale_case("an empty floor reads as absent, not stale", [], False)

    # and it must name the exact missing rules, not just say 'something is missing'
    root = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(root, ".claude"))
        with open(os.path.join(root, ".claude", "settings.json"), "w", encoding="utf-8") as f:
            _json.dump({"permissions": {"deny": stale}}, f)
        code, out = run_session_start(root.replace("\\", "/"))
        if "terraform destroy" in out and f"of {len(ref)}" in out:
            PASS += 1; print("  PASS: names the exact missing rules and the floor size")
        else:
            FAIL += 1; print(f"  FAIL: gap message not actionable — {out[:110]!r}")
    finally:
        shutil.rmtree(root, ignore_errors=True)


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


def run_hook_env(hook_script, payload, env_extra):
    """Run a hook with extra environment, returning (exit_code, stdout)."""
    env = dict(os.environ)
    env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, os.path.join(HOOKS_DIR, hook_script)],
        input=json.dumps(payload), capture_output=True, text=True, timeout=15, env=env,
    )
    return proc.returncode, proc.stdout.strip()


def test_configurable_at_the_edges():
    """Ch. 13 — "It's configurable at the edges": hard-coding a team's branch names makes
    the plugin unusable in a repo that calls its trunk something else, and "test the plugin
    in a repo that isn't yours before shipping it". The core rule (don't push straight to
    the trunk) is universal; WHICH branches are the trunk is a parameter. Defaults must not
    change, or this is a silent behavioural break for every existing consumer."""
    print("\n[configurable at the edges — SDH_PROTECTED_BRANCHES]")
    global PASS, FAIL

    # 1. Defaults unchanged: main/master/develop still gated with no env set.
    for branch in ("main", "master", "develop"):
        code, out = run_hook_env("pre-commit-check.py",
                                 {"tool_name": "Bash", "tool_input": {"command": f"git push origin {branch}"}},
                                 {"SDH_PROTECTED_BRANCHES": ""})
        if '"permissionDecision": "ask"' in out and f"'{branch}'" in out:
            PASS += 1
            print(f"  PASS: default still gates a direct push to {branch}")
        else:
            FAIL += 1
            print(f"  FAIL: default no longer gates a direct push to {branch} — silent break: {out[:120]}")

    # 2. A repo whose trunk is `trunk` can protect it.
    code, out = run_hook_env("pre-commit-check.py",
                             {"tool_name": "Bash", "tool_input": {"command": "git push origin trunk"}},
                             {"SDH_PROTECTED_BRANCHES": "trunk,release-line"})
    if "trunk" in out and ("ask" in out.lower() or "deny" in out.lower()):
        PASS += 1
        print("  PASS: SDH_PROTECTED_BRANCHES=trunk gates a push to trunk")
    else:
        FAIL += 1
        print(f"  FAIL: override did not gate the configured trunk: {out[:160]}")

    # 3. Overriding must actually REPLACE the defaults, or the override is decorative.
    code, out = run_hook_env("pre-commit-check.py",
                             {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}},
                             {"SDH_PROTECTED_BRANCHES": "trunk"})
    if "permissionDecision" not in out:
        PASS += 1
        print("  PASS: override replaces the defaults (main not gated when trunk is the trunk)")
    else:
        FAIL += 1
        print(f"  FAIL: override did not replace defaults — main still gated: {out[:120]}")

    # 4. A blank override means "unset", not "protect nothing" — the unprotected
    #    reading is the dangerous one, so it must fall back to the defaults.
    code, out = run_hook_env("pre-commit-check.py",
                             {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}},
                             {"SDH_PROTECTED_BRANCHES": "   ,  ,"})
    if "permissionDecision" in out:
        PASS += 1
        print("  PASS: a blank override falls back to defaults (does not silently unprotect)")
    else:
        FAIL += 1
        print("  FAIL: a blank SDH_PROTECTED_BRANCHES silently unprotected every branch")

    # 5. Regex-special branch names must not corrupt the pattern.
    code, out = run_hook_env("pre-commit-check.py",
                             {"tool_name": "Bash", "tool_input": {"command": "git push origin release/v1.0"}},
                             {"SDH_PROTECTED_BRANCHES": "release/v1.0"})
    if "permissionDecision" in out:
        PASS += 1
        print("  PASS: branch names with regex metacharacters are escaped, not broken")
    else:
        FAIL += 1
        print(f"  FAIL: a branch name with '/' or '.' broke the pattern: {out[:120]}")


def test_missing_tool_says_so_once():
    """Ch. 13 — a hook whose tool is missing "should say so once and exit 0, not crash on
    every write". Both failure modes are real: crashing punishes a repo we did not design
    for not having our toolchain, and exiting silently is Ch. 9's "silent failure is
    invisible failure" — the user watches formatting never happen and never learns why."""
    print("\n[works on day one — a missing formatter says so once]")
    global PASS, FAIL
    import shutil
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        target = os.path.join(tmp, "example.rb")
        with open(target, "w", encoding="utf-8") as fh:
            fh.write("puts 1\n")

        notices = os.path.join(tmp, "notices")
        payload = {"session_id": "sess-abc", "tool_name": "Write",
                   "tool_input": {"file_path": target}}
        # An empty PATH guarantees no formatter is found, whatever the machine has.
        env = {"PATH": os.path.join(tmp, "empty-bin"), "TMPDIR": notices, "TEMP": notices,
               "TMP": notices}
        os.makedirs(os.path.join(tmp, "empty-bin"), exist_ok=True)
        os.makedirs(notices, exist_ok=True)

        code1, out1 = run_hook_env("auto-format.py", payload, env)
        code2, out2 = run_hook_env("auto-format.py", payload, env)

        if code1 == 0 and code2 == 0:
            PASS += 1
            print("  PASS: a missing formatter never blocks the edit (exit 0 both times)")
        else:
            FAIL += 1
            print(f"  FAIL: a missing formatter changed the exit code ({code1}, {code2})")

        if "rubocop" in out1 and "not on PATH" in out1:
            PASS += 1
            print("  PASS: first edit names the missing binary (not silent)")
        else:
            FAIL += 1
            print(f"  FAIL: first edit said nothing about the missing formatter: {out1!r}")

        if "gem install rubocop" in out1:
            PASS += 1
            print("  PASS: the notice names a remedy, not just a gap")
        else:
            FAIL += 1
            print(f"  FAIL: the notice does not say how to fix it: {out1!r}")

        if out2 == "":
            PASS += 1
            print("  PASS: the second edit is silent (said ONCE, not on every write)")
        else:
            FAIL += 1
            print(f"  FAIL: the notice repeats on every write — that is noise: {out2!r}")

        # A different session must hear it again — the notice is per-session, not forever.
        code3, out3 = run_hook_env("auto-format.py", dict(payload, session_id="sess-xyz"), env)
        if "rubocop" in out3:
            PASS += 1
            print("  PASS: a new session hears the notice again (per-session, not once ever)")
        else:
            FAIL += 1
            print(f"  FAIL: a new session never learns the formatter is missing: {out3!r}")


def test_commit_types_match_the_skill():
    """`pre-commit-check.py` BLOCKS a commit whose type is not in its pattern, and its message
    names the `std-git-workflow` skill. So that pattern is a hard interface: a type the hook
    accepts but the skill omits is undiscoverable except by being denied, and a type the skill
    documents but the hook rejects is a documented instruction that cannot be followed.

    The hook accepted `revert`; neither the skill nor CLAUDE.md mentioned it. Same shape as the
    200-vs-300 line limit: a list in code and a list in prose drift silently."""
    print("\n[commit types: the blocking list must equal the documented list]")
    global PASS, FAIL
    import re as _re

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))
    hook_src = open(os.path.join(HOOKS_DIR, "pre-commit-check.py"), encoding="utf-8").read()
    m = _re.search(r"r'\^\(([a-z|]+)\)", hook_src)
    if not m:
        FAIL += 1
        print("  FAIL: could not find the conventional-commit pattern — did it move?")
        return
    hook_types = set(m.group(1).split("|"))

    skill_path = os.path.join(repo, "skills", "std-git-workflow", "SKILL.md")
    skill_types = set(_re.findall(r"^\| `([a-z]+)`", open(skill_path, encoding="utf-8").read(), _re.M))

    blocked = skill_types - hook_types          # documented, but the hook denies it
    undocumented = hook_types - skill_types     # accepted, but nobody can find it

    if blocked:
        FAIL += 1
        print(f"  FAIL: std-git-workflow documents {sorted(blocked)}, which the hook BLOCKS — "
              f"a documented instruction that cannot be followed")
    else:
        PASS += 1
        print("  PASS: every documented type is accepted by the hook")

    if undocumented:
        FAIL += 1
        print(f"  FAIL: the hook accepts {sorted(undocumented)} but the skill never lists them — "
              f"undiscoverable except by being denied")
    else:
        PASS += 1
        print(f"  PASS: every accepted type is documented ({len(hook_types)} types)")

    # Live fire, both directions.
    ok = run_hook("pre-commit-check.py", "Bash",
                  {"command": 'git commit -m "revert: feat(auth): add SSO login"'})[1]
    if "permissionDecision" not in ok or "deny" not in ok.lower():
        PASS += 1
        print("  PASS: a documented type ('revert') is actually accepted")
    else:
        FAIL += 1
        print(f"  FAIL: 'revert' is documented but denied: {ok[:120]}")

    bad = run_hook("pre-commit-check.py", "Bash",
                   {"command": 'git commit -m "wibble: do a thing"'})[1]
    if "deny" in bad.lower():
        PASS += 1
        print("  PASS: an undocumented type is still blocked (the gate is live)")
    else:
        FAIL += 1
        print("  FAIL: the conventional-commit gate accepts anything")


def test_autoformat_never_changes_semantics():
    """A formatter may reshape code; it must not change what the code MEANS.

    `auto-format.py` runs unattended on every write, with stdout/stderr sent to DEVNULL. It
    used to run `rubocop --autocorrect-all` — which RuboCop's own CLI documents as "Autocorrect
    offenses (safe and unsafe)", against a default config that marks 53 cops
    `SafeAutoCorrect: false`. So it silently applied corrections RuboCop's maintainers flag as
    able to change behaviour, to code nobody re-read.

    `-a/--autocorrect` is "only when it's safe". Unsafe corrections are a deliberate human act."""
    print("\n[auto-format must not silently change semantics]")
    global PASS, FAIL
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "af", os.path.join(HOOKS_DIR, "auto-format.py"))
    af = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(af)

    unsafe_flags = {"--autocorrect-all", "-A", "--auto-correct-all"}
    offenders = []
    for ext, (binary, cmd) in af.FORMATTER_MAP.items():
        bad = unsafe_flags.intersection(cmd)
        if bad:
            offenders.append(f".{ext} runs {binary} with {sorted(bad)}")
    if offenders:
        FAIL += 1
        print(f"  FAIL: unattended formatter applies UNSAFE corrections: {offenders}")
    else:
        PASS += 1
        print("  PASS: no formatter runs an unsafe-autocorrect flag unattended")

    # Ruby must still be autocorrected — the safe half is the whole point of the hook.
    rb = af.FORMATTER_MAP.get("rb")
    if rb and "--autocorrect" in rb[1]:
        PASS += 1
        print("  PASS: .rb still autocorrects, with the safe flag")
    else:
        FAIL += 1
        print(f"  FAIL: .rb lost its autocorrect entirely: {rb}")

    # The other formatters are layout-only by nature; assert they stayed that way.
    for ext, expect in (("ts", "prettier"), ("py", "black"), ("tf", "terraform")):
        entry = af.FORMATTER_MAP.get(ext)
        if entry and entry[0] == expect:
            PASS += 1
            print(f"  PASS: .{ext} -> {expect} (layout only, no semantic rewrites)")
        else:
            FAIL += 1
            print(f"  FAIL: .{ext} formatter changed unexpectedly: {entry}")


def test_limits_match_the_skill_that_documents_them():
    """A gate whose number disagrees with the skill it names is worse than no gate: the
    developer reads the skill, writes to that number, gets warned anyway, and concludes the
    hook is noise. `code-quality-checker.py` warns at 200 lines for models/components and names
    the `std-code-standards` skill — which said only "300" and never mentioned 200.

    Numbers in code and numbers in prose drift silently. This is the same shape as the rule
    taxonomy check: gate the invariant that the two agree."""
    print("\n[enforced limits must match the skill that documents them]")
    global PASS, FAIL
    import importlib.util

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))
    spec = importlib.util.spec_from_file_location(
        "cqc", os.path.join(HOOKS_DIR, "code-quality-checker.py"))
    cqc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cqc)

    skill = os.path.join(repo, "skills", "std-code-standards", "SKILL.md")
    body = open(skill, encoding="utf-8").read()

    # Every number the hook enforces must appear in the skill that its message points at.
    enforced = {
        "MODEL_LIMIT": cqc.MODEL_LIMIT,
        "COMPONENT_LIMIT": cqc.COMPONENT_LIMIT,
        "DEFAULT_LIMIT": cqc.DEFAULT_LIMIT,
        "MAX_FUNCTION_LINES": cqc.MAX_FUNCTION_LINES,
        "MAX_PARAMS": cqc.MAX_PARAMS,
        "MAX_NESTING": cqc.MAX_NESTING,
    }
    missing = [f"{k}={v}" for k, v in enforced.items() if str(v) not in body]
    if missing:
        FAIL += 1
        print(f"  FAIL: std-code-standards never states: {', '.join(missing)} — the hook warns on "
              f"numbers the skill it names does not document")
    else:
        PASS += 1
        print(f"  PASS: all {len(enforced)} enforced limits are documented in std-code-standards")

    # The always-on skill consumers actually get must agree too (a plugin's CLAUDE.md is NOT
    # shipped as consumer context, so documenting a limit only there reaches nobody).
    always_on = os.path.join(repo, "skills", "sdh-engineering-standards", "SKILL.md")
    if os.path.isfile(always_on):
        text = open(always_on, encoding="utf-8").read()
        gaps = [str(v) for v in (cqc.MODEL_LIMIT, cqc.DEFAULT_LIMIT, cqc.MAX_FUNCTION_LINES)
                if str(v) not in text]
        if gaps:
            FAIL += 1
            print(f"  FAIL: sdh-engineering-standards (always-on) omits: {', '.join(gaps)}")
        else:
            PASS += 1
            print("  PASS: the always-on skill states the same headline limits")

    # And prove the gate fires: a model over MODEL_LIMIT must warn.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        d = os.path.join(tmp, "backend", "app", "models")
        os.makedirs(d)
        f = os.path.join(d, "order.rb")
        open(f, "w", encoding="utf-8").write(
            "class Order < ApplicationRecord\n"
            + "".join(f"  # line {i}\n" for i in range(cqc.MODEL_LIMIT + 20)) + "end\n")
        out = cqc.check({"tool_name": "Write", "tool_input": {"file_path": f}})
        if any(str(cqc.MODEL_LIMIT) in w for w in out):
            PASS += 1
            print(f"  PASS: a model over {cqc.MODEL_LIMIT} lines warns (the gate is live)")
        else:
            FAIL += 1
            print(f"  FAIL: a model over {cqc.MODEL_LIMIT} lines produced no warning: {out}")


def test_mcp_install_gate():
    """An MCP server is an instruction source, not a library: its tool descriptions are prompts
    the model obeys, and the docs say plainly "Verify you trust each server before connecting
    it. Servers that fetch external content can expose you to prompt injection risk." So the
    human picks it (layer 6). The `mcp-advisor` skill cannot guarantee that — guidance only
    works if read — which is why this is a gate (Ch. 7's placement test).

    `ask`, never `deny`: MCP servers are legitimate and useful, and a deny here just gets the
    plugin disabled."""
    print("\n[mcp-install-gate.py]")
    assert_warns("asks on `claude mcp add` (stdio)", "mcp-install-gate.py", "Bash",
                 {"command": "claude mcp add airtable -- npx -y airtable-mcp-server"})
    assert_warns("asks on `claude mcp add --transport http`", "mcp-install-gate.py", "Bash",
                 {"command": "claude mcp add --transport http notion https://mcp.notion.com/mcp"})
    assert_warns("asks on `claude mcp add-json`", "mcp-install-gate.py", "Bash",
                 {"command": "claude mcp add-json weather '{\"type\":\"stdio\"}'"})
    assert_warns("asks on add-from-claude-desktop (a bulk import of servers)",
                 "mcp-install-gate.py", "Bash",
                 {"command": "claude mcp add-from-claude-desktop"})

    # The team-wide path: project scope ships to everyone, so the reason must say so.
    assert_output_contains("names the team-wide blast radius for --scope project",
                           "mcp-install-gate.py", "Bash",
                           {"command": "claude mcp add --transport http --scope project acme https://mcp.acme.com/mcp"},
                           "EVERY teammate")
    # A deny reason must name a remedy (Ch. 25) — here, where to find vetted servers.
    assert_output_contains("names a remedy: the reviewed directory", "mcp-install-gate.py", "Bash",
                           {"command": "claude mcp add foo -- npx foo"},
                           "claude.ai/directory")

    # Editing .mcp.json adds servers for the whole team with no CLI involved. Gating only the
    # CLI would be a gate with a door next to it.
    assert_warns("asks when .mcp.json is written directly", "mcp-install-gate.py", "Write",
                 {"file_path": "/repo/.mcp.json",
                  "content": '{"mcpServers": {"acme": {"type": "http", "url": "https://mcp.acme.com"}}}'})

    # Must NOT fire on things that reduce or merely inspect capability, or the gate becomes
    # noise people click through.
    assert_allowed("silent on `claude mcp list`", "mcp-install-gate.py", "Bash",
                   {"command": "claude mcp list"})
    assert_allowed("silent on `claude mcp remove` (reduces capability)", "mcp-install-gate.py",
                   "Bash", {"command": "claude mcp remove airtable"})
    assert_allowed("silent on `claude mcp get`", "mcp-install-gate.py", "Bash",
                   {"command": "claude mcp get airtable"})
    assert_allowed("silent on unrelated bash", "mcp-install-gate.py", "Bash",
                   {"command": "npm run build"})
    assert_allowed("silent on unrelated file writes", "mcp-install-gate.py", "Write",
                   {"file_path": "/repo/package.json", "content": '{"name":"x"}'})


def test_hook_messages_point_somewhere_real():
    """Ch. 13 — "It explains its denials … the deny reasons are your plugin's user interface,
    and they're the only part most users will ever read." Ch. 25 adds that a reason must name a
    remedy. A pointer to a file that does not exist fails both: the user greps for it, finds
    nothing, and learns that the guidance is unreachable.

    This is not hypothetical. Converting `.claude/rules/*.md` into `std-*` skills left **37
    messages across 10 hooks** pointing at `accessibility.md`, `security.md`, `database.md` and
    friends — none of which existed any more. Every one of those hooks fired correctly and sent
    the reader nowhere."""
    print("\n[hook messages must point at something that exists]")
    global PASS, FAIL
    import glob
    import re

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))
    skills = {os.path.basename(os.path.dirname(p))
              for p in glob.glob(os.path.join(repo, "skills", "*", "SKILL.md"))}

    dangling, skill_refs = [], 0
    for path in sorted(glob.glob(os.path.join(HOOKS_DIR, "*.py"))):
        text = open(path, encoding="utf-8").read()
        name = os.path.basename(path)

        # 1. Any `something.md` named in a hook must exist on disk somewhere in the repo.
        for m in re.finditer(r"\b([a-z][a-z0-9_-]*\.md)\b", text):
            target = m.group(1)
            if not glob.glob(os.path.join(repo, "**", target), recursive=True):
                dangling.append(f"{name}: points at '{target}', which does not exist")

        # 2. Any `std-x` skill it names must be a real skill directory.
        for m in re.finditer(r"`(std-[a-z0-9-]+)`", text):
            skill_refs += 1
            if m.group(1) not in skills:
                dangling.append(f"{name}: names skill '{m.group(1)}', which does not exist")

    if dangling:
        FAIL += 1
        for d in dangling[:10]:
            print(f"  FAIL: {d}")
        print(f"  ({len(dangling)} dangling pointer(s) — a reason nobody can follow is not a reason)")
    else:
        PASS += 1
        print(f"  PASS: every file/skill named by a hook exists ({skill_refs} skill pointers checked)")

    # Prove the check FIRES rather than merely agreeing with today's tree.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        fake = os.path.join(tmp, "fake-hook.py")
        open(fake, "w", encoding="utf-8").write(
            '"""Checks things per totally-made-up-rules.md."""\n')
        text = open(fake, encoding="utf-8").read()
        found = [m.group(1) for m in re.finditer(r"\b([a-z][a-z0-9_-]*\.md)\b", text)
                 if not glob.glob(os.path.join(repo, "**", m.group(1)), recursive=True)]
        if found:
            PASS += 1
            print("  PASS: the check catches an invented .md pointer")
        else:
            FAIL += 1
            print("  FAIL: the check would not notice a dangling pointer")

    # A hook that warns must also say WHERE the rule lives. The earlier fix guaranteed that a
    # named skill exists; this guarantees one is named at all. 8 hooks warned into the void
    # while 11 pointed somewhere — a developer hit by the design-token checker had nowhere to
    # learn the rule.
    #
    # `[a-z0-9-]` and not `[a-z-]`: `std-i18n` has digits in it. The narrower class silently
    # reported i18n-checker as pointing nowhere when it pointed correctly — a false positive
    # that would have "fixed" working code.
    EXEMPT = {
        # Names an install command ("gem install rubocop"), which is the actual remedy.
        # No skill teaches "have rubocop on your PATH".
        "auto-format.py": "names an install command, not a rule",
        "audit-logger.py": "records, never warns",
        "capture-event.py": "developer tool, not a gate",
        "session-start-check.py": "reports environment state; the sentinel names the rules inline",
    }
    silent = []
    for path in sorted(glob.glob(os.path.join(HOOKS_DIR, "*.py"))):
        name = os.path.basename(path)
        if name.startswith("_") or name in EXEMPT:
            continue
        text = open(path, encoding="utf-8").read()
        if not re.search(r"warnings\.append|hooklib\.(ask|deny)|notice_once", text):
            continue
        if not re.search(r"`[a-z0-9-]+` skill", text):
            silent.append(name)
    if silent:
        FAIL += 1
        print(f"  FAIL: warns but names no skill, so the reader has nowhere to go: {silent}")
    else:
        PASS += 1
        print("  PASS: every warning-emitting hook names the skill that carries the rule")


def test_release_hygiene_checker():
    """Ch. 13 — "pin, don't float", with the mechanical edge the plugin docs spell out: a
    `version` that does not move means "pushing new commits ... does nothing for existing
    users". That is a SILENT delivery failure — everything merges, CI is green, and no
    installed user receives any of it. The gate is inert until the first tag exists, so it
    would otherwise be a gate that has only ever printed a note. Prove it fires."""
    print("\n[release hygiene — a stale version delivers nothing]")
    global PASS, FAIL
    import shutil
    import tempfile

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))
    script = os.path.join(repo, ".github", "scripts", "check_release_hygiene.py")
    if not os.path.isfile(script):
        FAIL += 1
        print("  FAIL: .github/scripts/check_release_hygiene.py is missing")
        return

    def run(cwd, env_extra=None):
        env = dict(os.environ)
        env.pop("GITHUB_REF", None)
        env.update(env_extra or {})
        proc = subprocess.run([sys.executable, script], cwd=cwd, capture_output=True,
                              text=True, timeout=60, env=env)
        return proc.returncode, proc.stdout + proc.stderr

    code, out = run(repo)
    if code == 0:
        PASS += 1
        print("  PASS: the real tree passes")
    else:
        FAIL += 1
        print(f"  FAIL: the real tree fails its own release gate:\n{out}")
    if "INERT" in out:
        PASS += 1
        print("  PASS: with no tags the gate announces it is inert (not silently green)")
    else:
        FAIL += 1
        print("  FAIL: an inert delivery gate stayed quiet — indistinguishable from a passing one")

    def git(cwd, *args):
        subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=30)

    def scaffold(tmp, version="1.0.0", entry_version=None):
        work = os.path.join(tmp, "repo")
        os.makedirs(os.path.join(work, ".claude-plugin"))
        os.makedirs(os.path.join(work, "skills", "demo"))
        shutil.copytree(os.path.join(repo, ".github", "scripts"),
                        os.path.join(work, ".github", "scripts"))
        entry = {"name": "sdh", "source": "./"}
        if entry_version:
            entry["version"] = entry_version
        json.dump({"name": "sdh", "version": version},
                  open(os.path.join(work, ".claude-plugin", "plugin.json"), "w"))
        json.dump({"name": "m", "plugins": [entry]},
                  open(os.path.join(work, ".claude-plugin", "marketplace.json"), "w"))
        open(os.path.join(work, "skills", "demo", "SKILL.md"), "w").write("# demo\n")
        open(os.path.join(work, "CHANGELOG.md"), "w").write(
            "# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2026-01-01\n\n- initial\n")
        git(work, "init", "-q")
        git(work, "config", "user.email", "t@t.t")
        git(work, "config", "user.name", "t")
        git(work, "add", "-A")
        git(work, "commit", "-qm", "init")
        git(work, "tag", "v1.0.0")
        return work

    # The real regression: plugin content changes, version does not.
    with tempfile.TemporaryDirectory() as tmp:
        work = scaffold(tmp)
        open(os.path.join(work, "skills", "demo", "SKILL.md"), "a").write("a new rule\n")
        git(work, "add", "-A")
        git(work, "commit", "-qm", "change a skill")
        code, out = run(work)
        if code != 0 and "does nothing for existing users" in out.lower():
            PASS += 1
            print("  PASS: catches changed plugin content under an unchanged version")
        else:
            FAIL += 1
            print(f"  FAIL: MISSED the silent-delivery bug — this is the whole point: {out[:200]}")

        # Bumping the version is what makes the change deliverable.
        manifest = os.path.join(work, ".claude-plugin", "plugin.json")
        json.dump({"name": "sdh", "version": "1.1.0"}, open(manifest, "w"))
        git(work, "add", "-A")
        git(work, "commit", "-qm", "bump")
        code, out = run(work)
        if code == 0:
            PASS += 1
            print("  PASS: a bumped version passes (the gate is satisfiable)")
        else:
            FAIL += 1
            print(f"  FAIL: gate still fails after a correct bump — it would be routed around: {out[:200]}")

    # A tag push must be internally consistent.
    with tempfile.TemporaryDirectory() as tmp:
        work = scaffold(tmp, version="1.1.0")
        code, out = run(work, {"GITHUB_REF": "refs/tags/v9.9.9"})
        if code != 0 and "does not match" in out:
            PASS += 1
            print("  PASS: catches a tag that disagrees with plugin.json")
        else:
            FAIL += 1
            print("  FAIL: a tag naming a version the manifest never declared was allowed")

        # CHANGELOG has no [1.1.0] section, and [Unreleased] is empty -> the missing-section
        # failure must fire on its own.
        code, out = run(work, {"GITHUB_REF": "refs/tags/v1.1.0"})
        if code != 0 and "no `## [1.1.0]` section" in out:
            PASS += 1
            print("  PASS: catches releasing a version the CHANGELOG never documents")
        else:
            FAIL += 1
            print(f"  FAIL: released an undocumented version: {out[:200]}")

    # Draining [Unreleased] is part of cutting a release.
    with tempfile.TemporaryDirectory() as tmp:
        work = scaffold(tmp, version="1.1.0")
        open(os.path.join(work, "CHANGELOG.md"), "w").write(
            "# Changelog\n\n## [Unreleased]\n\n- a change nobody moved\n\n"
            "## [1.1.0] - 2026-02-02\n\n- released\n")
        code, out = run(work, {"GITHUB_REF": "refs/tags/v1.1.0"})
        if code != 0 and "Unreleased" in out:
            PASS += 1
            print("  PASS: catches a release that left entries stranded under [Unreleased]")
        else:
            FAIL += 1
            print("  FAIL: released with undrained [Unreleased] — the version misdescribes itself")

    # Two versions, one silently ignored.
    with tempfile.TemporaryDirectory() as tmp:
        work = scaffold(tmp, version="1.0.0", entry_version="2.0.0")
        code, out = run(work)
        if code != 0 and "WITHOUT WARNING" in out:
            PASS += 1
            print("  PASS: catches a marketplace entry version that plugin.json silently masks")
        else:
            FAIL += 1
            print(f"  FAIL: allowed two conflicting versions: {out[:200]}")


def test_rule_taxonomy_checker():
    """Ch. 9 — a gate that has only ever passed is untested. This one exists because
    react-native-best-practices had silently collapsed its 14 canonical sections into 8
    invented ones, dropping "Core Rendering" (CRITICAL — "violations cause runtime crashes")
    and promoting List Performance into the vacant slot. The body is what the model reads, so
    a wrong impact there mis-prioritises real work. Prove the checker CATCHES that regression
    rather than merely agreeing with today's tree."""
    print("\n[rule taxonomy — the body must match rules/_sections.md]")
    global PASS, FAIL
    import shutil
    import tempfile

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))
    script = os.path.join(repo, ".github", "scripts", "check_rule_taxonomy.py")
    if not os.path.isfile(script):
        FAIL += 1
        print("  FAIL: .github/scripts/check_rule_taxonomy.py is missing — the taxonomy gate is gone")
        return

    def run(cwd):
        proc = subprocess.run([sys.executable, script], cwd=cwd,
                              capture_output=True, text=True, timeout=60)
        return proc.returncode, proc.stdout + proc.stderr

    # 1. The real tree must pass, or the gate is crying wolf.
    code, out = run(repo)
    if code == 0:
        PASS += 1
        print("  PASS: the real tree passes the taxonomy gate")
    else:
        FAIL += 1
        print(f"  FAIL: the real tree does not satisfy its own taxonomy gate:\n{out}")

    with tempfile.TemporaryDirectory() as tmp:
        work = os.path.join(tmp, "repo")
        os.makedirs(os.path.join(work, ".github"))
        shutil.copytree(os.path.join(repo, "skills"), os.path.join(work, "skills"))
        shutil.copytree(os.path.join(repo, ".github", "scripts"),
                        os.path.join(work, ".github", "scripts"))
        body_path = os.path.join(work, "skills", "react-native-best-practices", "SKILL.md")
        original = open(body_path, encoding="utf-8").read()

        # 2. Reconstruct the actual regression and prove the gate fires on it.
        cases = [
            ("a CRITICAL section downgraded",
             lambda t: t.replace("### 1. Core Rendering (CRITICAL)",
                                 "### 1. Core Rendering (MEDIUM)")),
            ("an impact relabelled upward",
             lambda t: t.replace("### 2. List Performance (HIGH)",
                                 "### 2. List Performance (CRITICAL)")),
            ("a section dropped from the body",
             lambda t: t.replace("### 14. Fonts (LOW)", "### 14. Fonts")),
        ]
        for label, mutate in cases:
            open(body_path, "w", encoding="utf-8", newline="\n").write(mutate(original))
            code, out = run(work)
            if code != 0:
                PASS += 1
                print(f"  PASS: gate catches {label}")
            else:
                FAIL += 1
                print(f"  FAIL: gate MISSED {label} — it would merge")

        # 3. A rule file on disk that no section prefix claims must be caught: the body
        #    cannot group it, so the model never learns it exists.
        open(body_path, "w", encoding="utf-8", newline="\n").write(original)
        orphan = os.path.join(work, "skills", "react-native-best-practices", "rules",
                              "zzz-unclaimed-rule.md")
        open(orphan, "w", encoding="utf-8").write("# orphan\n")
        code, out = run(work)
        if code != 0 and "claimed by no section" in out:
            PASS += 1
            print("  PASS: gate catches a rule file no section claims")
        else:
            FAIL += 1
            print("  FAIL: gate MISSED an unclaimed rule file")
        os.remove(orphan)

        # 4. Numbering is house style, not an invariant. Both conventions are in use; a gate
        #    that fires on a legitimate variation trains people to ignore it.
        open(body_path, "w", encoding="utf-8", newline="\n").write(
            original.replace("### 1. Core Rendering (CRITICAL)", "### Core Rendering (CRITICAL)"))
        code, out = run(work)
        if code == 0:
            PASS += 1
            print("  PASS: unnumbered headings accepted (gates the invariant, not house style)")
        else:
            FAIL += 1
            print("  FAIL: gate rejects a legitimate heading style — it will be ignored as noise")


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
    test_ci_workflow_is_loadable()
    test_deny_reasons_name_a_remedy()
    test_terraform_command_gate()
    test_fail_open_is_not_silent()
    test_permission_sentinel()
    test_hooklib_primitives()
    test_wrapper_agnostic()
    test_vague_request_detector()
    test_rule_taxonomy_checker()
    test_commit_types_match_the_skill()
    test_autoformat_never_changes_semantics()
    test_limits_match_the_skill_that_documents_them()
    test_mcp_install_gate()
    test_hook_messages_point_somewhere_real()
    test_release_hygiene_checker()
    test_configurable_at_the_edges()
    test_missing_tool_says_so_once()

    print("\n" + "=" * 60)
    print(f"Results: {PASS} passed, {FAIL} failed")
    print("=" * 60)

    sys.exit(1 if FAIL > 0 else 0)


if __name__ == "__main__":
    main()
