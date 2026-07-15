# React Native i18n

Load-bearing rules restated (hold even if you read nothing else):

1. **RTL is a layout change, not a text change.** `I18nManager.forceRTL` requires a
   **restart** — it is not a runtime toggle.
2. **Use logical properties** (`start`/`end`), never `left`/`right`, or RTL silently breaks.
3. **Type the keys.** An untyped `t('typo.key')` ships a blank label, not an error.

---

### Libraries

Use `i18next` + `react-i18next` + `react-native-localize` for device locale detection:

```bash
npm install i18next react-i18next react-native-localize
```

### Setup

```typescript
// mobile/src/i18n/index.ts
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
mobile/src/i18n/
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
// mobile/src/i18n/types.ts
import en from './locales/en.json';

type NestedKeyOf<T, K extends string = ''> = T extends object
  ? { [P in keyof T]: NestedKeyOf<T[P], K extends '' ? `${P & string}` : `${K}.${P & string}`> }[keyof T]
  : K;

export type TranslationKey = NestedKeyOf<typeof en>;
```

### RTL (Right-to-Left) Support

```typescript
// mobile/src/i18n/rtl.ts
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
