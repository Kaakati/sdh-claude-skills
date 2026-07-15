# Signing Secrets in CI — held, not leaked

Load-bearing rules restated (hold even if you read nothing else):

1. **Binary credentials travel as base64 in a secret, and are written to a temp path the job
   deletes.** Never into the workspace, never into the repo.
2. **Never `echo` a secret** — CI masks known secret *values*, not what you derive from them.
3. **Scope the credential to the job.** A beta pipeline must not hold production release rights.

---

## Why this file exists separately

The signing identities are the highest-value secrets a mobile team owns: they authorise code to
run on your users' devices. A leaked API key gets rotated; a leaked signing identity is a
supply-chain compromise. And CI is where they are most likely to leak, because CI is where
people debug by printing things.

## Binary credentials: base64 in, file out, file gone

Keystores, `.p12`s and `.p8`s are binary. CI secrets are strings. Base64 is the bridge — and it
is **encoding, not encryption**: a base64 secret in a log is a plaintext secret.

```bash
# Local, once. base64 -w0 keeps it on one line (macOS: base64 -i file).
base64 -w0 upload-keystore.jks    # -> paste into the CI secret ANDROID_KEYSTORE_B64
base64 -w0 AuthKey_ABC123.p8      # -> paste into ASC_KEY_CONTENT_B64
```

```yaml
# .github/workflows/beta.yml  ✅
      - name: Materialise the keystore
        env:
          ANDROID_KEYSTORE_B64: ${{ secrets.ANDROID_KEYSTORE_B64 }}
        run: |
          # RUNNER_TEMP, not the workspace: the workspace can be uploaded as an artifact,
          # cached, or committed by a careless step. RUNNER_TEMP dies with the runner.
          echo "$ANDROID_KEYSTORE_B64" | base64 -d > "$RUNNER_TEMP/upload.jks"
          echo "ANDROID_KEYSTORE_PATH=$RUNNER_TEMP/upload.jks" >> "$GITHUB_ENV"

      - name: Build the bundle
        env:
          ANDROID_KEYSTORE_PASSWORD: ${{ secrets.ANDROID_KEYSTORE_PASSWORD }}
          ANDROID_KEY_ALIAS: ${{ secrets.ANDROID_KEY_ALIAS }}
          ANDROID_KEY_PASSWORD: ${{ secrets.ANDROID_KEY_PASSWORD }}
        run: ./gradlew bundleRelease
```

Note what is absent: no `set -x`, no `echo` of the decoded value, no writing into
`$GITHUB_WORKSPACE`.

## Bad — the four ways this leaks

```yaml
      - name: Debug signing        # ❌ every line here is a real incident
        run: |
          set -x                                   # 1. traces every command WITH its arguments
          echo "${{ secrets.ANDROID_KEYSTORE_PASSWORD }}" | md5sum
                                                   # 2. derived value: masking does not follow it
          base64 -d <<< "${{ secrets.ANDROID_KEYSTORE_B64 }}" > ./release.jks
                                                   # 3. workspace -> may be cached/uploaded
          echo "Signing with ${{ secrets.ANDROID_KEY_ALIAS }} / pass len ${#PASSWORD}"
                                                   # 4. interpolating secrets into a run block
                                                   #    puts them in the shell's history/logs
```

GitHub masks the **exact string** of a registered secret. It cannot mask an md5 of it, a base64
of it, or a substring — and it does not know a file you wrote is sensitive. Masking is a
courtesy, not a boundary.

```yaml
      - uses: actions/upload-artifact@v4
        with:
          path: .                                  # ❌ ships release.jks to anyone with repo read
```

## Good — a job that holds only what it needs

```yaml
# .github/workflows/beta.yml  ✅
name: Beta

on:
  workflow_dispatch:
  push:
    tags: ["beta-*"]

# Least privilege at the job level. This job ships a beta; it has no business
# writing to the repo.
permissions:
  contents: read

jobs:
  ios-beta:
    runs-on: macos-14
    # An environment lets you require a reviewer and scope secrets to it, so a PR from a
    # fork can never reach the signing identities.
    environment: beta
    steps:
      - uses: actions/checkout@v4

      - name: Sign and ship
        env:
          ASC_KEY_ID: ${{ secrets.ASC_KEY_ID }}
          ASC_ISSUER_ID: ${{ secrets.ASC_ISSUER_ID }}
          ASC_KEY_CONTENT_B64: ${{ secrets.ASC_KEY_CONTENT_B64 }}
          MATCH_PASSWORD: ${{ secrets.MATCH_PASSWORD }}
          MATCH_GIT_BASIC_AUTHORIZATION: ${{ secrets.MATCH_GIT_BASIC_AUTHORIZATION }}
        # fastlane reads these from the environment. They are never interpolated into a
        # shell string, so they cannot land in a trace.
        run: bundle exec fastlane ios beta
```

```ruby
# fastlane/Fastfile  ✅
lane :beta do
  setup_ci if ENV["CI"]     # ephemeral keychain, destroyed with the runner
  api_key = app_store_connect_api_key(
    key_id: ENV.fetch("ASC_KEY_ID"),
    issuer_id: ENV.fetch("ASC_ISSUER_ID"),
    key_content: ENV.fetch("ASC_KEY_CONTENT_B64"),
    is_key_content_base64: true,
  )
  # readonly: a CI job must never regenerate a certificate. Regeneration revokes the
  # existing one and breaks every other machine's profiles — from a job nobody was watching.
  match(type: "appstore", readonly: true, api_key: api_key)
  build_app(scheme: "App", export_method: "app-store")
  upload_to_testflight(api_key: api_key, skip_waiting_for_build_processing: true)
end
```

## Fork PRs are the hole people forget

Secrets are not exposed to `pull_request` runs from forks — which is the platform protecting
you. The danger is `pull_request_target`, which runs **with secrets** in the context of the base
repo. Combined with checking out the PR's head, it hands an attacker your signing identity for
the price of one pull request.

```yaml
on: pull_request_target          # ⚠️ has secrets
jobs:
  build:
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}   # ❌ runs attacker code WITH secrets
```

Signing jobs should trigger on `push` to trusted refs, tags, or `workflow_dispatch` — never on
untrusted PR content.

## Rotation, and knowing it worked

- Rotate on a schedule and **on every departure** of someone who had access. "They wouldn't" is
  not an access control.
- Rotating an ASC API key breaks every job holding the old one — do it deliberately, not on
  release day.
- After rotating, **prove** it: run the beta lane. A rotation you didn't verify is a rotation you
  did at the worst possible time.
- Log the *fact* of signing, never the material: `"signed with upload cert SHA1 ab:cd:…"` is a
  useful audit line; the key is not.

## Checklist for a new signing pipeline

1. Credentials in the secret manager **before** the first CI run, verified restorable by someone
   other than the person who made them.
2. `permissions:` least-privilege; a protected `environment` for anything that can publish.
3. Binary secrets base64 → `RUNNER_TEMP` → deleted with the runner.
4. `match(readonly: true)`; a Play service account scoped to testing tracks only.
5. No `set -x`, no `echo`, no secret interpolated into a `run:` string.
6. Rotation runbook written down — see `../incident-response` for the leaked-credential case.
