# TestFlight — internal speed, external review

Load-bearing rules restated (hold even if you read nothing else):

1. **Internal = up to 100 team members with App Store Connect roles. External = up to 10,000,
   and the first build of a group goes to Beta App Review.**
2. **Builds expire after 90 days.** A "stable" beta silently dies on your testers.
3. **Never add a non-employee as an internal tester** — it requires giving them a real role on
   your app.

---

## The two audiences, exactly as Apple defines them

**Internal** — *"up to 100 members of your development team who hold the Account Holder, Admin,
App Manager, Developer, or Marketing role."* They are App Store Connect users. That is the whole
constraint, and it is also the catch: making someone an internal tester means **granting them a
role on your app**. Marketing is the narrowest of those roles and is the right answer for a
non-engineer who only needs the build.

**External** — *"up to 10,000 external testers."* Apple: *"you'll first create a group in App
Store Connect, add the builds you'd like them to test, and have your first build already approved
by App Review for TestFlight. Your builds are automatically sent for review once they're added
to a group."*

So external is not "internal with more people". It is a **review gate**, on Apple's schedule,
that you cannot expedite by wanting it more.

## Decision: which do I use?

| Situation | Use | Because |
|---|---|---|
| Daily QA loop | Internal | No external review gate; testers are already on the team |
| Demo to a client tomorrow | Internal **if** they can hold a role; otherwise plan for review | External review is not a same-day operation |
| 500-customer beta | External | Internal caps at 100, and outsiders should not have roles |
| Regression sweep before a release | Internal | Speed matters more than breadth here |

## The 90-day expiry is a scheduled outage

*"Builds remain available for testing for up to 90 days"*, then *"your build becomes unavailable
for testers."* Teams that ship a beta and move on discover this as "TestFlight is broken" three
months later, usually from the one tester who still cared.

- Ship a fresh build to your beta group at least quarterly, even if nothing changed.
- If a long-running beta matters, put the expiry date in the same calendar as your certificate
  expiries — it is the same class of failure.

## Uploading — and the wait you should not block on

```ruby
# fastlane/Fastfile  ✅
lane :beta do
  setup_ci if ENV["CI"]
  api_key = app_store_connect_api_key(
    key_id: ENV.fetch("ASC_KEY_ID"),
    issuer_id: ENV.fetch("ASC_ISSUER_ID"),
    key_content: ENV.fetch("ASC_KEY_CONTENT_B64"),
    is_key_content_base64: true,
  )
  match(type: "appstore", readonly: true, api_key: api_key)

  # Ask Apple what it already has, rather than trusting a number in the repo. Two branches
  # cannot collide on this, and it survives a re-run.
  increment_build_number(
    build_number: app_store_build_number(api_key: api_key, live: false, initial_build_number: 0) + 1,
    xcodeproj: "ios/App.xcodeproj",
  )

  build_app(
    workspace: "ios/App.xcworkspace",
    scheme: "App",
    export_method: "app-store",
    # Release config: a beta built in Debug is a different binary and will not reproduce
    # the crash you are chasing.
    configuration: "Release",
  )

  upload_to_testflight(
    api_key: api_key,
    # Do NOT block a CI runner for 5-20 minutes of Apple-side processing. Distribute to
    # internal testers automatically once it finishes, on Apple's clock, not yours.
    skip_waiting_for_build_processing: true,
    distribute_external: false,
    groups: ["Internal QA"],
    changelog: File.read("fastlane/metadata/beta_changelog.txt"),
  )

  # Crash reports are unreadable without these, and the beta is FOR the crash reports.
  upload_symbols_to_crashlytics(dsym_path: lane_context[SharedValues::DSYM_OUTPUT_PATH])
end
```

`skip_waiting_for_build_processing: true` is the difference between a 3-minute job and a
20-minute one. The tradeoff is honest: fastlane cannot set the changelog *after* processing, so
supply it at upload, and accept that a processing failure surfaces in App Store Connect rather
than as a red CI job. If you need CI to fail on a bad build, set it to `false` and pay the wait.

## External distribution, when you actually need it

```ruby
lane :beta_external do
  # ... build as above ...
  upload_to_testflight(
    api_key: api_key,
    distribute_external: true,
    groups: ["Public Beta"],
    # Required for external: Apple asks what changed, and a reviewer reads it.
    changelog: File.read("fastlane/metadata/beta_changelog.txt"),
    beta_app_review_info: {
      contact_email: "release@acme.com",
      contact_first_name: "Release",
      contact_last_name: "Team",
      contact_phone: "+10000000000",
      # If the reviewer cannot log in, you are rejected and you wait again. This is the
      # single most common Beta App Review rejection and it is entirely self-inflicted.
      demo_account_name: ENV["DEMO_ACCOUNT_USER"],
      demo_account_password: ENV["DEMO_ACCOUNT_PASSWORD"],
      notes: "Sign in with the demo account. New: checkout with saved cards.",
    },
  )
end
```

Give the reviewer a **working demo account** and say so in the notes. A reviewer who cannot get
past your login screen rejects the build, and the clock restarts.

## "Stuck in Processing" — what it usually is

Processing takes minutes, not hours. When it doesn't finish, it is almost never Apple:

| Symptom | Usual cause |
|---|---|
| Processing, then an email "invalid binary" | Missing/invalid entitlement, or a bitcode/arch problem — read the email, it names it |
| Processing forever, no email | Missing export compliance answer — set `ITSAppUsesNonExemptEncryption` in `Info.plist` or it waits on a human |
| Build never appears | It uploaded to a **different app record** — check the bundle id |
| "Missing compliance" badge | Same as above; automate it rather than clicking it each build |

```xml
<!-- ios/App/Info.plist — answers the export-compliance question at build time -->
<key>ITSAppUsesNonExemptEncryption</key>
<false/>
```

Set this deliberately: `false` is correct for apps using only standard HTTPS. If you ship your
own crypto, it is not, and the answer has legal weight.

## Groups are the unit of control

- Create a group per audience (`Internal QA`, `Design`, `Public Beta`), not one big list.
- A build is distributed *to groups*; adding a build to an external group **automatically sends
  it for review**. That is a decision, so make it in a lane, not by clicking.
- Removing a tester from a group revokes their access to future builds, not the installed one.

## Verify the tester experience, not just the upload

The lane going green means Apple accepted a binary. It does not mean a human can install it.
Once per release cycle, install from TestFlight on a real device as a real tester — the first
time you discover the group is empty or the build expired should not be during a demo.
