---
name: mobile-beta-release
description: Build and ship React Native betas to testers — TestFlight (internal vs external groups, Beta App Review, 90-day build expiry) and Google Play testing tracks (internal, closed, open, staged rollout), with fastlane lanes, build-number strategy, and release notes. Use when shipping a build to testers or QA, setting up TestFlight or a Play internal/closed track, automating beta distribution in CI, deciding which track a build belongs on, or when someone asks "how do I get this to testers", "push to TestFlight", "Play internal testing", "staged rollout", or why a beta build is stuck in processing or review.
model: sonnet
---

# Mobile Beta Release — getting a build to testers

Two stores, two completely different shapes. The mistake that costs the most time is assuming
they behave alike and planning the release around the faster one.

| | iOS (TestFlight) | Android (Play tracks) |
|---|---|---|
| Fast lane | **Internal testers** — up to **100** team members holding Account Holder, Admin, App Manager, Developer or Marketing roles | **Internal testing** track — up to 100 testers, fastest availability |
| Wide lane | **External testers** — up to **10,000** | Closed → Open testing |
| Review gate | **External requires Beta App Review**: *"have your first build already approved by App Review for TestFlight. Your builds are automatically sent for review once they're added to a group."* | No App Review for internal testing |
| Build lifetime | **90 days**, then the build expires for testers | No expiry |
| Distribution | Apple hosts; testers use the TestFlight app | Play hosts; testers opt in via a link |

**The planning consequence:** an external TestFlight build can sit in Beta App Review while the
Android build is already on testers' phones. If your QA cycle assumes both land together, it
doesn't. Use **internal** testers for the tight loop and reserve external for the wider round.

### Which of these facts expire

**The shapes above are stable; the numbers are store policy and they move.** Apple has raised the
external-tester ceiling before (2,000 → 10,000) and the internal one (25 → 100). Nothing in this
skill records when it was last checked, because nothing here ever was — the Apple wording quoted in
`references/testflight.md` is verbatim, which makes it *sourced* but not *dated*, and a quote is
exactly as confident the day it goes stale as the day it was right.

| Stable — the reason to read this skill | Expires — check before you rely on it |
|---|---|
| Internal is fast, external is reviewed | The tester ceilings (**100** / **10,000**) |
| A TestFlight build has a finite life; a Play build does not | The **90-day** window |
| The first build of an external group goes to Beta App Review | Review turnaround, and what triggers a re-review |
| Build numbers must increase, forever, per platform | Track names and their availability |

Check the ceiling and the window in **App Store Connect** and the **Play Console** — the consoles
show your app's real limits, which beat any doc. **Do not restate a number from memory** if it is
not in the table above: asked about a platform or a tier not covered here, say so rather than
producing a plausible figure, because a recalled limit is indistinguishable from a checked one once
it is in a release plan.

**The planning advice survives either way**, which is the point of separating them: *use internal
for the tight loop, reserve external for the wider round* stays true whether the ceiling is 10,000
or 25,000.

## Decision: which track does this build belong on?

| Who needs it | iOS | Android |
|---|---|---|
| The 5 people on the team, right now | Internal testers | Internal testing |
| QA / the wider company | Internal (if ≤100 and they hold roles) | Closed testing (email list or Google Group) |
| Real customers in a beta programme | External group (Beta App Review) | Closed or Open testing |
| Everyone, gradually | — (use phased release on the App Store) | Production + **staged rollout** |

**Do not put non-employees in TestFlight internal.** Internal testers must be App Store Connect
users on your team — which means giving them an account with real permissions on your app.
"Just add the client as an Admin" is how a customer ends up able to change your app's pricing.

## Build numbers: the rule that prevents the most wasted uploads

**Every upload needs a build number nobody has used before, for that version.** Both stores
reject a duplicate — and on iOS you discover it *after* the archive, upload, and processing
wait.

- **Never** hand-increment in the repo. Two branches will collide, and the merge conflict is in
  a file nobody reads.
- Derive it. `github.run_number` is monotonic and free. `app_store_build_number(live: false) + 1`
  asks Apple what it already has.
- Keep the **version** (marketing) in the repo and the **build number** from CI. They answer
  different questions: version is what you tell users, build number is what distinguishes two
  uploads of the same version.

## Release notes are the point, not paperwork

A tester who does not know what changed reports nothing useful. "Bug fixes and improvements"
wastes the whole build.

- Say **what to test**, not what you did: *"Checkout: try paying with a saved card — the crash
  on Apply Promo should be gone."*
- Both stores accept notes per build; automate them from the changelog or commits.
- Ship the same notes to both platforms, or your two tester groups test different things and
  you cannot compare their reports.

## What must never differ from production

A beta whose config differs from production tests the beta, not the app.

- Point betas at **staging** deliberately, and label it in-app (a visible build banner) — a
  tester filing bugs against production data is worse than no tester.
- **Same signing, same minification.** A beta built without ProGuard/R8 or with a debug
  entitlement is a different binary; the crash you are hunting may only exist in release.
- Ship **source maps / dSYMs** with the beta or the crash reports are unreadable stack noise.

## Deep guides (read on demand, do not preload)

- TestFlight end to end — internal vs external groups, Beta App Review, the 90-day expiry,
  processing states, `upload_to_testflight` options, and why builds sit in "Processing"
  → `references/testflight.md`
- Play testing tracks — internal/closed/open, opt-in links, promoting a build between tracks,
  staged rollout and halting one, `.aab` uploads with `supply`
  → `references/play-tracks.md`
- The fastlane lanes themselves — one beta lane per platform, build-number derivation, changelog
  → notes, dSYM/mapping upload, and the CI wiring
  → `references/fastlane-lanes.md`

Signing identities (certificates, profiles, keystores, API keys) are a separate concern — see
the `mobile-signing` skill. Do not debug a signing failure from here.
