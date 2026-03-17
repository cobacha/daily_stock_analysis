# Theme Toggle Design

## Goal

Add a light/dark theme toggle to the Settings page header. Light theme uses clean tech aesthetic (white bg, blue accent). Persists to `localStorage` as `dsa-theme`.

## Architecture

**CSS variable override** — `ThemeProvider` sets/removes `data-theme="light"` on `<html>`. `:root` defines dark defaults; `[data-theme="light"]` overrides. No per-component changes needed beyond fixing hardcoded colors.

Default (no attribute) = dark. Only light needs an explicit `data-theme` attribute.

## Files

| File | Change |
|------|--------|
| `src/index.css` | Add `[data-theme="light"] { ... }` block |
| `src/index.html` | Add inline script in `<head>` to read localStorage before React mounts (FOUC prevention) |
| `src/contexts/ThemeContext.tsx` | New: `ThemeProvider` + `useTheme` hook |
| `src/App.tsx` | Wrap with `<ThemeProvider>` |
| `src/pages/SettingsPage.tsx` | Add toggle in page `<header>` area (always visible, not in dynamic fields) |

## ThemeContext

```tsx
type Theme = 'dark' | 'light';
// createContext(null) — useTheme throws if used outside ThemeProvider
export const ThemeProvider: React.FC<{ children: ReactNode }>;
export const useTheme: () => { theme: Theme; toggle: () => void };
```

`ThemeProvider` owns all DOM writes via a single `useEffect([theme])`:
```ts
useEffect(() => {
  if (theme === 'light') {
    document.documentElement.dataset.theme = 'light';
  } else {
    delete document.documentElement.dataset.theme;
  }
  localStorage.setItem('dsa-theme', theme);
}, [theme]);
```

Init state: `(localStorage.getItem('dsa-theme') as Theme) ?? 'dark'`

## FOUC Prevention (index.html)

Add before `</head>`:
```html
<script>
  (function(){var t=localStorage.getItem('dsa-theme');if(t==='light')document.documentElement.dataset.theme='light';})();
</script>
```

## Light Theme — CSS Variable Overrides

### Custom properties (`[data-theme="light"]`)

| Variable | Light value |
|----------|-------------|
| `--bg-base` | `#f0f4fa` |
| `--bg-card` | `#ffffff` |
| `--bg-elevated` | `#f8fafc` |
| `--bg-hover` | `#f1f5f9` |
| `--text-primary` | `#0f172a` |
| `--text-secondary-text` | `#475569` |
| `--text-muted-text` | `#94a3b8` |
| `--color-cyan` | `#2563eb` |
| `--color-cyan-dim` | `#1d4ed8` |
| `--color-cyan-glow` | `rgba(37,99,235,0.2)` |
| `--border-default` | `rgba(0,0,0,0.08)` |
| `--border-dim` | `rgba(0,0,0,0.05)` |
| `--border-accent` | `rgba(37,99,235,0.3)` |
| `--border-purple` | `rgba(111,97,241,0.2)` |
| `--border-cyan` | `#2563eb` |

### Tailwind HSL tokens (`[data-theme="light"]`)

| Variable | Light value |
|----------|-------------|
| `--background` | `214 32% 96%` |
| `--foreground` | `222 47% 11%` |
| `--card` | `0 0% 100%` |
| `--card-foreground` | `222 47% 11%` |
| `--popover` | `0 0% 100%` |
| `--popover-foreground` | `222 47% 11%` |
| `--primary` | `221 83% 53%` |
| `--primary-foreground` | `0 0% 100%` |
| `--secondary` | `210 40% 96%` |
| `--secondary-foreground` | `222 47% 11%` |
| `--muted` | `210 40% 96%` |
| `--muted-foreground` | `215 16% 47%` |
| `--accent` | `210 40% 94%` |
| `--accent-foreground` | `222 47% 11%` |
| `--border` | `214 32% 91%` |
| `--input` | `214 32% 91%` |
| `--ring` | `221 83% 53%` |
| `--elevated` | `210 40% 98%` |
| `--hover` | `214 32% 93%` |
| `--secondary-text` | `215 25% 40%` |
| `--muted-text` | `215 16% 60%` |

### Global CSS classes to override in `[data-theme="light"]`

These classes in `index.css` use hardcoded dark colors and need explicit light overrides:

```css
[data-theme="light"] .dock-surface {
  background: rgba(255,255,255,0.85);
  border-color: rgba(0,0,0,0.08);
  box-shadow: 0 12px 40px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.9);
}
[data-theme="light"] .dock-logo {
  color: #ffffff;
  background: linear-gradient(135deg, rgba(37,99,235,0.8) 0%, #2563eb 100%);
}
[data-theme="light"] .dock-item {
  background: rgba(0,0,0,0.03);
  border-color: rgba(0,0,0,0.07);
  color: #64748b;
}
[data-theme="light"] .dock-item:hover {
  background: rgba(37,99,235,0.08);
  border-color: rgba(37,99,235,0.2);
  color: #1e40af;
}
[data-theme="light"] .dock-item.is-active {
  background: linear-gradient(135deg, rgba(37,99,235,0.15), rgba(111,97,241,0.1));
  border-color: rgba(37,99,235,0.25);
  color: #1e3a8a;
}
[data-theme="light"] .btn-primary {
  color: #ffffff;
}
[data-theme="light"] .btn-secondary {
  background: rgba(0,0,0,0.03);
  border-color: rgba(0,0,0,0.09);
  color: #475569;
}
[data-theme="light"] .btn-secondary:hover {
  background: rgba(37,99,235,0.06);
  border-color: rgba(37,99,235,0.3);
  color: #1e40af;
}
[data-theme="light"] .input-terminal {
  background: #f8fafc;
  border-color: rgba(0,0,0,0.1);
  color: #0f172a;
}
[data-theme="light"] ::-webkit-scrollbar-thumb {
  background: rgba(0,0,0,0.12);
}
[data-theme="light"] .title-gradient {
  background: linear-gradient(90deg, #0f172a 0%, #475569 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
```

Note: `.bg-hover` utility uses `var(--bg-hover)` and automatically responds to the variable override — no extra rule needed.

## Hardcoded Tailwind Values to Fix in .tsx Files

Scan pattern: `bg-\[#` in `src/**/*.tsx`. Cases to migrate:
- `bg-[#08080c]`, `bg-[#0d0d14]`, `bg-[#12121a]`, `bg-[#1a1f2e]` → replace with `bg-base`, `bg-card`, `bg-elevated` utility classes (already defined in CSS)

Known instance: `src/components/report/ReportPriceHistory.tsx:126` uses `bg-[#1a1f2e] border border-white/10` (chart tooltip) — migrate `bg-[#1a1f2e]` to `bg-elevated`, and replace `border-white/10` with `border-black/8` under `[data-theme="light"]` or use a CSS variable.

Stock color backgrounds (`bg-[#ff4d4d]/10`, `bg-[#00d46a]/10`) stay unchanged — these are financial convention colors that remain consistent across themes.

## Settings Page Toggle Placement

In the `<header>` block (always rendered, not inside dynamic field categories). Right side, next to the page title:

```
┌─────────────────────────────────────────────┐
│  系统设置            ☾ ──●── ☀              │
└─────────────────────────────────────────────┘
```

Pill toggle: moon icon + sliding knob + sun icon. Active side highlighted in accent color.
