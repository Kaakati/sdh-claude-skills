# fastlane Lanes — one beta command per platform

Load-bearing rules restated (hold even if you read nothing else):

1. **`bundle exec fastlane` with a committed `Gemfile.lock`.** An unpinned fastlane is a build
   that changes under you.
2. **Derive the build number in CI; keep the marketing version in the repo.**
3. **Upload dSYMs / mapping files with every beta**, or the crash reports it exists to produce
   are unreadable.

---

## Why lanes rather than CI steps

A beta you can only ship from CI is a beta you cannot debug. Put the logic in a **lane**, and
let CI call the same command a developer runs:

```bash
bundle exec fastlane ios beta        # identical locally and in CI
bundle exec fastlane android beta
```

When the release breaks at 6pm, the person fixing it runs the exact thing CI ran. Logic spread
across twelve YAML `run:` steps cannot be reproduced anywhere but CI, which is precisely where
you cannot iterate.

## Pin fastlane

```ruby
# Gemfile  ✅ committed alongside Gemfile.lock
source "https://rubygems.org"
gem "fastlane"
```

```bash
bundle install && git add Gemfile.lock
```

Always `bundle exec`. A globally-installed fastlane means your machine, the next developer's,
and CI are running three different tools — and the resulting "works for me" is unfalsifiable.
This is the same *pin, don't float* discipline the plugin applies to itself.

## The shape

```ruby
# fastlane/Fastfile
default_platform(:ios)

# --- shared ---------------------------------------------------------------
# Release notes tell testers WHAT TO TEST. "Bug fixes and improvements" wastes the build:
# a tester who doesn't know what changed reports nothing useful.
def beta_changelog
  path = "fastlane/metadata/beta_changelog.txt"
  return File.read(path) if File.exist?(path)
  # Fall back to commit subjects since the last tag — imperfect, better than nothing,
  # and it makes the missing-changelog case visible rather than silent.
  changelog_from_git_commits(pretty: "- %s", merge_commit_filtering: "exclude_merges")
end

platform :ios do
  desc "Build and ship to TestFlight internal testers"
  lane :beta do
    setup_ci if ENV["CI"]   # ephemeral keychain; see mobile-signing

    api_key = app_store_connect_api_key(
      key_id: ENV.fetch("ASC_KEY_ID"),
      issuer_id: ENV.fetch("ASC_ISSUER_ID"),
      key_content: ENV.fetch("ASC_KEY_CONTENT_B64"),
      is_key_content_base64: true,
    )

    match(type: "appstore", readonly: true, api_key: api_key)

    increment_build_number(
      build_number: app_store_build_number(api_key: api_key, live: false, initial_build_number: 0) + 1,
      xcodeproj: "ios/App.xcodeproj",
    )

    build_app(
      workspace: "ios/App.xcworkspace",
      scheme: "App",
      configuration: "Release",
      export_method: "app-store",
    )

    upload_to_testflight(
      api_key: api_key,
      skip_waiting_for_build_processing: true,
      distribute_external: false,
      groups: ["Internal QA"],
      changelog: beta_changelog,
    )

    upload_symbols_to_crashlytics(dsym_path: lane_context[SharedValues::DSYM_OUTPUT_PATH])
  end
end

platform :android do
  desc "Build and ship to the Play internal testing track"
  lane :beta do
    gradle(task: "clean", project_dir: "android/")
    gradle(
      task: "bundle",
      build_type: "Release",
      project_dir: "android/",
      # VERSION_CODE comes from CI (github.run_number): monotonic, collision-free across
      # branches, and it survives a re-run. A number in git does none of those.
      system_properties: { "versionCode" => ENV.fetch("VERSION_CODE") },
    )

    upload_to_play_store(
      track: "internal",
      aab: lane_context[SharedValues::GRADLE_AAB_OUTPUT_PATH],
      release_status: "completed",
      skip_upload_metadata: true,     # a beta must not rewrite the store listing
      skip_upload_images: true,
      skip_upload_screenshots: true,
    )

    # R8 obfuscates release builds: without the mapping file every stack trace is noise.
    upload_symbols_to_crashlytics(
      mapping_path: "android/app/build/outputs/mapping/release/mapping.txt",
    )
  end
end
```

## Bad — the lane that lies about failing

```ruby
lane :beta do
  build_app(scheme: "App")
  # ❌ swallows the failure: the job goes green, and nobody gets a build. You find out
  # when a tester asks where it is — a day later, from the wrong person.
  begin
    upload_to_testflight
  rescue => e
    UI.message("upload failed: #{e}")
  end
end
```

A beta pipeline that cannot fail is a beta pipeline you cannot trust. If a step is genuinely
optional (symbol upload to a third party, a Slack ping), say so explicitly and *say it loudly*:

```ruby
  # ✅ optional, and visibly optional
  begin
    slack(message: "Beta #{lane_context[SharedValues::BUILD_NUMBER]} is up")
  rescue => e
    UI.important("Slack notification failed (build IS uploaded): #{e}")
  end
```

The build succeeding and the notification failing are different facts. Conflating them is how a
green pipeline ships nothing.

## CI wiring

```yaml
# .github/workflows/beta.yml
name: Beta

on:
  workflow_dispatch:
  push:
    branches: [develop]

permissions:
  contents: read

jobs:
  ios:
    runs-on: macos-14
    environment: beta          # scopes the signing secrets; blocks fork PRs from reaching them
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }   # changelog_from_git_commits needs history
      - uses: ruby/setup-ruby@v1
        with: { bundler-cache: true }
      - run: bundle exec fastlane ios beta
        env:
          ASC_KEY_ID: ${{ secrets.ASC_KEY_ID }}
          ASC_ISSUER_ID: ${{ secrets.ASC_ISSUER_ID }}
          ASC_KEY_CONTENT_B64: ${{ secrets.ASC_KEY_CONTENT_B64 }}
          MATCH_PASSWORD: ${{ secrets.MATCH_PASSWORD }}
          MATCH_GIT_BASIC_AUTHORIZATION: ${{ secrets.MATCH_GIT_BASIC_AUTHORIZATION }}

  android:
    runs-on: ubuntu-latest
    environment: beta
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: ruby/setup-ruby@v1
        with: { bundler-cache: true }
      - uses: actions/setup-java@v4
        with: { distribution: temurin, java-version: "17" }
      - name: Materialise credentials
        env:
          ANDROID_KEYSTORE_B64: ${{ secrets.ANDROID_KEYSTORE_B64 }}
          PLAY_SERVICE_ACCOUNT_JSON_B64: ${{ secrets.PLAY_SERVICE_ACCOUNT_JSON_B64 }}
        run: |
          # RUNNER_TEMP, never the workspace — see mobile-signing/references/ci-signing-secrets.md
          echo "$ANDROID_KEYSTORE_B64" | base64 -d > "$RUNNER_TEMP/upload.jks"
          echo "$PLAY_SERVICE_ACCOUNT_JSON_B64" | base64 -d > "$RUNNER_TEMP/play.json"
          echo "ANDROID_KEYSTORE_PATH=$RUNNER_TEMP/upload.jks" >> "$GITHUB_ENV"
          echo "PLAY_SERVICE_ACCOUNT_JSON_PATH=$RUNNER_TEMP/play.json" >> "$GITHUB_ENV"
      - run: bundle exec fastlane android beta
        env:
          VERSION_CODE: ${{ github.run_number }}
          ANDROID_KEYSTORE_PASSWORD: ${{ secrets.ANDROID_KEYSTORE_PASSWORD }}
          ANDROID_KEY_ALIAS: ${{ secrets.ANDROID_KEY_ALIAS }}
          ANDROID_KEY_PASSWORD: ${{ secrets.ANDROID_KEY_PASSWORD }}
```

The two jobs are deliberately independent: iOS waits on Beta App Review for external groups and
Android does not, so coupling them makes the fast platform wait for the slow one for no reason.

## Keep the lane honest

- **Run it on a schedule**, even with no changes. A beta pipeline that only runs at release time
  is discovered broken at release time — the certificate expired three weeks ago and nothing
  said so.
- **`fetch-depth: 0`** or `changelog_from_git_commits` produces an empty changelog and testers
  get "what changed? nothing."
- Print the build number and track in the job summary. "Uploaded successfully" without saying
  *what*, *where*, is an audit line nobody can act on.
