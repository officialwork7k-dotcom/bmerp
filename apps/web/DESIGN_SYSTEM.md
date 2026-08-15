# MetaForge Design System

## System Info

| Field | Value |
|-------|-------|
| **Name** | MetaForge UI Theme System |
| **Version** | 1.1.0 |
| **Owner** | apps/web |
| **Status** | Active |
| **Last Updated** | 2026-08-14 |

Generated with help from the `ui-design-system` skill (installed at `.claude/skills/ui-design-system/`) — this doc is that skill's Workflow 4 (Developer Handoff) deliverable, filled in with MetaForge's actual system rather than the template's placeholders.

---

## Design Principles

1. **One flat radius, everywhere** — Odoo's own `--border-radius: 0.25rem` (4px) is used for both `rounded-md` and `rounded-lg` sitewide; there is no larger-radius "card" tier. Consistency over per-component variety.
2. **Neutral ramp is fixed, only the accent rotates** — all 5 themes share the exact same neutral gray scale, semantic colors (success/warning/danger/info), radius, and font. Only `--theme-primary-*` changes per theme.
3. **The user's explicit choice wins over the OS** — `dark:` is redefined to key off `[data-theme="dark"]`, not `prefers-color-scheme`. Picking Yellow/Blue/Orange/BM stays light regardless of OS dark-mode setting.
4. **Accessible by default** — every theme's primary-600 (the actual `bg-primary-600 text-white` filled-button color, used in 19+ components) must clear WCAG AA's 4.5:1 contrast ratio for white text. See Accessibility Audit below — this was not true until this pass.

---

## Color Palette

### Themes (`--theme-primary-*`, defined in `apps/web/src/app.css`)

Switchable at runtime via `<html data-theme="...">` (see `$lib/theme.svelte.ts`). Each theme is an 11-step ramp (`50`→`950`); only `600` (filled-button background) and `700` (hover) are listed below — see `app.css` for the full ramp.

| Theme | 600 (button bg) | 700 (hover) | Basis |
|-------|------|------|-------|
| **BM** (default) | `#714b67` | `#624159` | Extracted from Odoo's real computed CSS custom properties (`--o-cc*-btn-primary`), not guessed |
| **Yellow** | `#b06105` | `#b45309` | Darkened from the original `#d97706` — see audit below |
| **Blue** | `#2563eb` | `#1d4ed8` | Clean corporate blue |
| **Orange** | `#b75a3c` | `#9e4a31` | Darkened from the original `#c05f3f` — see audit below |
| **Dark** | `#4f46e5` | `#4338ca` | Cool indigo, chosen to read against dark surfaces where warmer accents wash out |

### Neutral Colors (constant across all themes)

| Name | Hex | Usage |
|------|-----|-------|
| neutral-50 | `#f9fafb` | Page background |
| neutral-100 | `#f3f4f6` | Hover backgrounds |
| neutral-200 | `#d8dadd` | Borders — the app's most common border class |
| neutral-700–900 | `#374151`–`#111827` | Text |

### Semantic Colors (Odoo's own values, constant across all themes)

| Name | Hex |
|------|-----|
| Success | `#28a745` |
| Warning | `#e99d00` |
| Danger | `#d44c59` |
| Info | `#17a2b8` |

---

## Accessibility Audit (2026-08-14)

Ran a real luminance-based WCAG contrast check (not eyeballed) against every theme's `primary-600`/`primary-700` vs. white — the actual filled-button color combination used across the app.

| Theme | 600 vs white | AA (4.5:1) | 700 vs white | AA (4.5:1) |
|-------|--------------|------------|---------------|------------|
| BM | 7.23 | ✅ | 8.68 | ✅ |
| Yellow (before fix) | 3.19 | ❌ | 5.02 | ✅ |
| Yellow (after fix) | 4.61 | ✅ | 5.02 | ✅ |
| Blue | 5.17 | ✅ | 6.70 | ✅ |
| Orange (before fix) | 4.24 | ❌ | 6.04 | ✅ |
| Orange (after fix) | 4.62 | ✅ | 6.04 | ✅ |
| Dark | 6.29 | ✅ | 7.90 | ✅ |

**Fix applied:** Yellow's and Orange's `primary-600` were darkened in place (same hue/saturation, binary-searched brightness) until they cleared 4.5:1 — a minimal, surgical change rather than jumping to the much-darker `700` shade. Every `bg-primary-600 text-white` button across the app (19 components) now meets WCAG AA for both themes.

---

## Component Conventions

- **Filled button:** `bg-primary-600 text-white hover:bg-primary-700`
- **Border/divider:** `border-neutral-200` (light) / `border-neutral-800` (dark theme)
- **Radius:** `rounded-md` (buttons, inputs, badges) or `rounded-lg` (cards, panels, dialogs) — both resolve to the same 4px
- **Shadows/z-index/transition durations:** no custom token layer — plain Tailwind v4 utilities (`shadow-lg`, `z-50`, `duration-150`) are used directly and are sufficient; adding a parallel `--shadow-*`/`--z-*` custom-property scale on top of Tailwind's own would be redundant, not a real gap

---

## Adding a New Theme

1. Add a `[data-theme="yourtheme"] { --theme-primary-50: ...; ... --theme-primary-950: ...; }` block to `apps/web/src/app.css`, following the existing 5.
2. Register it in `THEMES` in `apps/web/src/lib/theme.svelte.ts` (id, label, swatch — swatch should match `--theme-primary-600` exactly).
3. **Before shipping:** check `primary-600` vs white contrast (WCAG AA needs ≥4.5:1) — this is exactly the bug this audit found and fixed for Yellow/Orange. A quick way to check: `(L1+0.05)/(L2+0.05)` using relative luminance, or reuse the calculation in this doc's audit section.
