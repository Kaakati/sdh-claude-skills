# Forms and Feedback — Field, notify(), Confirmation, Loading and Empty

Load-bearing rules restated (hold even if you read nothing else):

1. **Every form is `Field` parts + react-hook-form + zod.** Never `add form` — the legacy wrapper has
   no docs page, and its base-nova item has no files.
2. **One schema module**, imported by the form and by the server. Its messages are translation keys.
3. **Invalid state is wired on both elements:** `data-invalid` on `Field`, `aria-invalid` on the
   control, and `aria-describedby` from the control to its `FieldError` (`role="alert"`).
4. **Next.js:** the server action `safeParse`s the same schema and returns field errors plus the
   submitted values; the form reads them with `useActionState`. **Vite:** a TanStack Query mutation;
   `VALIDATION_ERROR` details land on their fields with `setError`, and every other failure on
   `root`, carrying `requestId` and rendered as a `FieldError`.
5. **Toasts go through `notify()` with translation keys**, implemented per base. A toast never
   carries field validation and is never the only place a blocking error appears.
6. **Irreversible actions confirm in an `AlertDialog`** that names the action and the object, and
   closes on success — not on click.

The form rules themselves (schema first, `z.infer`, no raw axios, disabled while submitting) belong
to `std-reactjs` → @skills/std-reactjs/references/forms.md; server action rules belong to
`std-nextjs` → @skills/std-nextjs/references/server-actions.md. This file is where those rules meet
shadcn's parts.

---

## The Field family

| Part | Renders | Use |
|---|---|---|
| `FieldSet`, `FieldLegend` (`variant` `legend` or `label`) | `<fieldset>` and its legend | Related controls — a radio set, an address block; the legend is announced with each control |
| `FieldGroup` | A stack of fields | The form body |
| `Field` (`orientation` `vertical`, `horizontal`, `responsive`) | `role="group"` | One control with its label, description and error |
| `FieldLabel`, `FieldTitle` | A label, or a title for a control that cannot be labelled | `htmlFor` equals the control's `id` |
| `FieldDescription`, `FieldContent`, `FieldSeparator` | Hint text, a content column, a divider | |
| `FieldError` | `role="alert"`; dedupes an `errors` array, or renders its children | The translated message |

shadcn's guides wire `data-invalid` and `aria-invalid` but no `aria-describedby`. `role="alert"`
announces an error once, when it appears; `aria-describedby` is what reads it again when focus
returns to the field. The `std-accessibility` skill requires both.

## The shared schema

```ts
// src/domain/members/invite-schema.ts — imported by the form and by the server action
import { z } from 'zod';

export const inviteMemberSchema = z.object({
  email: z.string().trim().email('members.invite.errors.email'),
  message: z.string().trim().max(280, 'members.invite.errors.messageTooLong').optional(),
});

export type InviteMemberInput = z.infer<typeof inviteMemberSchema>;
```

- **Messages are keys.** The client translates them; they never reach a user untranslated.
- **Pin zod and `@hookform/resolvers` together.** shadcn's form guides still show zod v3 while npm's
  latest zod is 4.x with resolvers 5.x — confirm the resolver supports the zod major before pinning.

## One field, wired once

```ts
// src/lib/form-errors.ts
import type { TFunction } from 'i18next';
import type { FieldError as RhfFieldError } from 'react-hook-form';

// Client-side zod messages are translation keys; server messages arrive localized (type 'server').
export function errorText(t: TFunction, error?: RhfFieldError): string | undefined {
  if (!error?.message) return undefined;
  return error.type === 'server' ? error.message : t(error.message);
}
```

```tsx
// src/components/molecules/TextField/TextField.tsx
'use client';

import { Controller, type Control, type FieldPath, type FieldValues } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { Field, FieldDescription, FieldError, FieldLabel } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { errorText } from '@/lib/form-errors';

interface TextFieldProps<T extends FieldValues> {
  control: Control<T>;
  name: FieldPath<T>;
  label: string;        // translated by the caller
  description?: string; // translated by the caller
  autoComplete?: string;
}

export function TextField<T extends FieldValues>({ control, name, label, description, autoComplete }: TextFieldProps<T>) {
  const { t } = useTranslation();
  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState }) => (
        <Field data-invalid={fieldState.invalid}>
          <FieldLabel htmlFor={field.name}>{label}</FieldLabel>
          <Input
            {...field}
            id={field.name}
            autoComplete={autoComplete}
            aria-invalid={fieldState.invalid}
            aria-describedby={fieldState.invalid ? `${field.name}-error` : undefined}
          />
          {description && <FieldDescription>{description}</FieldDescription>}
          {fieldState.invalid && <FieldError id={`${field.name}-error`}>{errorText(t, fieldState.error)}</FieldError>}
        </Field>
      )}
    />
  );
}
```

Rails localizes validation messages from `Accept-Language` (the `std-i18n` skill), so a server
message is shown as sent. Running it through `t()` would look the sentence up as a key and log it
missing.

---

## Next.js — the server action re-checks the schema

```ts
// src/actions/members.ts
'use server';

import { revalidatePath } from 'next/cache';
import { railsServer } from '@/api/rails-server';
import { requireSession } from '@/lib/auth';
import { inviteMemberSchema, type InviteMemberInput } from '@/domain/members/invite-schema';
import type { ActionResult } from './result';

// std-nextjs's ActionResult, plus the submitted values: React resets the form after an action.
export type InviteState = ActionResult<{ id: string }> & { values?: Partial<InviteMemberInput> };

export async function inviteMember(_prev: InviteState | null, formData: FormData): Promise<InviteState> {
  const session = await requireSession();
  const values = { email: String(formData.get('email') ?? ''), message: String(formData.get('message') ?? '') };
  const parsed = inviteMemberSchema.safeParse(values);
  if (!parsed.success) {
    const { formErrors, fieldErrors } = parsed.error.flatten();
    return { ok: false, formErrors, fieldErrors, values };
  }
  try {
    const response = await railsServer.post<{ data: { id: string } }>('/api/v1/invitations', parsed.data, {
      headers: { Authorization: `Bearer ${session.token}` },
    });
    revalidatePath('/members');
    return { ok: true, data: response.data.data };
  } catch (error) {
    console.error('inviteMember failed', { userId: session.userId, error });
    return { ok: false, formErrors: ['members.invite.errors.failed'], values };
  }
}
```

```tsx
// src/components/organisms/InviteMemberForm/InviteMemberForm.tsx — Next.js
'use client';

import { useActionState } from 'react';
import { useTranslations } from 'next-intl';
import { inviteMember, type InviteState } from '@/actions/members';
import { Button } from '@/components/ui/button';
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field';
import { Input } from '@/components/ui/input';

export function InviteMemberForm() {
  const t = useTranslations();
  const [state, formAction, pending] = useActionState<InviteState | null, FormData>(inviteMember, null);
  const failed = state?.ok === false ? state : undefined;
  const emailError = failed?.fieldErrors?.email?.[0];

  return (
    <form action={formAction} noValidate>
      <FieldGroup>
        <Field data-invalid={!!emailError}>
          <FieldLabel htmlFor="invite-email">{t('members.invite.email')}</FieldLabel>
          <Input id="invite-email" name="email" type="email" autoComplete="email"
            defaultValue={failed?.values?.email} aria-invalid={!!emailError}
            aria-describedby={emailError ? 'invite-email-error' : undefined} />
          {emailError && <FieldError id="invite-email-error">{t(emailError)}</FieldError>}
        </Field>
      </FieldGroup>
      {failed?.formErrors?.[0] && <p role="alert" className="text-sm text-error">{t(failed.formErrors[0])}</p>}
      <Button type="submit" disabled={pending}>{t('members.invite.submit')}</Button>
    </form>
  );
}
```

- **`defaultValue={failed?.values?.email}` is what keeps the input.** React resets an action form
  after it submits; shadcn's Next.js guide returns the values for exactly this reason.
- **Need live per-field validation as well?** Keep the action and put react-hook-form in front of
  it: `handleSubmit` validates with `zodResolver(inviteMemberSchema)`, then
  `startTransition(() => formAction(new FormData(formElement)))`. The same schema now runs on both
  sides.
- **A Rails `VALIDATION_ERROR` caught in the action carries localized messages.** Return them in a
  map of their own — never merged into `fieldErrors`, whose entries are keys.

---

## Vite SPA — a mutation, server errors on the fields

```tsx
// src/components/organisms/InviteMemberForm/InviteMemberForm.tsx — Vite SPA
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useTranslation } from 'react-i18next';
import { ApiError } from '@/api/client';
import { useInviteMember } from '@/api/members';
import { TextField } from '@/components/molecules/TextField';
import { Button } from '@/components/ui/button';
import { FieldError, FieldGroup } from '@/components/ui/field';
import { inviteMemberSchema, type InviteMemberInput } from '@/domain/members/invite-schema';
import { useNotify } from '@/lib/notify';

function useInviteMemberForm() {
  const { t } = useTranslation();
  const notify = useNotify();
  const invite = useInviteMember(); // a useMutation hook in src/api/members.ts
  const form = useForm<InviteMemberInput>({
    resolver: zodResolver(inviteMemberSchema),
    defaultValues: { email: '', message: '' },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await invite.mutateAsync(values);
      notify.success('members.invite.sent');
      form.reset();
    } catch (error) {
      if (error instanceof ApiError && error.code === 'VALIDATION_ERROR') {
        for (const [field, message] of Object.entries(error.fieldErrors())) {
          form.setError(field as keyof InviteMemberInput, { type: 'server', message });
        }
        return;
      }
      const requestId = error instanceof ApiError ? error.requestId : undefined;
      form.setError('root', { type: 'server', message: t('common.errors.requestFailed', { requestId }) });
      notify.error('common.errors.requestFailed'); // optional: on top of the root error, never instead
    }
  });
  return { form, onSubmit };
}

export function InviteMemberForm() {
  const { t } = useTranslation();
  const { form, onSubmit } = useInviteMemberForm();
  const rootError = form.formState.errors.root;
  return (
    <form onSubmit={onSubmit} noValidate>
      <FieldGroup>
        <TextField control={form.control} name="email" label={t('members.invite.email')} autoComplete="email" />
        <TextField control={form.control} name="message" label={t('members.invite.message')} />
        {rootError && <FieldError>{rootError.message}</FieldError>}
      </FieldGroup>
      <Button type="submit" disabled={form.formState.isSubmitting}>{t('members.invite.submit')}</Button>
    </form>
  );
}
```

`ApiError`, its `fieldErrors()` and `requestId` come from the house axios interceptor →
@skills/std-api-design/references/errors-typescript.md. The root `FieldError` is where a failure
that belongs to no field is guaranteed to appear; a toast is optional on top
(@skills/std-reactjs/references/forms.md). A 403 is not handled here: the same
interceptor invalidates `['me']`, because the UI offered something the server refused
(@skills/access-control-designer/references/ui-gates.md).

---

## Toasts — one `notify()`, two bases

- **Mount one `<Toaster />` at the root** — Next.js in the client providers the root layout renders,
  Vite in `App.tsx`'s providers — with its own strings filled from `t()`
  (@skills/std-shadcn-ui/references/accessibility-and-i18n.md).
- **Success and info are polite and dismiss themselves. An error the user must act on persists**,
  has a close control, and also appears where it happened — inline, or inside the dialog that failed.
- **Never field validation.** That is `FieldError`, next to the field.
- **Call sites never know the base:** both implementations export the same `useNotify()` →
  `{ success(key, vars), error(key, vars) }`. The toast call follows the base; the translation hook
  follows the platform.

| | Base UI `toast` | Radix `sonner` |
|---|---|---|
| Announcement | `priority: 'low'` is announced politely, `'high'` urgently | One polite live region — no urgent channel |
| Auto-dismiss | `timeout`, default 5000 ms; `0` never dismisses | `duration`; `Infinity` never dismisses |
| Keyboard | F6 moves focus into the toast viewport landmark | Alt+T moves focus to the toasts |
| Theme | Tokens and the `.dark` class, like any primitive | The vendored `sonner.tsx` reads `useTheme()` from `next-themes`; in Vite, point it at the house theme provider |

```ts
// src/lib/notify.ts — Next.js package on Base UI (style base-*)
'use client';

import { useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { toast } from '@/components/ui/toast';

type Vars = Record<string, string | number>;

export function useNotify() {
  const t = useTranslations();
  return useMemo(() => ({
    success: (key: string, vars?: Vars) => toast.add({ type: 'success', title: t(key, vars), priority: 'low' }),
    error: (key: string, vars?: Vars) => toast.add({ type: 'error', title: t(key, vars), priority: 'high', timeout: 0 }),
  }), [t]);
}
```

```ts
// src/lib/notify.ts — Vite SPA package on Radix (style radix-*, new-york)
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';

type Vars = Record<string, string | number>;

export function useNotify() {
  const { t } = useTranslation();
  return useMemo(() => ({
    success: (key: string, vars?: Vars) => toast.success(t(key, vars)),
    error: (key: string, vars?: Vars) => toast.error(t(key, vars), { duration: Infinity, closeButton: true }),
  }), [t]);
}
```

The other two pairings swap only the platform lines:

| Platform | Directive | Translation hook |
|---|---|---|
| Next.js (next-intl) | `'use client'` first | `import { useTranslations } from 'next-intl'` → `const t = useTranslations()` |
| Vite SPA (react-i18next) | None — `rsc: false` | `import { useTranslation } from 'react-i18next'` → `const { t } = useTranslation()` |

A Next.js package already on react-i18next keeps that hook, with the directive.

`sonner` has no urgent channel, which is why a blocking failure never lives only in a toast — the
rule above is an accessibility requirement, not a style preference. Politeness levels and live
regions in general → @skills/accessibility-auditor/references/aria-patterns.md.

---

## Confirming a destructive action

```tsx
// src/components/organisms/DeleteProjectDialog/DeleteProjectDialog.tsx — Vite SPA, Base UI package
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useDeleteProject } from '@/api/projects';
import { useAppAbility } from '@/components/providers/AbilityProvider';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { allows } from '@/lib/ability';
import type { Project } from '@/types/project';

export function DeleteProjectDialog({ project }: { project: Project }) {
  const { t } = useTranslation();
  const ability = useAppAbility(); // @casl/react 7 (ui-gates.md); throws outside the AbilityProvider
  const [open, setOpen] = useState(false);
  const remove = useDeleteProject();
  if (!allows(ability, 'projects.delete', project)) return null; // not permitted → not rendered

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogTrigger render={<Button variant="destructive" />}>{t('projects.delete.trigger')}</AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t('projects.delete.title', { name: project.name })}</AlertDialogTitle>
          <AlertDialogDescription>{t('projects.delete.consequence')}</AlertDialogDescription>
        </AlertDialogHeader>
        {remove.isError && <p role="alert" className="text-sm text-error">{t('projects.delete.failed')}</p>}
        <AlertDialogFooter>
          <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
          <AlertDialogAction variant="destructive" disabled={remove.isPending}
            onClick={() => remove.mutate(project.id, { onSuccess: () => setOpen(false) })}>
            {t('projects.delete.confirm')}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

- **Radix:** the trigger is `<AlertDialogTrigger asChild><Button variant="destructive">…</Button></AlertDialogTrigger>`,
  and because Radix's `AlertDialogAction` closes the dialog on click, the confirm control is a plain
  `<Button variant="destructive">` in the footer — the dialog stays open until the mutation settles.
  **Next.js:** call the server action inside `useTransition` and close when it returns `ok`.
- **`AlertDialog`, not `Dialog`,** for anything irreversible.
- **The title names the action and the object; the confirm button repeats the verb** ("Delete
  project"), never "OK" or "Yes".
- **A failure renders inside the open dialog** (`role="alert"`), not as a toast behind a closed one.
- **Confirmation strength follows the persona card's cost-of-a-mistake row**
  (@skills/ui-ux-patterns/references/role-based-ux.md): a high-cost delete makes the user type the
  object's name.
- **Focus:** assert in the component test that focus lands on Cancel when the dialog opens — neither
  base's docs state the default for alert dialogs. After a successful delete the trigger's row is
  gone, so set the dialog's final-focus target to a stable element (the list heading, the next row).
- **Blocked by record state, not by permission:** the trigger stays rendered, focusable, and
  described by a visible reason (`std-accessibility`).

---

## Loading and empty states

- **Loading:** a `Skeleton` shaped like the content — Next.js `loading.tsx`, Vite `isPending` — with
  `aria-busy="true"` on the region while it loads. `Spinner` for inline progress, its label prop
  filled from `t()`. `animate-pulse` is covered by the reduced-motion backstop.
- **Submitting:** the submit button is `disabled` while pending and keeps a text label — never a
  spinner on its own.
- **Empty:** `Empty` with `EmptyHeader`, `EmptyMedia`, `EmptyTitle`, `EmptyDescription` and
  `EmptyContent`. Denied, empty, and filtered-to-nothing are three different screens
  (@skills/ui-ux-patterns/references/role-based-ux.md), and the create call-to-action renders only
  when the role holds the `.create` key.

```tsx
<Empty>
  <EmptyHeader>
    <EmptyMedia variant="icon"><FolderIcon aria-hidden="true" /></EmptyMedia>
    <EmptyTitle>{t('projects.empty.title')}</EmptyTitle>
    <EmptyDescription>{t('projects.empty.description')}</EmptyDescription>
  </EmptyHeader>
  {allows(ability, 'projects.create') && (
    <EmptyContent>
      <Link href="/projects/new" className={buttonVariants()}>{t('projects.new')}</Link>
    </EmptyContent>
  )}
</Empty>
```

Empty-state copy and layout patterns → @skills/ui-ux-patterns/references/screen-patterns.md.
