# Locale Management Workflow

Load-bearing rules restated (hold even if you read nothing else):

1. **A key added to one locale must be added to all** — CI is what enforces that, not care.
2. **Never delete a key that ships in a released client.** Old app versions still request it.

---

### Adding a New Locale

1. **Rails**: Create locale directory under `backend/config/locales/{code}/`, copy English files, translate.
2. **React Native**: Create `mobile/src/i18n/locales/{code}.json`, copy English file, translate.
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
