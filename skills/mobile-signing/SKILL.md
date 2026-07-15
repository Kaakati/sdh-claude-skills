---
name: mobile-signing
description: iOS and Android code-signing identity management — Apple certificates, App IDs, provisioning profiles, APNs (.p8) and App Store Connect API keys, fastlane match; Android upload key vs app signing key, keystores, Play App Signing, and Play Console service accounts. Use when setting up or fixing code signing, when a certificate or provisioning profile expires, when a build fails to sign in CI, when rotating or resetting keys, when onboarding a machine or a new developer to signing, or when someone asks about keystores, .p8 keys, match, Play App Signing, "no signing certificate found", "provisioning profile doesn't include signing certificate", or "upload key vs app signing key".
model: sonnet
---

# Mobile Signing — identities you cannot regenerate

Signing is the one part of mobile release engineering where a mistake is **permanent**. Most
build problems are annoying; losing an app signing key means **you can never update that app
again** — not "call support", not "restore from backup". Google's own words:

> *"If you lose access to your app signing key or your key is compromised, Google cannot retrieve
> the app signing key for you, and you will not be able to release new versions of your app to
> users as updates to the original app."* … *"You cannot regenerate a previously generated key."*

So this skill's rules are ordered by **blast radius**, not by workflow.

## The irreversibility table — read this before touching anything

| Identity | Lose it and… | Recoverable? |
|---|---|---|
| **Android app signing key**, *not* enrolled in Play App Signing | The app is dead. You ship a **new listing** and every user must reinstall manually. | ❌ **Never** |
| **Android app signing key**, enrolled in Play App Signing | Nothing — Google holds it. | ✅ n/a |
| **Android upload key** | Nothing lasting — request a reset in Play Console. | ✅ Reset |
| **Apple distribution certificate** | Revoke and reissue; rebuild profiles. Annoying, not fatal. | ✅ Reissue |
| **APNs auth key (.p8)** | Cannot re-download; generate a new one and update servers. | ⚠️ Replace |
| **App Store Connect API key (.p8)** | Cannot re-download; revoke and issue a new one. | ⚠️ Replace |

**The single highest-value action in this whole skill: enrol in Play App Signing.** It converts
the only unrecoverable failure in the table into a recoverable one. It is also **required** for
Android App Bundles, which are required for new apps — so most teams already have it and don't
know what it bought them.

## The rule that prevents the disaster

**You upload with the upload key. Google signs with the app signing key.** They are different
keys with different owners, and conflating them is why teams think a lost keystore is survivable
(it is, *only* if enrolled) or panic when it isn't (it isn't, if not).

- Never commit a keystore or a `.p8`/`.p12` to git — ever, even a private repo, even briefly.
  Git history is forever and a leaked signing key is a supply-chain compromise of every user's
  device.
- Never email or Slack them. Use the team's secret manager.
- **Back up the upload keystore and its passwords** somewhere the team — not one laptop — can
  reach. The developer who generated it will leave.
- `.p8` files **download exactly once**. Save them at creation or start over.

## Decision: how do we distribute signing identities?

| Team shape | Approach | Why |
|---|---|---|
| More than one developer, or any CI | **fastlane match** (Apple) | One encrypted git/S3 store; machines sync, nobody hand-manages Keychain |
| Solo, no CI | Xcode automatic signing | match's setup cost isn't repaid yet |
| Any Android | **Play App Signing + upload keystore in CI secrets** | The only posture where a lost key isn't fatal |
| Enterprise / strict | App Store Connect API key + short-lived CI creds | No human Apple ID in CI |

**Do not let CI use a person's Apple ID.** It breaks when they leave, when 2FA prompts, and it
grants CI everything that human can do. Use an **App Store Connect API key** scoped to the job.

## Expiry is a scheduled outage you can see coming

Certificates and profiles expire on a fixed date, and the failure always lands the morning of a
release. Put the dates in a calendar the team reads:

- Apple distribution certificate → **expires; rebuild/reissue before it does**
- Provisioning profiles → expire, and **a profile is invalidated when its certificate is
  revoked** (revoking a "broken" cert breaks every profile built on it — this is the classic
  self-inflicted outage)
- APNs `.p8` auth key → does **not** expire (its advantage over legacy `.p12` push certs)
- Play upload/app signing keys → set a long validity (25+ years) at creation; a keystore that
  expires mid-life is a self-inflicted version of the unrecoverable case

## Deep guides (read on demand, do not preload)

- Apple identities end-to-end — certificate types, App IDs & capabilities, provisioning profile
  anatomy, the `.p8` keys, fastlane match, and decoding the real meaning of "no signing
  certificate found" / "profile doesn't include signing certificate"
  → `references/ios-identities.md`
- Android keystores — generating an upload key, enrolling in Play App Signing, what Google holds
  vs what you hold, resetting a lost upload key, Play Console service accounts, and the
  `signingConfigs` that must never contain a literal password
  → `references/android-keystores.md`
- Holding these secrets in CI — base64 round-tripping, ephemeral keychains, what must never be
  echoed, and least-privilege API keys → `references/ci-signing-secrets.md`

Shipping the signed build to testers is a separate task — see the `mobile-beta-release` skill.
