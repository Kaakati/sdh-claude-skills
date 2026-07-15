# Apple Identities — certificates, App IDs, profiles, keys

Load-bearing rules restated (hold even if you read nothing else):

1. **Revoking a certificate invalidates every provisioning profile built on it.** This is the
   most common self-inflicted signing outage.
2. **`.p8` keys download exactly once.** Save at creation or generate a new one.
3. **CI authenticates with an App Store Connect API key, never a human's Apple ID.**

---

## The four things, and how they relate

Apple's signing is four objects that people call "the certificate" indiscriminately. The errors
only make sense once they are separate in your head:

```
Certificate  = WHO is allowed to sign          (tied to a private key in a Keychain)
App ID       = WHICH app, and what it may do   (bundle id + capabilities)
Device       = WHICH hardware may run it       (development/ad-hoc only)
Provisioning = a signed bundle of the three: certificate + App ID + devices
   Profile     -> this is what is embedded in the .ipa
```

A build fails when any one of the four disagrees with the others. The error message names the
symptom, never the disagreement.

## Decoding the two errors you will actually hit

| Error | What it really means | Fix |
|---|---|---|
| *"No signing certificate 'iOS Distribution' found"* | This **machine's Keychain** has no private key for a distribution certificate. The certificate may exist perfectly well in the portal — a certificate without its private key is useless. | Import the `.p12` (which contains the private key), or `match` it |
| *"Provisioning profile doesn't include signing certificate"* | The profile was built naming a **different** certificate than the one you're signing with — usually because someone reissued the cert and didn't rebuild the profiles. | Regenerate the profile against the current cert |

> **The trap:** a developer hits the first error, sees a "broken" certificate in the portal, and
> **revokes** it to make a clean one. That revocation invalidates every provisioning profile
> built on it — including production — so an annoyance becomes an outage for everyone. **Never
> revoke to troubleshoot.** A certificate is not the problem; its absence from *your* Keychain
> is.

## Certificate types — pick the narrow one

| Type | Signs | Notes |
|---|---|---|
| Apple Development | Debug builds on registered devices | Per developer |
| Apple Distribution | App Store + Ad Hoc builds | **The one CI needs** |
| APNs Auth Key (`.p8`) | Push, for all your apps | Doesn't expire — prefer over legacy push certs |
| App Store Connect API Key (`.p8`) | API/CI authentication | Replaces a human Apple ID in CI |

Apple limits how many distribution certificates an account may hold. When you hit the ceiling
the answer is **share the existing one via `match`**, not revoke-and-recreate — see the trap
above.

## The two `.p8` keys — download once, then never again

Both are generated in the portal, both download **exactly once**, and neither can be recovered.
Save them to the secret manager in the same minute you create them.

- **APNs Auth Key** — Keys → `+` → Apple Push Notifications service. One key works across all
  your apps and **does not expire**, which is why it beats the legacy per-app `.p12` push
  certificate that silently expired every year. Note the **Key ID** and your **Team ID**; the
  server needs both plus the file.
- **App Store Connect API Key** — Users and Access → Integrations → App Store Connect API.
  Note **Key ID** and **Issuer ID**. Give it the narrowest role that works: *App Manager* is
  usually enough to upload builds and manage TestFlight; *Admin* is not required and hands CI
  the ability to change your agreements and users.

Lost one? You cannot re-download. Revoke it and issue a new one — and remember every server or
CI job holding the old one now fails, so do it deliberately.

## fastlane match — the answer to "it works on my machine"

`match` keeps one set of certificates and profiles in an **encrypted** git repo (or S3). Every
machine and CI job syncs the same identities, so the "no signing certificate found" class of
error stops existing.

```ruby
# fastlane/Matchfile  ✅
git_url("git@github.com:acme/certificates.git")   # PRIVATE repo, contents encrypted by match
storage_mode("git")
type("appstore")
app_identifier(["com.acme.app"])
# No Apple ID here: CI authenticates with an App Store Connect API key (below).
```

```bash
# One person, once: creates the identities and pushes them encrypted.
fastlane match appstore

# Every other machine, and CI: read-only. --readonly is the important flag — it makes it
# IMPOSSIBLE for a CI job to "helpfully" regenerate a certificate, which would revoke the
# existing one and break every other machine's profiles.
fastlane match appstore --readonly
```

The match repo is encrypted with a passphrase (`MATCH_PASSWORD`). That passphrase is a
credential with the same blast radius as the certificates themselves — secret manager, not
Slack.

## Authenticating CI without a human

```ruby
# fastlane/Fastfile  ✅
lane :ci_setup do
  api_key = app_store_connect_api_key(
    key_id: ENV.fetch("ASC_KEY_ID"),
    issuer_id: ENV.fetch("ASC_ISSUER_ID"),
    # The .p8 contents, base64'd into a CI secret. `is_key_content_base64` avoids ever
    # writing the key to disk in the workspace.
    key_content: ENV.fetch("ASC_KEY_CONTENT_B64"),
    is_key_content_base64: true,
    in_house: false,
  )

  # An ephemeral keychain: created for this job, destroyed with the runner. On a shared
  # runner, importing into the login keychain leaves your distribution key behind for the
  # next job — which may not be yours.
  setup_ci if ENV["CI"]

  match(type: "appstore", readonly: true, api_key: api_key)
end
```

Why an API key rather than an Apple ID: it survives the developer leaving, it never prompts for
2FA at 2am, and it can be scoped. A human Apple ID in CI grants CI everything that human can do.

## App IDs and capabilities — the mismatch that builds fine and crashes later

The App ID declares what the app may do (Push, Sign in with Apple, App Groups, HealthKit…). The
entitlements file declares what the binary *asks* for. When they disagree, the build often
succeeds and the feature fails on device — or the upload is rejected after the build.

```xml
<!-- ios/App/App.entitlements -->
<key>aps-environment</key>
<string>production</string>   <!-- requires Push Notifications enabled on the App ID -->
```

Changing capabilities on an App ID **invalidates its provisioning profiles** — they encode the
entitlements. Regenerate profiles (`match` does this) after any capability change, or you get
"profile doesn't match entitlements" on the next build.

## Expiry — put it in the calendar, not in your memory

- **Distribution certificate** expires. When it does, every profile built on it stops working.
- **Provisioning profiles** expire, and are invalidated early by a cert revocation or a
  capability change.
- **APNs `.p8`** does not expire — one less annual outage.

Renew *before* expiry, on a normal Tuesday. The failure mode of "renew when it breaks" is that
it breaks on the day you're shipping, and the fastest-looking fix is the revoke that takes
everyone else down with you.
