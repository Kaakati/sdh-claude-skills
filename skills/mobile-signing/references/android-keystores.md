# Android Keystores & Play App Signing

Load-bearing rules restated (hold even if you read nothing else):

1. **Enrol in Play App Signing.** It is the difference between a lost key being an inconvenience
   and the end of the app.
2. **Upload key ≠ app signing key.** You hold the first; Google holds the second.
3. **No password, keystore, or service-account JSON in git.** Ever, in any repo.

---

## The two keys, and why the distinction is the whole chapter

```
   you                          Google Play                     user's device
   ───                          ───────────                     ─────────────
   .aab  --sign with-->  UPLOAD KEY  --upload-->  Play verifies upload key,
                                                  re-signs APKs with the
                                                  APP SIGNING KEY  --------->  installs
```

- **Upload key** — yours. Proves *"this bundle came from us."* If it leaks or is lost, you
  request a reset in Play Console and carry on. Google: *"if you lose your upload key, or if it
  is compromised, you can request an upload key reset in the Play Console."*
- **App signing key** — held by Google, protected by their KMS, **never changes for the life of
  the app**. It is what the device checks on update. You never see it.

**Not enrolled?** Then the key on someone's laptop *is* the app signing key, and:

> *"Google cannot retrieve the app signing key for you, and you will not be able to release new
> versions of your app to users as updates to the original app."* … *"You cannot regenerate a
> previously generated key."*

The recovery is: publish a **new listing**, with a new package name, and ask every existing user
to find and install it. You lose your ratings, your install base, and your deep links.

App Bundles **require** Play App Signing — Play builds and signs the per-device APKs, which it
cannot do without holding the key. Since new apps must ship `.aab`, most teams are enrolled
already. Confirm it rather than assume: **Play Console → your app → Setup → App integrity → App
signing.**

## Bad — the keystore is the app signing key and lives on a laptop

```groovy
// android/app/build.gradle  ❌ three separate disasters
android {
    signingConfigs {
        release {
            // 1. A path to a file that exists on exactly one machine.
            storeFile file("/Users/alex/keys/release.keystore")
            // 2. Literal credentials, about to be committed to git forever.
            storePassword "hunter2-and-friends"
            keyAlias "release"
            keyPassword "hunter2-and-friends"
        }
    }
}
```

3. And if this app predates App Bundles and was never enrolled, that file **is** the app signing
key. When Alex's laptop dies, the app does.

## Good — generate an upload key, keep it out of the repo

```bash
# Generate ONCE. 10000 days ≈ 27 years: a keystore that expires mid-life is a self-inflicted
# version of the unrecoverable case. Prompts for the passwords — do not pass them as flags,
# where they land in your shell history.
keytool -genkeypair -v \
  -keystore upload-keystore.jks \
  -alias upload \
  -keyalg RSA -keysize 2048 -validity 10000
```

Store the file and its passwords in the team's secret manager **immediately** — before the first
build, while you still remember. Then:

```properties
# android/keystore.properties   <-- gitignored, never committed
storeFile=/absolute/path/upload-keystore.jks
keyAlias=upload
```

```groovy
// android/app/build.gradle  ✅ file path from a local, ignored properties file;
// secrets from the environment so CI supplies them and git never sees them.
def keystorePropertiesFile = rootProject.file("keystore.properties")
def keystoreProperties = new Properties()
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(new FileInputStream(keystorePropertiesFile))
}

android {
    signingConfigs {
        release {
            storeFile file(System.getenv("ANDROID_KEYSTORE_PATH")
                ?: keystoreProperties["storeFile"])
            keyAlias System.getenv("ANDROID_KEY_ALIAS")
                ?: keystoreProperties["keyAlias"]
            // No literals. CI injects these; a developer exports them locally.
            storePassword System.getenv("ANDROID_KEYSTORE_PASSWORD")
            keyPassword System.getenv("ANDROID_KEY_PASSWORD")
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled true
            proguardFiles getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro"
        }
    }
}
```

```gitignore
# .gitignore  ✅ belt and braces
*.jks
*.keystore
keystore.properties
play-service-account.json
```

## Enrolling an existing app (the migration that must not be rushed)

If the app already ships and is **not** enrolled, you are one laptop failure from the
unrecoverable case. Fix it deliberately:

1. **Back up the current keystore first**, to the secret manager, verified restorable. Do not
   start until someone other than the author has restored it successfully.
2. Play Console → App integrity → **opt in to Play App Signing**, uploading the existing key as
   the app signing key (Play provides a `PEPK` tool for the export).
3. Generate a **new** upload key (steps above). From now on you sign with the upload key.
4. Keep the old key archived anyway until the first enrolled release is live and verified.

Do not do step 2 and 3 in the same afternoon as a release.

## Resetting a lost or compromised upload key

Only possible because you enrolled — this is the payoff:

1. Generate a new upload keystore.
2. Export its certificate: `keytool -export -rfc -keystore upload-keystore.jks -alias upload -file upload_certificate.pem`
3. Play Console → App integrity → **request upload key reset**, attach the `.pem`.
4. Google swaps the registered upload certificate. The **app signing key is untouched**, so
   users update normally and never notice.

## The Play Console service account (for CI uploads)

CI needs to talk to the Play Developer API. Give it an identity, not a person's Google account.

1. Google Cloud Console → create a **service account** → create a **JSON key**.
2. Play Console → **Users and permissions** → invite the service-account email.
3. Grant **only** what the job needs — typically *Release to testing tracks* and *View app
   information*. Do not grant production release rights to a CI account that only ships betas;
   an over-scoped credential is a production deploy waiting for a bad merge.
4. Store the JSON in CI secrets. It is a credential: same rules as the keystore.

```ruby
# fastlane/Appfile  ✅ path from env; the file itself is written at runtime from a secret
json_key_file(ENV["PLAY_SERVICE_ACCOUNT_JSON_PATH"])
package_name("com.acme.app")
```

Verify the wiring before you need it: `fastlane run validate_play_store_json_key` fails loudly
now rather than at 5pm on release day.

## Verifying what you actually shipped

```bash
# Which key signed this bundle? (should be your UPLOAD key — Play re-signs afterwards)
jarsigner -verify -verbose -certs app-release.aab | grep -A1 "Signed by"

# Fingerprint of a keystore, to compare against Play Console -> App integrity
keytool -list -v -keystore upload-keystore.jks -alias upload | grep SHA1
```

Play Console shows both the **upload certificate** and the **app signing certificate**
fingerprints. If an upload is rejected with a signing mismatch, compare your keystore's SHA-1
against the *upload* certificate — not the app signing one. Confusing the two is the most common
reason teams "fix" a working setup by regenerating the wrong key.

> The SHA-1/SHA-256 of the **app signing** certificate is what third parties need (Google Maps
> keys, Firebase, Facebook login) — because that is what is on the user's device. Handing them
> the upload fingerprint is why "it works in debug, breaks in production."
