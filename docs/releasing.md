# Releasing — the version is the delivery handle

> **The one thing to know:** if `plugin.json`'s `version` does not change, **nothing you ship
> reaches anyone who already installed the plugin.** Not a lint nit — a silent delivery
> failure. Everything merges, CI goes green, and installed users keep the cached copy.

From the Claude Code plugin docs:

> *"Setting `version` pins the plugin. If `plugin.json` declares `"version": "1.0.0"`, pushing
> new commits without changing that string does nothing for existing users, because Claude Code
> sees the same version and keeps the cached copy. **Bump the field on every release**, or omit
> it to use the commit SHA."*

And Ch. 13's supply-chain discipline:

> *"**Pin, don't float.** Installing from a marketplace's `main` or an unpinned git URL means
> every teammate silently tracks a moving target: a standards change — or a hook bug — reaches
> everyone the moment it's pushed, with no review gate between commit and production behavior.
> Tag releases (`v2.1.0`) and have teams pin the tag. An unpinned governance plugin is the exact
> supply-chain posture you would flag in someone else's audit; hold yours to the same standard."*

---

## How Claude Code resolves a version

First one set wins:

1. `version` in the plugin's `plugin.json`  ← **what this repo uses**
2. `version` in the plugin's marketplace entry
3. The git commit SHA of the plugin's source

**Never set both 1 and 2.** Claude Code uses the `plugin.json` value *without warning*, so a
stale manifest silently masks the marketplace entry. `check_release_hygiene.py` fails the build
if both appear.

### The two viable postures

| Posture | Setup | Use when |
|---|---|---|
| **Explicit versions** (this repo) | Keep `version` in `plugin.json`, **bump every release**, tag `vX.Y.Z` | You want consumers to pin a reviewed release — correct for a governance plugin |
| **Commit-SHA delivery** | **Omit** `version` from `plugin.json` entirely; every commit is a new version | Internal, actively-developed plugins where floating is acceptable |

Choose one. The failure mode is the accidental third state — *declaring* a version and never
bumping it — which looks like the first and behaves like nothing at all.

## Cutting a release

1. **Decide the number.** SemVer, judged from the consumer's perspective — see below.
2. **Bump `.claude-plugin/plugin.json`** → `"version": "X.Y.Z"`.
3. **Drain the CHANGELOG**: move everything under `## [Unreleased]` into `## [X.Y.Z] - YYYY-MM-DD`.
4. **Open a PR, merge it.**
5. **Tag and push:**
   ```bash
   git tag vX.Y.Z && git push origin vX.Y.Z
   ```
   The tag push runs CI, which verifies the tag, the manifest version, and the CHANGELOG
   section all agree, and that `[Unreleased]` was actually drained.
6. **Announce what consumers must do by hand** — above all, any **permission-floor change**
   (see below).

## What counts as which bump

This is a **governance** plugin: the thing it ships is a change to what your teammates' agents
are allowed to do. Judge from the consumer's process, not from our code.

| Change | Bump | Why |
|---|---|---|
| A new **deny** rule, or a gate that now denies/asks where it did not | **MAJOR** | Work that succeeded yesterday now stops. That is breaking, whatever the diff size. |
| Removing a deny, loosening a gate | MINOR | Nothing that worked stops working — but it is still an interface change. |
| New skill / agent / reference; new advisory warning | MINOR | Additive. |
| Wording, docs, a fixed false positive | PATCH | No behavioural change for a correct user. |

> A new deny is a MAJOR bump even though it is "just a config line". A team whose deploy script
> starts getting blocked does not care that the diff was small.

**Every entry under "Permission floor" in the CHANGELOG is ACTION REQUIRED**: a plugin cannot
ship `permissions`, so consumers must copy those rules into their own
`.claude/settings.json` by hand. The SessionStart sentinel will name the missing rules on every
session until they do — but the release notes are what tells them *why*.

## How consumers pin

Verified against the plugin-marketplace docs. Git sources (`github`, `url`, `git-subdir`)
accept `ref` and `sha`; **when both are set, `sha` is the effective pin.**

```json
{
  "name": "sdh-pinned",
  "plugins": [
    {
      "name": "sdh",
      "source": {
        "source": "github",
        "repo": "Kaakati/sdh-claude-skills",
        "ref": "v1.1.0"
      }
    }
  ]
}
```

A `sha` pin survives the tag being deleted or moved upstream, as long as the commit stays
reachable — the stronger choice if you are pinning because you do not trust the upstream to
hold a tag still:

```json
{ "source": "github", "repo": "Kaakati/sdh-claude-skills", "ref": "v1.1.0", "sha": "<commit>" }
```

> `/plugin marketplace add Kaakati/sdh-claude-skills` **floats on `main`**. That is fine for
> evaluating the plugin and wrong for running a team on it.

### Stable and latest channels

Two marketplaces pointing at different refs of this repo, assigned to different groups via
managed settings (`enabledPlugins`). **Each channel must resolve to a different version
string** — if two refs declare the same `version`, Claude Code treats them as identical and
skips the update, which silently collapses the channels into one.

## Repo-side controls (layer 7)

Layer 7 is *"everything outside the session, assuming all six inner layers failed"* — so it
must not be enforceable by the person it is checking. These are GitHub settings, not code; CI
cannot verify them from inside a workflow run, which is precisely why they are written down.

Required on `main`:

- **Require a pull request before merging** — no direct pushes. The `pre-commit-check` hook
  *asks* on a direct push; that is layer 6 (a tired human can click through it). Branch
  protection is the layer that does not get tired.
- **Require status checks to pass**: `hook-fixtures`, `plugin-manifest`, `skills-lint`,
  `sentinel-guard`, `release-hygiene`.
- **Require at least one approving review**, and **not from the author**. Ch. 20: *"human
  fatigue correlates layers 6 and 7 — if the same tired person clicks `ask` and approves the
  PR, you have one layer wearing two hats."*
- **Require branches to be up to date before merging** — otherwise two green PRs merge into a
  red trunk.
- **Restrict who may push tags** (`v*`) — a tag is what consumers pin; anyone who can move it
  can change what every pinned consumer runs.
- **Do not allow force pushes or deletions** on `main`.

## Current state (2026-07-15)

**`v2.0.0` is prepared but not yet tagged.** `plugin.json` declares `2.0.0`, the CHANGELOG has a
drained `## [2.0.0]` section, and a simulated tag push passes the release gate.

Why MAJOR: the release makes `terraform destroy`, `state rm|mv|push`, `force-unlock` and
`apply -auto-approve` **denied**, and `terraform apply` **ask**. Work that succeeded before now
stops — breaking from the consumer's process, whatever the diff size.

Background: `version` sat at `1.0.0` from the plugin-conversion commit while 16+ commits changed
plugin content (the deny floor, a fail-closed gate, the sentinel, skills). Under the resolution
rules above, **none of it could reach an installed user.** `2.0.0` is the first version that can
actually be delivered.

**Remaining, in order** — the tag must point at reviewed code on `main`, not at a feature branch,
because the tag is what consumers pin:

1. Merge `feat/governance-layers` → `main`.
2. `git tag v2.0.0 && git push origin v2.0.0` on the merge commit.
3. CI runs `release-hygiene` on the tag push and verifies the tag, the manifest, and the
   CHANGELOG agree.

Until step 2, the delivery gate stays **inert** and says so on every run rather than passing
quietly.
