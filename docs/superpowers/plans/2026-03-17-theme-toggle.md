# Theme Toggle Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dark/light theme toggle in the Settings page header; light theme uses white backgrounds and blue accents; preference persists in `localStorage`.

**Architecture:** CSS custom properties drive theming — `[data-theme="light"]` on `<html>` overrides `:root` variables; a `ThemeContext` manages state and DOM writes; an inline `<script>` in `index.html` prevents flash-of-unstyled-content on page load.

**Tech Stack:** React 18, TypeScript, Tailwind v4, CSS custom properties

---

## Chunk 1: ThemeContext + FOUC prevention + CSS variables

### Task 1: Create ThemeContext

**Files:**
- Create: `apps/dsa-web/src/contexts/ThemeContext.tsx`

- [ ] **Step 1: Create the file**

```tsx
// apps/dsa-web/src/contexts/ThemeContext.tsx
import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';

type Theme = 'dark' | 'light';

type ThemeContextValue = {
  theme: Theme;
  toggle: () => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem('dsa-theme') as Theme) ?? 'dark'
  );

  useEffect(() => {
    if (theme === 'light') {
      document.documentElement.dataset.theme = 'light';
    } else {
      delete document.documentElement.dataset.theme;
    }
    localStorage.setItem('dsa-theme', theme);
  }, [theme]);

  const toggle = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'));

  return (
    <ThemeContext.Provider value={{ theme, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd apps/dsa-web && npx tsc --noEmit 2>&1 | head -20
```
Expected: no errors.

---

### Task 2: Add FOUC-prevention script to index.html

**Files:**
- Modify: `apps/dsa-web/index.html`

Current content:
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>dsa-web</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 1: Add inline script before `</head>`**

Replace the `<head>` closing tag:
```html
    <script>
      (function(){var t=localStorage.getItem('dsa-theme');if(t==='light')document.documentElement.dataset.theme='light';})();
    </script>
  </head>
```

Full result:
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>dsa-web</title>
    <script>
      (function(){var t=localStorage.getItem('dsa-theme');if(t==='light')document.documentElement.dataset.theme='light';})();
    </script>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

---

### Task 3: Add light theme CSS variables to index.css

**Files:**
- Modify: `apps/dsa-web/src/index.css`

Append this entire block at the **end** of the file (after all existing rules):

- [ ] **Step 1: Append the light theme block**

```css
/* =========================================
   LIGHT THEME OVERRIDES
   ========================================= */

[data-theme="light"] {
  /* Custom bg/text/border tokens */
  --bg-base: #f0f4fa;
  --bg-card: #ffffff;
  --bg-elevated: #f8fafc;
  --bg-hover: #f1f5f9;
  --text-primary: #0f172a;
  --text-secondary-text: #475569;
  --text-muted-text: #94a3b8;

  /* Accent: cyan → blue */
  --color-cyan: #2563eb;
  --color-cyan-dim: #1d4ed8;
  --color-cyan-glow: rgba(37, 99, 235, 0.2);

  /* Borders */
  --border-default: rgba(0, 0, 0, 0.08);
  --border-dim: rgba(0, 0, 0, 0.05);
  --border-accent: rgba(37, 99, 235, 0.3);
  --border-purple: rgba(111, 97, 241, 0.2);
  --border-cyan: #2563eb;

  /* Tailwind HSL tokens */
  --background: 214 32% 96%;
  --foreground: 222 47% 11%;
  --card: 0 0% 100%;
  --card-foreground: 222 47% 11%;
  --popover: 0 0% 100%;
  --popover-foreground: 222 47% 11%;
  --primary: 221 83% 53%;
  --primary-foreground: 0 0% 100%;
  --secondary: 210 40% 96%;
  --secondary-foreground: 222 47% 11%;
  --muted: 210 40% 96%;
  --muted-foreground: 215 16% 47%;
  --accent: 210 40% 94%;
  --accent-foreground: 222 47% 11%;
  --destructive: 0 84% 60%;
  --destructive-foreground: 0 0% 100%;
  --border: 214 32% 91%;
  --input: 214 32% 91%;
  --ring: 221 83% 53%;
  --elevated: 210 40% 98%;
  --hover: 214 32% 93%;
  --secondary-text: 215 25% 40%;
  --muted-text: 215 16% 60%;
}

/* Dock navigation */
[data-theme="light"] .dock-surface {
  background: rgba(255, 255, 255, 0.85);
  border-color: rgba(0, 0, 0, 0.08);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

[data-theme="light"] .dock-surface::before {
  background: linear-gradient(
    180deg,
    rgba(0, 0, 0, 0.06) 0%,
    rgba(0, 0, 0, 0.02) 100%
  );
}

[data-theme="light"] .dock-logo {
  color: #ffffff;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.9) 0%, #2563eb 100%);
  box-shadow: 0 8px 16px rgba(37, 99, 235, 0.25);
}

[data-theme="light"] .dock-item {
  background: rgba(0, 0, 0, 0.03);
  border-color: rgba(0, 0, 0, 0.07);
  color: #64748b;
}

[data-theme="light"] .dock-item:hover {
  background: rgba(37, 99, 235, 0.08);
  border-color: rgba(37, 99, 235, 0.2);
  color: #1e40af;
}

[data-theme="light"] .dock-item.is-active {
  background: linear-gradient(
    135deg,
    rgba(37, 99, 235, 0.15),
    rgba(111, 97, 241, 0.1)
  );
  border-color: rgba(37, 99, 235, 0.25);
  color: #1e3a8a;
  box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.1),
    0 14px 32px rgba(37, 99, 235, 0.12);
}

/* Buttons */
[data-theme="light"] .btn-primary {
  color: #ffffff;
  border-color: rgba(37, 99, 235, 0.4);
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  box-shadow: 0 12px 28px rgba(37, 99, 235, 0.2);
}

[data-theme="light"] .btn-secondary {
  background: rgba(0, 0, 0, 0.03);
  border-color: rgba(0, 0, 0, 0.09);
  color: #475569;
}

[data-theme="light"] .btn-secondary:hover {
  background: rgba(37, 99, 235, 0.06);
  border-color: rgba(37, 99, 235, 0.3);
  color: #1e40af;
}

/* Input */
[data-theme="light"] .input-terminal {
  background: #f8fafc;
  border-color: rgba(0, 0, 0, 0.1);
  color: #0f172a;
}

[data-theme="light"] .input-terminal::placeholder {
  color: #94a3b8;
}

/* Title gradient (dark→light text) */
[data-theme="light"] .title-gradient {
  background: linear-gradient(90deg, #0f172a 0%, #475569 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* Scrollbar */
[data-theme="light"] ::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.12);
}

[data-theme="light"] ::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.2);
}

/* body background */
[data-theme="light"] body {
  background: var(--bg-base);
  color: var(--text-primary);
}
```

- [ ] **Step 2: Build and verify no CSS errors**

```bash
cd apps/dsa-web && npm run build 2>&1 | tail -10
```
Expected: `✓ built in X.XXs` with no errors.

- [ ] **Step 3: Commit**

```bash
cd apps/dsa-web && git add src/contexts/ThemeContext.tsx index.html src/index.css && git commit -m "feat: add ThemeContext and light theme CSS variables"
```

---

## Chunk 2: Wire ThemeProvider + Settings toggle + hardcoded fix

### Task 4: Wrap App with ThemeProvider

**Files:**
- Modify: `apps/dsa-web/src/App.tsx`

- [ ] **Step 1: Add import at top of App.tsx**

Find the existing imports block and add:
```tsx
import { ThemeProvider } from './contexts/ThemeContext';
```

- [ ] **Step 2: Wrap the return value**

The current `App.tsx` `App` component (lines 247-255) returns:
```tsx
return (
  <Router>
    <AuthProvider>
      <AppContent/>
    </AuthProvider>
  </Router>
);
```

Wrap with `ThemeProvider` as the outermost wrapper:
```tsx
return (
  <ThemeProvider>
    <Router>
      <AuthProvider>
        <AppContent/>
      </AuthProvider>
    </Router>
  </ThemeProvider>
);
```

- [ ] **Step 3: Verify TypeScript**

```bash
cd apps/dsa-web && npx tsc --noEmit 2>&1 | head -20
```
Expected: no errors.

---

### Task 5: Add theme toggle to SettingsPage header

**Files:**
- Modify: `apps/dsa-web/src/pages/SettingsPage.tsx`

- [ ] **Step 1: Add useTheme import**

At the top of `SettingsPage.tsx`, add to the hooks import:
```tsx
import { useTheme } from '../contexts/ThemeContext';
```

- [ ] **Step 2: Call the hook inside the component**

Add after the existing hook calls (around line 38, after `useSystemConfig()`):
```tsx
const { theme, toggle } = useTheme();
```

- [ ] **Step 3: Add toggle to the header**

The current header block (lines 107–139) contains:
```tsx
<header className="mb-4 rounded-2xl border border-white/8 bg-card/80 p-4 backdrop-blur-sm">
  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
    <div>
      <h1 className="text-xl font-semibold text-white">系统设置</h1>
      <p className="text-sm text-secondary">
        默认使用 .env 中的配置
      </p>
    </div>

    <div className="flex flex-wrap items-center gap-2">
      <button type="button" className="btn-secondary" onClick={() => void load()} disabled={isLoading || isSaving}>
        重置
      </button>
      ...
    </div>
  </div>
```

Replace the inner `<div className="flex flex-wrap items-center gap-2">` block to add the theme toggle before the existing buttons:

```tsx
<div className="flex flex-wrap items-center gap-2">
  {/* Theme toggle */}
  <button
    type="button"
    onClick={toggle}
    className="flex items-center gap-2 rounded-xl border border-white/8 bg-white/4 px-3 py-1.5 text-xs text-muted-text transition-colors hover:border-cyan/30 hover:text-white"
    title={theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'}
  >
    <span className={theme === 'dark' ? 'text-muted-text' : 'text-cyan font-semibold'}>
      ☀
    </span>
    <span className="relative inline-block h-5 w-9 rounded-full border border-white/10 bg-white/8 transition-colors">
      <span
        className={`absolute top-0.5 h-4 w-4 rounded-full bg-cyan transition-all duration-200 ${
          theme === 'light' ? 'left-4' : 'left-0.5'
        }`}
      />
    </span>
    <span className={theme === 'light' ? 'text-muted-text' : 'text-cyan font-semibold'}>
      ☾
    </span>
  </button>

  <button type="button" className="btn-secondary" onClick={() => void load()} disabled={isLoading || isSaving}>
    重置
  </button>
  <button
    type="button"
    className="btn-primary"
    onClick={() => void save()}
    disabled={!hasDirty || isSaving || isLoading}
  >
    {isSaving ? '保存中...' : `保存配置${dirtyCount ? ` (${dirtyCount})` : ''}`}
  </button>
</div>
```

- [ ] **Step 4: Verify TypeScript**

```bash
cd apps/dsa-web && npx tsc --noEmit 2>&1 | head -20
```
Expected: no errors.

---

### Task 6: Fix hardcoded dark color in ReportPriceHistory

**Files:**
- Modify: `apps/dsa-web/src/components/report/ReportPriceHistory.tsx:126`

- [ ] **Step 1: Find and replace the hardcoded class**

Current (line ~126):
```tsx
<div className="bg-[#1a1f2e] border border-white/10 rounded-lg px-3 py-2 text-xs shadow-xl">
```

Replace with CSS variables:
```tsx
<div className="bg-elevated border border-white/10 [data-theme=light_&]:border-black/8 rounded-lg px-3 py-2 text-xs shadow-xl">
```

Wait — Tailwind v4 arbitrary variant syntax for `data-theme` attribute on ancestor is: `[[data-theme=light]_&]:`. Use this pattern:

```tsx
<div className="bg-elevated border border-white/10 [[data-theme=light]_&]:border-black/8 rounded-lg px-3 py-2 text-xs shadow-xl">
```

- [ ] **Step 2: Verify build**

```bash
cd apps/dsa-web && npm run build 2>&1 | tail -10
```
Expected: `✓ built in X.XXs`

- [ ] **Step 3: Commit**

```bash
cd apps/dsa-web && git add src/App.tsx src/pages/SettingsPage.tsx src/components/report/ReportPriceHistory.tsx && git commit -m "feat: wire ThemeProvider and add theme toggle to settings"
```

---

## Chunk 3: Manual verification checklist

### Task 7: Smoke test the full feature

- [ ] **Step 1: Start dev server**

```bash
cd apps/dsa-web && npm run dev
```

Open `http://localhost:5173`

- [ ] **Step 2: Verify dark mode (default)**

- Page loads in dark mode (no flash)
- Dock is dark, cards are dark
- Settings page header shows ☀ ◯ ☾ toggle

- [ ] **Step 3: Toggle to light**

- Click the toggle → page switches to light theme immediately
- Background becomes `#f0f4fa`
- Dock becomes white/frosted
- Text becomes dark (`#0f172a`)
- Accent color becomes blue (`#2563eb`)

- [ ] **Step 4: Verify persistence**

- Hard-refresh the page
- Light theme should still be active (no flash back to dark)

- [ ] **Step 5: Toggle back to dark**

- Click toggle again → returns to dark mode
- Hard-refresh → stays dark

- [ ] **Step 6: Final build**

```bash
cd apps/dsa-web && npm run build 2>&1 | tail -5
```
Expected: `✓ built in X.XXs`

- [ ] **Step 7: Commit if any final tweaks needed**

```bash
git add -p && git commit -m "fix: theme toggle polish"
```
