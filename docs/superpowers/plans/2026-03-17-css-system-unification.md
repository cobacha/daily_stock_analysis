# CSS System Unification — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify two parallel CSS variable systems into a single HSL-based source of truth, migrate components from `text-white` to `text-foreground`, and eliminate all theme-switching CSS hacks.

**Architecture:** Old hex CSS vars become computed aliases (`--text-primary: hsl(var(--foreground))`), so existing CSS classes continue to work while values flow from the HSL source of truth. Components replace `text-white` with `text-foreground` and `border-white/*` with semantic border utilities. The light theme block simplifies to pure HSL variable overrides.

**Tech Stack:** Tailwind CSS v4, CSS custom properties, React/TSX

---

## Chunk 1: CSS Foundation

**Goal:** Rewrite `:root` and `[data-theme="light"]` in `src/index.css`, add `.border-surface` utilities, remove the `.text-white` hack block.

### Task 1: Rewrite `:root` block in `src/index.css`

**Files:**
- Modify: `apps/dsa-web/src/index.css` lines 6–80

- [ ] **Step 1: Replace the entire `:root { ... }` block (lines 6–80) with:**

```css
:root {
  /* ─ HSL tokens — single source of truth ──────────────────────
     These are the ONLY vars that change between dark/light.     */
  --background:  228 35%  7%;
  --foreground:  210 33% 98%;
  --card:        230 24% 10%;
  --card-foreground: 210 33% 98%;
  --elevated:    230 22% 12%;
  --hover:       231 20% 16%;
  --primary:         190 100% 50%;
  --primary-foreground: 228 35%  8%;
  --secondary:       231 19% 15%;
  --secondary-foreground: 210 33% 94%;
  --muted:           230 18% 14%;
  --muted-foreground: 228 13% 66%;
  --accent:          249 84% 63%;
  --accent-foreground: 210 33% 98%;
  --destructive:     349 100% 63%;
  --destructive-foreground: 210 33% 98%;
  --success:   150 100% 53%;
  --warning:    38 100% 50%;
  --border:   226 19% 20%;
  --input:    226 19% 20%;
  --ring:     190 100% 50%;
  --radius:   1rem;
  --secondary-text: 228 16% 72%;
  --muted-text:     228 10% 48%;

  /* ─ Alpha border tokens (flip dark→light via theme override) ── */
  --border-dim:     rgba(255, 255, 255, 0.06);
  --border-default: rgba(255, 255, 255, 0.10);
  --border-strong:  rgba(255, 255, 255, 0.20);

  /* ─ Glow tokens ─────────────────────────────────────────────── */
  --glow-cyan:    rgba(0, 212, 255, 0.40);
  --glow-purple:  rgba(111, 97, 241, 0.30);
  --glow-success: rgba(0, 255, 136, 0.30);
  --glow-danger:  rgba(255, 68, 102, 0.30);

  /* ─ Computed aliases — bridge old system to new ──────────────
     Old CSS utility classes (.text-muted-text, .bg-card, etc.)
     reference these. They now auto-update when HSL tokens change. */
  --color-cyan:    hsl(var(--primary));
  --color-purple:  hsl(var(--accent));
  --color-success: hsl(var(--success));
  --color-warning: hsl(var(--warning));
  --color-danger:  hsl(var(--destructive));
  --color-cyan-glow: var(--glow-cyan);
  --color-purple-glow: var(--glow-purple);
  --bg-base:       hsl(var(--background));
  --bg-card:       hsl(var(--card));
  --bg-elevated:   hsl(var(--elevated));
  --bg-hover:      hsl(var(--hover));
  --text-primary:  hsl(var(--foreground));
  --text-secondary-text: hsl(var(--secondary-text));
  --text-muted-text:     hsl(var(--muted-text));
  --border-accent: hsl(var(--primary) / 0.3);
  --border-purple: hsl(var(--accent) / 0.28);
  --border-cyan:   hsl(var(--primary));

  /* ─ Typography ──────────────────────────────────────────────── */
  font-family: "Inter", "SF Pro Display", "Segoe UI", system-ui, -apple-system, sans-serif;
  line-height: 1.5;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

- [ ] **Step 2: Replace the `[data-theme="light"]` variable block** (the `{ --bg-base: ...; --bg-card: ...; ... }` section, currently around lines 873–919) with:

```css
/* ─────────────────────────────────────────────────────────────
   LIGHT THEME — HSL overrides only.
   Old vars (--bg-card, --text-primary, etc.) auto-recompute
   from the HSL source above — no need to repeat them here.
   ───────────────────────────────────────────────────────────── */
[data-theme="light"] {
  --background:  214 32% 96%;
  --foreground:  222 47% 11%;
  --card:          0  0% 100%;
  --card-foreground: 222 47% 11%;
  --elevated:    210 40% 98%;
  --hover:       214 32% 93%;

  --primary:         221 83% 53%;
  --primary-foreground: 0 0% 100%;
  --secondary:       210 40% 96%;
  --secondary-foreground: 222 47% 11%;
  --muted:           210 40% 96%;
  --muted-foreground: 215 16% 47%;
  --accent:          249 65% 55%;
  --accent-foreground: 0 0% 100%;
  --destructive:     349 80% 50%;
  --destructive-foreground: 0 0% 100%;

  --secondary-text:  215 25% 40%;
  --muted-text:      215 16% 60%;

  --border:   214 32% 91%;
  --input:    214 32% 91%;
  --ring:     221 83% 53%;

  /* Alpha borders flip from white-on-dark to black-on-light */
  --border-dim:     rgba(0, 0, 0, 0.05);
  --border-default: rgba(0, 0, 0, 0.08);
  --border-strong:  rgba(0, 0, 0, 0.15);

  /* Glow tokens become subtle shadows in light mode */
  --glow-cyan:    rgba(37, 99, 235, 0.20);
  --glow-purple:  rgba(111, 97, 241, 0.20);
}
```

- [ ] **Step 3: Keep** the existing component-level override rules that follow the variable block (dock-surface, dock-logo, dock-item, btn-primary, btn-secondary, input-terminal, title-gradient, scrollbar). These contain hardcoded `rgba()` values that cannot auto-update and must remain.

- [ ] **Step 4: Delete the entire "Text color overrides" hack block** at the end of the file (the block starting with `/* ── Text color overrides ──` containing `.text-white { color: var(--text-primary) }`, prose overrides, etc.). This is ~40 lines. These hacks become unnecessary after the component migration in Chunks 2–3.

- [ ] **Step 5: Add `.border-surface` semantic utilities** in the `/* ============ Utilities ============ */` section, after the existing `.border-cyan` rule:

```css
/* Semantic alpha-border utilities — theme-adaptive */
.border-surface        { border-color: var(--border-default); }
.border-surface-dim    { border-color: var(--border-dim); }
.border-surface-strong { border-color: var(--border-strong); }

/* Hover variants (escape the colon for CSS class names) */
.hover\:border-surface:hover        { border-color: var(--border-default); }
.hover\:border-surface-dim:hover    { border-color: var(--border-dim); }
.hover\:border-surface-strong:hover { border-color: var(--border-strong); }
```

- [ ] **Step 6: Build verification**

```bash
cd /Users/11069760/claude-test/daily_stock_analysis/apps/dsa-web && npm run build
```

Expected: `✓ built` with no errors.

- [ ] **Step 7: Commit**

```bash
git add apps/dsa-web/src/index.css
git commit -m "refactor(css): unify CSS var systems — computed alias bridge, simplify light theme, add border-surface utilities"
```

---

## Chunk 2: Component `text-white` → `text-foreground` Migration

**Rule:** Replace `text-white` with `text-foreground` in all `.tsx` files **EXCEPT**:
- `Button.tsx` `gradient` and `danger` variants (lines 25–26): white text on cyan/danger bg — **keep**
- `ScoreGauge.tsx` line 165: white text on colored glow bg — **keep**
- `ConfirmDialog.tsx` confirm button (line 54): white on danger bg — **keep**
- `.dock-item.is-active` in CSS (already `color: #fff` in CSS class body, no TSX change needed)

Also replace `hover:text-white` → `hover:text-foreground` everywhere (hover state should be theme-adaptive).

### Task 2: Common components

**Files:**
- Modify: `apps/dsa-web/src/components/common/PageHeader.tsx`
- Modify: `apps/dsa-web/src/components/common/Card.tsx`
- Modify: `apps/dsa-web/src/components/common/SectionCard.tsx`
- Modify: `apps/dsa-web/src/components/common/StatCard.tsx`
- Modify: `apps/dsa-web/src/components/common/EmptyState.tsx`
- Modify: `apps/dsa-web/src/components/common/Drawer.tsx`
- Modify: `apps/dsa-web/src/components/common/ConfirmDialog.tsx`

- [ ] **Step 1: PageHeader.tsx** — line 24: `text-white` → `text-foreground` (page title h1)

- [ ] **Step 2: Card.tsx** — lines 48, 64: `text-white` → `text-foreground` (card title h3, both render paths)

- [ ] **Step 3: SectionCard.tsx** — line 24: `text-white` → `text-foreground` (section title h2)

- [ ] **Step 4: StatCard.tsx** — line 40: `text-white` → `text-foreground` (stat value div)

- [ ] **Step 5: EmptyState.tsx** — line 22: `text-white` → `text-foreground` (empty state title h3)

- [ ] **Step 6: Drawer.tsx** — line 73: `text-white` → `text-foreground` (drawer title h2); line 79: `hover:text-white` → `hover:text-foreground` (close button)

- [ ] **Step 7: ConfirmDialog.tsx** — line 39: `text-white` → `text-foreground` (dialog title h3); line 47: `hover:text-white` → `hover:text-foreground` (cancel button); line 54: **keep** `text-white` (confirm button on danger bg)

- [ ] **Step 8: Build**

```bash
cd /Users/11069760/claude-test/daily_stock_analysis/apps/dsa-web && npm run build
```

Expected: `✓ built`.

- [ ] **Step 9: Commit**

```bash
git add apps/dsa-web/src/components/common/
git commit -m "refactor: text-white → text-foreground in common components"
```

### Task 3: Settings components

**Files:**
- Modify: `apps/dsa-web/src/components/settings/SettingsField.tsx`
- Modify: `apps/dsa-web/src/components/settings/IntelligentImport.tsx`
- Modify: `apps/dsa-web/src/components/settings/LLMChannelEditor.tsx`
- Modify: `apps/dsa-web/src/components/settings/ChangePasswordCard.tsx`

- [ ] **Step 1: SettingsField.tsx** — line 211: `text-white` → `text-foreground` (field label)

- [ ] **Step 2: IntelligentImport.tsx**
  - Line 274: `text-white` → `text-foreground` (section label "智能导入")
  - Line 300: `text-white` → `text-foreground` (textarea text color)
  - Line 352: `text-white` → `text-foreground` (valid code span)
  - Lines 326, 329, 332, 361: `hover:text-white` → `hover:text-foreground`

- [ ] **Step 3: LLMChannelEditor.tsx**
  - Line 221: `text-white` → `text-foreground` (channel display name)
  - Line 872: `text-white` → `text-foreground` (section heading h3 "AI 模型配置")

- [ ] **Step 4: ChangePasswordCard.tsx** — line 66: `text-white` → `text-foreground` (label "修改密码")

- [ ] **Step 5: Build**

```bash
cd /Users/11069760/claude-test/daily_stock_analysis/apps/dsa-web && npm run build
```

Expected: `✓ built`.

- [ ] **Step 6: Commit**

```bash
git add apps/dsa-web/src/components/settings/
git commit -m "refactor: text-white → text-foreground in settings components"
```

### Task 4: Report + market components

**Files:**
- Modify: `apps/dsa-web/src/components/report/ReportMarkdown.tsx`
- Modify: `apps/dsa-web/src/components/report/ReportOverview.tsx`
- Modify: `apps/dsa-web/src/components/report/ReportNews.tsx`
- Modify: `apps/dsa-web/src/components/report/ReportDetails.tsx`
- Modify: `apps/dsa-web/src/components/report/ReportStrategy.tsx`
- Modify: `apps/dsa-web/src/components/report/ReportPriceHistory.tsx`
- Modify: `apps/dsa-web/src/components/history/HistoryList.tsx`
- Modify: `apps/dsa-web/src/components/tasks/TaskPanel.tsx`
- Modify: `apps/dsa-web/src/components/market/MarketReviewMarkdown.tsx`

- [ ] **Step 1: ReportMarkdown.tsx**
  - Line 76: `text-white` → `text-foreground` (stock name h2)
  - Line 106: `prose-headings:text-white` → `prose-headings:text-foreground`
  - Line 111: `prose-strong:text-white` → `prose-strong:text-foreground`
  - Line 116: `prose-th:text-white` → `prose-th:text-foreground`
  - Line 136: `hover:text-white` → `hover:text-foreground` (copy button)

- [ ] **Step 2: ReportOverview.tsx**
  - Lines 45, 77, 95, 112: `text-white` → `text-foreground`
  - Line 125: `text-white` → `text-foreground` (heading "Market Sentiment")

- [ ] **Step 3: ReportNews.tsx**
  - Lines 56, 100: `text-white` → `text-foreground`
  - Lines 65, 114: `hover:text-white` → `hover:text-foreground`

- [ ] **Step 4: ReportDetails.tsx** — lines 58, 81, 107: `text-white` → `text-foreground`

- [ ] **Step 5: ReportStrategy.tsx** — line 73: `text-white` → `text-foreground`

- [ ] **Step 6: ReportPriceHistory.tsx**
  - Line 218: `text-white` → `text-foreground` (heading "价格走势")
  - Line 231: `hover:text-white` → `hover:text-foreground`
  - Line 316: `color: 'text-white'` → `color: 'text-foreground'` (statLabels JS object)

- [ ] **Step 7: HistoryList.tsx** — line 182: `text-white` → `text-foreground` (stock name)

- [ ] **Step 8: TaskPanel.tsx** — lines 55, 135: `text-white` → `text-foreground` (task titles)

- [ ] **Step 9: MarketReviewMarkdown.tsx**
  - Line 13: `text-primary` → `text-foreground` (h2 section heading — was incorrectly set to cyan primary; should be theme-adaptive foreground)
  - Line 39: `text-white` → `text-foreground` (strong/bold text if present)

- [ ] **Step 10: Build**

```bash
cd /Users/11069760/claude-test/daily_stock_analysis/apps/dsa-web && npm run build
```

Expected: `✓ built`.

- [ ] **Step 11: Commit**

```bash
git add apps/dsa-web/src/components/report/ apps/dsa-web/src/components/history/ apps/dsa-web/src/components/tasks/ apps/dsa-web/src/components/market/
git commit -m "refactor: text-white → text-foreground in report/history/market components"
```

### Task 5: Pages

**Files:**
- Modify: `apps/dsa-web/src/pages/SettingsPage.tsx`
- Modify: `apps/dsa-web/src/pages/ChatPage.tsx` (prose classes only)
- Modify: `apps/dsa-web/src/pages/LoginPage.tsx`

- [ ] **Step 1: SettingsPage.tsx**
  - Line 112: `text-white` → `text-foreground` (page h1 "系统设置")
  - Line 195: `text-white` → `text-foreground` (active nav tab)
  - Line 196: `hover:text-white` → `hover:text-foreground` (inactive nav tab hover)

- [ ] **Step 2: ChatPage.tsx** — find and replace prose Tailwind modifier classes:
  - `prose-headings:text-white` → `prose-headings:text-foreground`
  - `prose-strong:text-white` → `prose-strong:text-foreground`
  - `prose-th:text-white` → `prose-th:text-foreground`

- [ ] **Step 3: LoginPage.tsx** — find any `text-white` on heading/label elements and replace with `text-foreground`. (Keep `text-white` on the submit button if it's on a colored background.)

- [ ] **Step 4: Build**

```bash
cd /Users/11069760/claude-test/daily_stock_analysis/apps/dsa-web && npm run build
```

Expected: `✓ built`.

- [ ] **Step 5: Verify no stray text-white remain**

```bash
grep -rn "text-white" --include="*.tsx" apps/dsa-web/src/ | grep -v "Button.tsx\|ScoreGauge"
```

Review results: any remaining `text-white` should be on explicitly colored elements (danger bg, gradient bg). If any are on plain headings/labels, fix them.

- [ ] **Step 6: Commit**

```bash
git add apps/dsa-web/src/pages/
git commit -m "refactor: text-white → text-foreground in pages"
```

---

## Chunk 3: Border Migration + Final Validation

**Rule for `border-white/*` replacement:**
- `/5`, `/6` → `border-surface-dim`
- `/8`, `/10`, `/12` → `border-surface`
- `/16`, `/18`, `/20` → `border-surface-strong`

When used with a `border` width class: `border border-white/10` → `border border-surface` (keep `border` for width).
When used as `hover:border-white/10`: → `hover:border-surface` (custom CSS utility added in Task 1).
**Do NOT change** `border-t-white` (spinner track color, intentional).

Run this first to see all files:
```bash
grep -rn "border-white/" --include="*.tsx" apps/dsa-web/src/
```

### Task 6: Migrate common components — borders

**Files:**
- Modify: `apps/dsa-web/src/components/common/PageHeader.tsx`
- Modify: `apps/dsa-web/src/components/common/Button.tsx`
- Modify: `apps/dsa-web/src/components/common/EmptyState.tsx`
- Modify: `apps/dsa-web/src/components/common/StatCard.tsx`
- Modify: `apps/dsa-web/src/components/common/Drawer.tsx`
- Modify: `apps/dsa-web/src/components/common/ConfirmDialog.tsx`
- Modify: `apps/dsa-web/src/components/common/Collapsible.tsx`
- Modify: `apps/dsa-web/src/components/common/Select.tsx`
- Modify: `apps/dsa-web/src/components/common/Input.tsx`
- Modify: `apps/dsa-web/src/components/common/Toolbar.tsx`
- Modify: `apps/dsa-web/src/components/common/Loading.tsx`
- Modify: `apps/dsa-web/src/components/common/ApiErrorAlert.tsx`
- Modify: `apps/dsa-web/src/components/common/StickyActionBar.tsx`
- Modify: `apps/dsa-web/src/components/common/Pagination.tsx`

- [ ] **Step 1:** For each file above, read it and apply the replacement rule.

Key replacements:
- **PageHeader.tsx** line 20: `border-white/8` → `border-surface`
- **Button.tsx** line 22 (secondary variant): `border-white/10` → `border-surface`
- **EmptyState.tsx**: `border-white/10` → `border-surface`
- **StatCard.tsx**: `border-white/8` → `border-surface`
- **Drawer.tsx**: `border-white/5` → `border-surface-dim`, `border-white/10` → `border-surface`
- **ConfirmDialog.tsx**: `border-white/10` → `border-surface`
- **Collapsible.tsx**: `border-white/8` → `border-surface`
- **Select.tsx**: `border-white/10` → `border-surface`; `hover:border-white/18` → `hover:border-surface-strong`
- **Input.tsx**: `border-white/10` → `border-surface`; `hover:border-white/18` → `hover:border-surface-strong`
- **Toolbar.tsx**: `border-white/8` → `border-surface`
- **Loading.tsx**: `border-white/8` → `border-surface`
- **ApiErrorAlert.tsx**: `border-white/8` → `border-surface`
- **StickyActionBar.tsx**: `border-white/8` → `border-surface`
- **Pagination.tsx**: `border-white/8` → `border-surface`

- [ ] **Step 2: Build**

```bash
cd /Users/11069760/claude-test/daily_stock_analysis/apps/dsa-web && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add apps/dsa-web/src/components/common/
git commit -m "refactor: border-white/* → border-surface in common components"
```

### Task 7: Migrate settings, report, history, market components — borders

**Files:**
- Modify: `apps/dsa-web/src/components/settings/SettingsField.tsx`
- Modify: `apps/dsa-web/src/components/settings/IntelligentImport.tsx`
- Modify: `apps/dsa-web/src/components/settings/LLMChannelEditor.tsx`
- Modify: `apps/dsa-web/src/components/settings/ChangePasswordCard.tsx`
- Modify: `apps/dsa-web/src/components/settings/SettingsLoading.tsx`
- Modify: `apps/dsa-web/src/components/report/ReportMarkdown.tsx`
- Modify: `apps/dsa-web/src/components/report/ReportOverview.tsx`
- Modify: `apps/dsa-web/src/components/report/ReportNews.tsx`
- Modify: `apps/dsa-web/src/components/report/ReportDetails.tsx`
- Modify: `apps/dsa-web/src/components/report/ReportStrategy.tsx`
- Modify: `apps/dsa-web/src/components/report/ReportPriceHistory.tsx`
- Modify: `apps/dsa-web/src/components/history/HistoryList.tsx`
- Modify: `apps/dsa-web/src/components/market/MarketTopBar.tsx`
- Modify: `apps/dsa-web/src/components/market/MarketReviewMarkdown.tsx`

- [ ] **Step 1:** Read each file and apply replacement rule.

Key replacements:
- **ReportMarkdown.tsx**: `prose-h1:border-white/10` → `prose-h1:border-surface`; `prose-pre:border-white/10` → `prose-pre:border-surface`; `prose-th:border-white/20` → `prose-th:border-surface-strong`; `prose-td:border-white/20` → `prose-td:border-surface-strong`; `prose-hr:border-white/10` → `prose-hr:border-surface`; also remove the manual `[[data-theme=light]_&]:border-black/8` override on the tooltip (it's now handled by `border-surface`)
- **ReportPriceHistory.tsx**: remove `[[data-theme=light]_&]:border-black/8` — no longer needed with `border-surface`
- **HistoryList.tsx**: `border-white/5` → `border-surface-dim`; `border-white/20` → `border-surface-strong`; `hover:border-white/10` → `hover:border-surface`
- **LLMChannelEditor.tsx**: multiple `border-white/8` → `border-surface`, `border-white/10` → `border-surface`

- [ ] **Step 2: Build**

```bash
cd /Users/11069760/claude-test/daily_stock_analysis/apps/dsa-web && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add apps/dsa-web/src/components/settings/ apps/dsa-web/src/components/report/ apps/dsa-web/src/components/history/ apps/dsa-web/src/components/market/
git commit -m "refactor: border-white/* → border-surface in settings/report/history/market components"
```

### Task 8: Migrate pages — borders

**Files:**
- Modify: `apps/dsa-web/src/pages/LoginPage.tsx`
- Modify: `apps/dsa-web/src/pages/SettingsPage.tsx`
- Modify: `apps/dsa-web/src/pages/MarketPage.tsx`
- Modify: `apps/dsa-web/src/pages/BacktestPage.tsx`
- Modify: `apps/dsa-web/src/pages/PortfolioPage.tsx`
- Modify: `apps/dsa-web/src/pages/ChatPage.tsx`
- Modify: `apps/dsa-web/src/pages/HomePage.tsx`

- [ ] **Step 1:** Read each file. Apply replacement rule. **Exception:** do NOT change `border-t-white` (spinner animation track).

Key replacements:
- **SettingsPage.tsx**: `border-white/8` → `border-surface` (multiple: header, toggle pill, nav items, form sections)
- **MarketPage.tsx**: `border-white/5` → `border-surface-dim`; `border-white/20` → `border-surface-strong`
- **ChatPage.tsx**: many `border-white/5`, `/10` replacements; also `prose-pre:border-white/10` → `prose-pre:border-surface`, etc.
- **PortfolioPage.tsx**: multiple `border-white/5`, `/10` replacements
- **BacktestPage.tsx**: multiple replacements

- [ ] **Step 2: Build**

```bash
cd /Users/11069760/claude-test/daily_stock_analysis/apps/dsa-web && npm run build
```

Expected: `✓ built`.

- [ ] **Step 3: Final verification**

```bash
# Should return zero results:
grep -rn "border-white/" --include="*.tsx" apps/dsa-web/src/

# Should only show Button.tsx (gradient/danger) and ScoreGauge.tsx:
grep -rn "text-white" --include="*.tsx" apps/dsa-web/src/
```

- [ ] **Step 4: Commit**

```bash
git add apps/dsa-web/src/pages/
git commit -m "refactor: border-white/* → border-surface in pages — complete CSS system unification"
```

---

## Summary

| Area | Change |
|------|--------|
| `src/index.css` `:root` | ~25 old hex vars replaced with HSL tokens + computed aliases |
| `src/index.css` `[data-theme="light"]` | Simplified to pure HSL overrides (removes ~20 redundant var repetitions) |
| `src/index.css` hack block | Removed `[data-theme="light"] .text-white` hack entirely |
| `src/index.css` utilities | Added `.border-surface`, `.border-surface-dim`, `.border-surface-strong` |
| ~22 component/page files | `text-white` → `text-foreground` |
| ~35 component/page files | `border-white/*` → `border-surface*` |

**Result:** Single HSL source of truth. Theme switching works by changing only the HSL vars in `[data-theme="light"]`. Old custom CSS classes (`.text-muted-text`, `.bg-card`, etc.) continue working via computed aliases. No global CSS hacks.
