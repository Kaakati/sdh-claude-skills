# Play Testing Tracks — internal, closed, open, and the rollout you can halt

Load-bearing rules restated (hold even if you read nothing else):

1. **Internal testing is the fast lane** — no App Review gate, availability in minutes.
2. **Promote the *same* artifact between tracks.** Rebuilding to promote means shipping a binary
   nobody tested.
3. **Staged rollout is the only production deploy you can stop.** Use it, and know how to halt.

---

## The four tracks

| Track | Audience | Speed | Use for |
|---|---|---|---|
| **Internal testing** | Up to 100 testers by email | Minutes — no review gate | The daily QA loop |
| **Closed testing** | Email lists / Google Groups | Review, usually fast | QA, clients, a private beta |
| **Open testing** | Anyone with the link | Review | Public beta, scale testing |
| **Production** | Everyone | Full review | The real thing — with staged rollout |

Unlike TestFlight, **internal testing has no App Review gate**, which is why the Android beta is
usually on phones while the iOS external build is still queued. Plan around that asymmetry
rather than being surprised by it every cycle.

## Decision: which track?

| Situation | Track |
|---|---|
| The team, right now | Internal testing |
| QA + client, a named list | Closed testing |
| "Anyone who wants to try it" | Open testing |
| Shipping to users, cautiously | Production with staged rollout |

Testers **opt in** via a link (internal and closed included) — they are not force-installed.
Sending the link is part of shipping; a track with no opted-in testers looks identical to a
successful release.

## Bad — rebuilding to promote

```yaml
# ❌ "promote to production" that rebuilds from source
- run: ./gradlew bundleRelease            # a NEW artifact
- run: fastlane supply --track production --aab app-release.aab
```

The bundle now in production was **never tested**. It may differ by a dependency resolution, a
timestamp, a build-tools patch — and the one time it matters, you will not know that is why. The
tested artifact and the shipped artifact must be the same bytes.

## Good — build once, promote the artifact

```ruby
# fastlane/Fastfile  ✅
lane :beta do
  gradle(task: "bundle", build_type: "Release", project_dir: "android/")
  upload_to_play_store(
    track: "internal",
    aab: lane_context[SharedValues::GRADLE_AAB_OUTPUT_PATH],
    release_status: "completed",
    skip_upload_metadata: true,   # a beta should not rewrite the store listing
    skip_upload_images: true,
    skip_upload_screenshots: true,
  )
end

lane :promote_to_closed do
  # No build step. `version_code` moves the EXACT artifact already on `internal` to
  # `alpha` (Play's API name for closed testing). Same bytes, new audience.
  upload_to_play_store(
    track: "internal",
    track_promote_to: "alpha",
    version_code: ENV.fetch("VERSION_CODE"),
    skip_upload_aab: true,
    skip_upload_metadata: true,
  )
end

lane :promote_to_production do
  upload_to_play_store(
    track: "alpha",
    track_promote_to: "production",
    version_code: ENV.fetch("VERSION_CODE"),
    skip_upload_aab: true,
    # 10% first. `rollout` only applies to production/open tracks.
    rollout: "0.1",
    release_status: "inProgress",
  )
end
```

**Track names in the API are historical**: `internal`, `alpha` (= closed testing), `beta`
(= open testing), `production`. The Console shows the friendly names; `supply` wants these. This
mismatch is the single most common "why did my build go to the wrong track".

## Version codes: monotonic, or the upload is rejected

Play requires a **strictly increasing** `versionCode` per upload. It is an integer, not a
version string, and it can never go backwards or repeat.

```groovy
// android/app/build.gradle  ✅ derived, never hand-edited
android {
    defaultConfig {
        // Monotonic and collision-free across branches. A number in git is not.
        versionCode System.getenv("VERSION_CODE")?.toInteger() ?: 1
        versionName "1.4.0"     // marketing version — this one lives in the repo
    }
}
```

```yaml
env:
  VERSION_CODE: ${{ github.run_number }}   # monotonic, free, survives re-runs
```

`versionName` is what users see; `versionCode` is what Play orders by. Bumping the name without
the code is rejected; bumping the code without the name is fine and normal for betas.

## Staged rollout — the only stoppable production deploy

```ruby
lane :halt_rollout do
  # The whole reason to stage. Stops NEW users getting the bad build; it does not
  # un-install it from those who already updated.
  upload_to_play_store(
    track: "production",
    version_code: ENV.fetch("VERSION_CODE"),
    skip_upload_aab: true,
    release_status: "halted",
  )
end
```

The rollout discipline that makes it worth doing:

1. **10%**, then wait for real signal — crash-free rate and ANRs in Play Console vitals, plus
   your own Sentry. An hour is not signal; a full daily cycle usually is.
2. **Only increase on evidence.** "Nothing looks wrong" from a 30-minute window at 10% is 3% of
   users for half an hour.
3. **Halt costs nothing.** Halting and resuming is cheap; a bad build at 100% is not.
4. **There is no rollback.** Halting stops new installs; users who already updated keep the bad
   version. The fix is a *new* higher `versionCode` rolled out in turn. Plan forward, never
   backward.

> That last point is the one people get wrong under pressure: they look for the "undo" button.
> There isn't one. The recovery is always to ship again — which means your pipeline must be
> fast enough to ship a fix, and that is a property you build *before* the incident.

## Service account permissions

CI uploads with a **service account**, not a person. Grant it *Release to testing tracks* only if
that is all it does — a beta pipeline holding production release rights is a production deploy
one bad merge away. See `../mobile-signing/references/android-keystores.md` for the setup, and
run `fastlane run validate_play_store_json_key` to prove the wiring before you need it.

## First upload is manual, and only the first

Play will not accept an API upload for an app whose **first** bundle has never been uploaded
through the Console. Do that once, by hand, then automate everything after it. Teams lose an
afternoon to this expecting a fresh app to be automatable from zero.
