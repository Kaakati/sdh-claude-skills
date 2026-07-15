---
name: i18n
description: Implement internationalization (i18n) and localization (l10n) for Rails backends, React Native mobile, ReactJS Vite SPA, and Next.js web apps. Use this skill whenever someone asks about translations, locales, internationalization, or says things like "add i18n support", "translate this", "support multiple languages", "add locale", "RTL support", "pluralization", "localize the app", or "web translations". Also trigger for date/currency/number formatting across locales, CSS logical properties for RTL, or server component i18n.
model: sonnet
---

# Internationalization (i18n)

Internationalization across the stack: Rails API, React Native, ReactJS Vite SPA, Next.js App
Router.

## The decisions that outlive the strings

Translating is the easy part. These four are what you cannot cheaply undo later:

| Decision | Get it wrong and… |
|---|---|
| **Who localizes — server or client?** | Two sources of truth for one message, drifting |
| **What is the key namespace?** | A rename becomes a migration across four codebases |
| **Is RTL ever in scope?** | Retrofitting `left`/`right` across an entire UI |
| **Where does the locale live?** | A shared link opens in the wrong language |

## Decision: does the server or the client localize this?

| The text | Localize in | Because |
|---|---|---|
| UI labels, buttons, empty states | **Client** | The server has no business knowing your button text |
| Validation errors shown inline | **Client**, from an error **code** | The API returns `code: "TOO_SHORT"`; the client owns the wording |
| Emails, push notifications, PDFs | **Server** | There is no client at send time |
| Anything a support agent reads back | Server, logged in **English** | Your logs are not localized |

**The API returns codes, not sentences.** A localized API string is a UI decision made in the
wrong layer: you cannot re-word it without a backend deploy, and a second client gets whatever
the first one needed. Where the server must localize (email), use the user's **stored
preference** — `Accept-Language` is a hint from whatever browser they happened to open, not an
identity.

## Non-negotiables (every platform)

- **If a human reads it, it is a key.** No user-facing literal in a component, view, or
  serializer. `i18n-checker.py` warns on **two of those three**: it inspects `.tsx`/`.jsx` and
  `.erb`, so a hardcoded string in a **Panko serializer (`.rb`) is not caught by anything** — that
  one is on you, and it is the one that reaches the API consumer rather than the page. The rule
  lives in `std-i18n`.
- **Keys are namespaced and hierarchical**: `orders.checkout.submit_button`. Never use the
  English text as the key; that turns a copy edit into a code change in every locale.
- **`en` is the fallback and the source of truth.** Every other locale is a delta from it.
- **Interpolate, never concatenate.** `t('greeting', { name })`, not `t('hello') + name` — word
  order is not universal, so a concatenation cannot be translated at all.
- **Pluralization is a library feature, not an `if`.** Arabic has six plural forms; a
  `count === 1 ? a : b` is wrong in most of the world.
- **Never delete a key that ships in a released mobile client.** Old app versions still request
  it and will render blank. Deprecate, remove a release later.

## RTL is a layout problem, not a text problem

The moment Arabic or Hebrew is plausible, **stop writing `left`/`right`** — everywhere.

- **Web**: CSS logical properties (`margin-inline-start`, `padding-inline-end`,
  `text-align: start`). Free, and no `dir`-specific stylesheet.
- **React Native**: `start`/`end` in styles. `I18nManager.forceRTL` **requires an app restart**,
  so it is a settings action, not a runtime toggle.
- Directional icons (arrows, chevrons) mirror; logos and media do not.

Retrofitting this later means auditing every style in the app. Deciding now costs nothing.

## Where the locale lives

**The URL** (`/ar/orders`) on web — a shared link must open in the language it was shared in, and
a cookie cannot survive being pasted into Slack. Persist the *preference* server-side for a
signed-in user; the URL still wins for the current request.

## CI is what keeps the locales honest

A missing key is invisible until a user sees a blank label or a raw key on screen. That must hold
whether or not anyone reads this file — so it is a gate, not a rule:

- fail when a key exists in `en` but not in another locale (or the reverse);
- fail on an unused key — dead weight a translator is still being paid for;
- keep locale files sorted, so merges conflict on content rather than on line order.

## Deep guides (read on demand, do not preload)

- Rails: locale file organization, lazy lookup, pluralization, API responses, date/number
  formatting → `references/rails-i18n.md`
- React Native: `react-i18next` setup, locale file structure, type-safe keys, and RTL including
  `I18nManager` and mirrored components → `references/react-native-i18n.md`
- Web: Vite SPA locale detection, Next.js Server vs Client Component i18n, locale routing, CSS
  logical properties → `references/web-i18n.md`
- Adding a locale, key rules, and the deprecation path → `references/locale-workflow.md`

Related, owned elsewhere — do not duplicate: the path-scoped conventions that auto-load when you
edit a locale file or a component live in `std-i18n`; RTL's accessibility implications live in
`../std-accessibility`.
