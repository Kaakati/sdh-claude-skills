---
name: i18n
description: Implement internationalization (i18n) and localization (l10n) for Rails backends, React Native mobile, ReactJS Vite SPA, and Next.js web apps. Use this skill whenever someone asks about translations, locales, internationalization, or says things like "add i18n support", "translate this", "support multiple languages", "add locale", "RTL support", "pluralization", "localize the app", or "web translations". Also trigger for date/currency/number formatting across locales, CSS logical properties for RTL, or server component i18n.
model: sonnet
---

# Internationalization (i18n)

Implement and maintain internationalization across the full stack: Rails API backend, React Native mobile, ReactJS Vite SPA, and Next.js App Router web frontends.

## Rails Backend i18n

### Setup

Use Rails built-in i18n framework. No additional gems needed for basic i18n.

```ruby
# config/application.rb
config.i18n.default_locale = :en
config.i18n.available_locales = [:en, :ar, :fr, :es, :de]
config.i18n.fallbacks = true
config.i18n.enforce_available_locales = true
```

### Locale File Organization

```
config/locales/
├── en/
│   ├── models.en.yml        # ActiveRecord model names and attributes
│   ├── errors.en.yml        # Error messages
│   ├── notifications.en.yml # Push notification templates
│   ├── mailers.en.yml       # Email templates
│   └── api.en.yml           # API response messages
├── ar/
│   ├── models.ar.yml
│   ├── errors.ar.yml
│   └── ...
└── defaults/
    └── devise.en.yml        # Devise-specific translations
```

### Translation Key Naming

Follow dot-separated hierarchical keys matching the domain structure:

```yaml
# config/locales/en/errors.en.yml
en:
  errors:
    not_found: "%{resource} not found"
    unauthorized: "You are not authorized to perform this action"
    validation:
      blank: "%{field} cannot be blank"
      too_short: "%{field} is too short (minimum %{count} characters)"
      taken: "%{field} is already taken"

# config/locales/en/models.en.yml
en:
  activerecord:
    models:
      user: "User"
      order: "Order"
    attributes:
      user:
        email: "Email address"
        full_name: "Full name"
```

### Lazy Lookup in Rails

Use lazy lookup in controllers and mailers to keep keys DRY:

```ruby
# app/controllers/api/v1/orders_controller.rb
class Api::V1::OrdersController < ApplicationController
  def create
    # Looks up: en.api.v1.orders.create.success
    render json: { message: t('.success') }
  end
end
```

### Pluralization

Rails handles pluralization rules per locale:

```yaml
en:
  orders:
    count:
      zero: "No orders"
      one: "%{count} order"
      other: "%{count} orders"

ar:
  orders:
    count:
      zero: "لا طلبات"
      one: "طلب واحد"
      two: "طلبان"
      few: "%{count} طلبات"
      many: "%{count} طلبًا"
      other: "%{count} طلب"
```

### API Response i18n

Set locale from request header in the base controller:

```ruby
# app/controllers/application_controller.rb
class ApplicationController < ActionController::API
  before_action :set_locale

  private

  def set_locale
    locale = request.headers['Accept-Language']&.scan(/^[a-z]{2}/)&.first
    I18n.locale = I18n.available_locales.map(&:to_s).include?(locale) ? locale : I18n.default_locale
  end
end
```

### Date, Time, and Number Formatting

```yaml
en:
  date:
    formats:
      default: "%Y-%m-%d"
      short: "%b %d"
      long: "%B %d, %Y"
  number:
    currency:
      format:
        unit: "$"
        precision: 2
        separator: "."
        delimiter: ","
```

Use `I18n.l(date, format: :short)` and `number_to_currency(amount)` — never format manually.

## React Native i18n

### Libraries

Use `i18next` + `react-i18next` + `react-native-localize` for device locale detection:

```bash
npm install i18next react-i18next react-native-localize
```

### Setup

```typescript
// src/i18n/index.ts
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import { getLocales } from 'react-native-localize';
import en from './locales/en.json';
import ar from './locales/ar.json';

const deviceLocale = getLocales()[0]?.languageCode ?? 'en';

i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, ar: { translation: ar } },
  lng: deviceLocale,
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
});

export default i18n;
```

### Locale File Structure

```
src/i18n/
├── index.ts           # i18n initialization
├── locales/
│   ├── en.json        # English translations
│   ├── ar.json        # Arabic translations
│   └── ...
└── types.ts           # Type-safe translation keys
```

### Translation Key Format

```json
{
  "common": {
    "save": "Save",
    "cancel": "Cancel",
    "delete": "Delete",
    "loading": "Loading...",
    "error": "Something went wrong"
  },
  "auth": {
    "login": "Log in",
    "logout": "Log out",
    "forgotPassword": "Forgot password?"
  },
  "orders": {
    "title": "Orders",
    "empty": "No orders yet",
    "count_one": "{{count}} order",
    "count_other": "{{count}} orders"
  }
}
```

### Usage in Components

```tsx
import { useTranslation } from 'react-i18next';

function OrderList() {
  const { t } = useTranslation();

  return (
    <View>
      <Text>{t('orders.title')}</Text>
      <Text>{t('orders.count', { count: orders.length })}</Text>
    </View>
  );
}
```

### Type-Safe Translation Keys

```typescript
// src/i18n/types.ts
import en from './locales/en.json';

type NestedKeyOf<T, K extends string = ''> = T extends object
  ? { [P in keyof T]: NestedKeyOf<T[P], K extends '' ? `${P & string}` : `${K}.${P & string}`> }[keyof T]
  : K;

export type TranslationKey = NestedKeyOf<typeof en>;
```

### RTL (Right-to-Left) Support

```typescript
// src/i18n/rtl.ts
import { I18nManager } from 'react-native';
import RNRestart from 'react-native-restart';

export function setRTL(isRTL: boolean): void {
  if (I18nManager.isRTL !== isRTL) {
    I18nManager.forceRTL(isRTL);
    RNRestart.restart();
  }
}

// RTL-aware styles
import { StyleSheet, I18nManager } from 'react-native';

const styles = StyleSheet.create({
  container: {
    flexDirection: I18nManager.isRTL ? 'row-reverse' : 'row',
  },
  text: {
    textAlign: I18nManager.isRTL ? 'right' : 'left',
    writingDirection: I18nManager.isRTL ? 'rtl' : 'ltr',
  },
});
```

### RTL Component Patterns

- Use `start`/`end` instead of `left`/`right` for margins and padding.
- Flip icons (arrows, chevrons) for RTL locales.
- Test navigation drawer direction in RTL mode.
- Use `I18nManager.isRTL` for conditional layout logic.

## Locale Management Workflow

### Adding a New Locale

1. **Rails**: Create locale directory under `config/locales/{code}/`, copy English files, translate.
2. **React Native**: Create `src/i18n/locales/{code}.json`, copy English file, translate.
3. **Add to available locales**: Update `config.i18n.available_locales` (Rails) and `i18n.init` resources (React Native).
4. **Pluralization rules**: Add CLDR pluralization rules for the locale if non-standard.
5. **RTL check**: If the locale is RTL (Arabic, Hebrew, Persian, Urdu), enable RTL layout handling.
6. **Test**: Verify all screens render correctly in the new locale, especially date/number formats.

### Translation Key Rules

- **Never hardcode user-facing strings** — always use translation keys.
- **Prefer flat keys** within logical namespaces: `orders.empty` not `pages.orders.list.emptyState.message`.
- **Use interpolation** for dynamic values: `"welcome": "Hello, {{name}}"` — never concatenate.
- **Separate singular/plural** using i18next pluralization: `_one`, `_other` suffixes.
- **Context variants**: Use `_male`, `_female` suffixes for gendered languages.
- **Keep keys stable**: Changing a key requires updating all locale files. Deprecate, don't rename.

### Missing Translation Handling

- **Development**: Show key path as fallback (makes missing translations visible).
- **Production**: Fall back to default locale (English). Never show raw keys to users.
- **CI check**: Run a script that validates all locale files have the same keys as the default locale.

## Web SPA i18n (Vite + react-i18next)

### Setup

Use `react-i18next` with browser language detection (no `react-native-localize`):

```typescript
// web/src/i18n/index.ts
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import en from './locales/en.json';
import ar from './locales/ar.json';

i18n.use(LanguageDetector).use(initReactI18next).init({
  resources: { en: { translation: en }, ar: { translation: ar } },
  fallbackLng: 'en',
  detection: { order: ['navigator', 'htmlTag', 'localStorage'] },
  interpolation: { escapeValue: false },
});

export default i18n;
```

### Locale Detection
- Detect via `navigator.language` (browser API).
- Fallback order: browser language → localStorage → HTML lang attribute → `en`.
- Same JSON locale file format as React Native.

### Web RTL Support
- Use CSS logical properties: `margin-inline-start` instead of `margin-left`.
- Tailwind CSS `rtl:` variant for directional overrides:
  ```html
  <div class="ml-4 rtl:ml-0 rtl:mr-4">Content</div>
  ```
- Set `dir="rtl"` on `<html>` element based on current locale.
- No `I18nManager` on web — CSS handles directionality.

## Next.js i18n

### Server Component i18n

Server Components cannot use React hooks. Use a server-side translation function:

```typescript
// next/src/i18n/server.ts
import { headers } from 'next/headers';

export async function getTranslations() {
  const headersList = await headers();
  const locale = headersList.get('x-locale') ?? 'en';
  const messages = await import(`./locales/${locale}.json`);
  return (key: string) => messages[key] ?? key;
}
```

### Client Component i18n
- Use `useTranslation` from `react-i18next` in `'use client'` components.
- Same patterns as Vite SPA for client-side translations.

### Middleware Locale Detection
- Detect locale in `middleware.ts` from `Accept-Language` header.
- Set locale in response header (`x-locale`) for Server Components to read.
