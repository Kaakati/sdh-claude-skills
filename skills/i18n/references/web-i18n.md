# Web i18n — Vite SPA and Next.js

Load-bearing rules restated (hold even if you read nothing else):

1. **Server Components and Client Components need different i18n paths** — a Client
   Component cannot read the server's locale without being handed it.
2. **CSS logical properties** (`margin-inline-start`) are what make RTL free on the web.
3. **The locale belongs in the URL**, not only in a cookie — a shared link must keep it.

---

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

