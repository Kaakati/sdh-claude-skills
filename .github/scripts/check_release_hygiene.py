#!/usr/bin/env python3
"""Verify the plugin's version is a working delivery handle, not decoration.

Ch. 13's supply-chain discipline — *"Pin, don't float. Tag releases (`v2.1.0`) and have teams
pin the tag"* — has a mechanical edge that is easy to miss, and the Claude Code plugin docs
state it plainly:

    "Setting `version` pins the plugin. If `plugin.json` declares `"version": "1.0.0"`, pushing
     new commits without changing that string does nothing for existing users, because Claude
     Code sees the same version and keeps the cached copy. Bump the field on every release, or
     omit it to use the commit SHA."

So a stale `version` is not a cosmetic problem. It is a **silent delivery failure**: every fix
merges, CI goes green, the repo looks healthy, and no installed user receives any of it. That
is the same shape as a dead gate masquerading as a green one — which is why it gets a gate.

Run locally exactly as CI does:

    python3 .github/scripts/check_release_hygiene.py

What is enforced:
  1. `plugin.json.version` is valid semver.
  2. A marketplace plugin entry does not ALSO set `version` — the docs warn that plugin.json
     silently wins, so a second value can only ever mislead.
  3. Plugin content changed since the newest release tag => `version` must have moved. This is
     the delivery gate; it is inert until the first tag exists, and says so rather than
     passing quietly.
  4. On a tag push: the tag, `plugin.json.version`, and the CHANGELOG's newest released
     section all agree, and `[Unreleased]` has been drained into it.
"""

import json
import os
import re
import subprocess
import sys

SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
# Directories whose contents ARE the plugin. A change here is a change every consumer runs.
PLUGIN_CONTENT = ("skills/", "agents/", "hooks/", "commands/", ".claude-plugin/")


def git(*args):
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True, timeout=30)
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def newest_release_tag():
    """Newest v-prefixed tag by semver order, or "" when the repo has never released."""
    tags = [t for t in git("tag", "-l", "v*").splitlines() if SEMVER.match(t.lstrip("v"))]
    if not tags:
        return ""
    return sorted(tags, key=lambda t: [int(p) for p in t.lstrip("v").split("-")[0].split(".")])[-1]


def changelog_sections(text):
    """Released version headings, newest first: ## [1.2.0] - 2026-01-01"""
    return re.findall(r"^##\s*\[(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)\]", text, re.M)


def unreleased_body(text):
    m = re.search(r"^##\s*\[Unreleased\]\s*$(.*?)(?=^##\s*\[|\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def main():
    fail, notes = [], []

    manifest_path = ".claude-plugin/plugin.json"
    market_path = ".claude-plugin/marketplace.json"
    if not os.path.isfile(manifest_path):
        print("FAIL: .claude-plugin/plugin.json not found — run from the repo root.")
        return 1

    manifest = json.load(open(manifest_path, encoding="utf-8"))
    version = manifest.get("version")

    # 1. semver
    if version is None:
        notes.append(
            "plugin.json omits `version` — every commit is then treated as a new version "
            "(the docs' simplest setup). Nothing to check; delivery is by commit SHA."
        )
    elif not SEMVER.match(str(version)):
        fail.append(
            f"{manifest_path}: version {version!r} is not semver (X.Y.Z). Consumers pin this "
            f"string; a value Claude Code cannot order is not a pin."
        )

    # 2. two versions, one of which is silently ignored
    if os.path.isfile(market_path):
        market = json.load(open(market_path, encoding="utf-8"))
        for entry in market.get("plugins", []):
            if entry.get("version") and version is not None:
                fail.append(
                    f"{market_path}: plugin entry '{entry.get('name')}' sets version "
                    f"{entry['version']!r} while {manifest_path} sets {version!r}. Claude Code "
                    f"always uses the plugin.json value WITHOUT WARNING, so this second value "
                    f"can only mislead. Remove it from the marketplace entry."
                )

    # 3. the delivery gate — changes that reach nobody
    tag = newest_release_tag()
    if not tag:
        notes.append(
            "No release tag exists yet, so the delivery gate is INERT: nothing can verify that "
            "shipped changes actually reach installed users. The book: \"Tag releases (v2.1.0) "
            "and have teams pin the tag.\" See docs/releasing.md."
        )
    elif version is not None:
        changed = [
            f for f in git("diff", "--name-only", f"{tag}..HEAD").splitlines()
            if f.startswith(PLUGIN_CONTENT)
        ]
        if changed and str(version) == tag.lstrip("v"):
            preview = ", ".join(sorted({c.split("/")[0] for c in changed}))
            fail.append(
                f"{manifest_path}: {len(changed)} plugin file(s) changed since {tag} ({preview}) "
                f"but version is still {version!r}. Per the plugin docs, pushing commits without "
                f"changing that string DOES NOTHING for existing users — Claude Code sees the "
                f"same version and keeps the cached copy. Bump the version (see "
                f"docs/releasing.md), or omit it to deliver by commit SHA."
            )

    # 4. a tag push must be internally consistent
    ref = os.environ.get("GITHUB_REF", "")
    if ref.startswith("refs/tags/"):
        pushed = ref[len("refs/tags/"):]
        want = pushed.lstrip("v")
        if version is not None and want != str(version):
            fail.append(
                f"tag {pushed} does not match {manifest_path} version {version!r}. The tag is "
                f"what consumers pin; if it names a version the manifest does not declare, they "
                f"pin one thing and run another."
            )
        if os.path.isfile("CHANGELOG.md"):
            text = open("CHANGELOG.md", encoding="utf-8").read()
            if want not in changelog_sections(text):
                fail.append(
                    f"CHANGELOG.md has no `## [{want}]` section, but tag {pushed} is being "
                    f"released. The changelog is this plugin's interface — a release consumers "
                    f"cannot read is one they cannot copy the permission changes from."
                )
            if re.search(r"^\s*[-*]\s+\S", unreleased_body(text), re.M):
                fail.append(
                    f"CHANGELOG.md still has entries under `## [Unreleased]` while releasing "
                    f"{pushed}. Move them into `## [{want}]` so the released version documents "
                    f"what it actually contains."
                )

    for n in notes:
        print(f"NOTE: {n}")
    if fail:
        print()
        print("\n".join("FAIL: " + f for f in fail))
        return 1
    print(f"release hygiene OK (version={version}, newest tag={tag or 'none'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
