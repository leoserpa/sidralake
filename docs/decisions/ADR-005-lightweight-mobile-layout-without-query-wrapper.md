# ADR-005: Lightweight Pure-CSS Mobile Layout and Selective Drawer Reload without Query Wrapping

## Status
Accepted

## Date
2026-11-25

## Context
SidraLake needed mobile responsiveness (`<= 768px`) without degrading desktop route-switching latency. During initial mobile testing, two defects surfaced:
1. Client-side SPA transitions between routes on mobile sometimes displayed Evidence's permanent `[ ⓘ Dropdown ]` error badge (fixed only by page reload). Evidence's `buildQuery.js` invokes `client-duckdb`'s `query()`, which enforces a hard-coded **5-second `withTimeout`** on `tablesPromise` (`both.js`), whereas page queries await `database_initialization` via `data.__db.query`. When a mobile client switched routes while DuckDB-WASM (`duckdb-eh.wasm`) was still initializing (>5s) or hit SvelteKit `touchstart` `preload-data="hover"` / synchronous drawer unmount races, `Dropdown.svelte` latched permanently into `hasQueryError = true`.
2. Narrow mobile viewports (`390x844`) exposed three visual issues:
   - ECharts renders chart `title` and `subtitle` on a single non-wrapping `<canvas>` line, clipping subtitles past ~48 characters (e.g., `...IB(`).
   - `.sl-grid-2` / responsive grids used `1fr` (`minmax(auto, 1fr)`), allowing `ExecTable` intrinsic width to push cards beyond viewport width.
   - Multi-column heatmaps (`12` CNAE sections in `clusters-cnae.md` and `5` consumption groups in `pulso-varejo.md`) had `~24px` cells in portrait mode, causing ECharts to auto-hide overlapping cell numbers until rotating to landscape.

## Decision
1. **Pure-CSS Mobile Layout & Left-Aligned Drawer (`TopNavBar.svelte`, `+layout.svelte`, `CityHero.svelte`, `ExecTable.svelte`):**
   - Place the hamburger menu button (`button.sl-mobile-menu-btn`) on the **left** of the SidraLake brand (market convention) with an active-page pill on the right and a 3x3 mobile drawer.
   - Apply `data-sveltekit-reload` **exclusively on mobile drawer links** (`.sl-mobile-link`), giving mobile users clean route transitions free of the `Dropdown` 5s/SPA latch while touching **zero** desktop JavaScript or `data-sveltekit-preload-data="hover"` on desktop `.sl-nav-link` links.
2. **HTML Chart Headers (`.sl-chart-head`):** Move chart `title` and `subtitle` out of ECharts `<canvas>` props across all 38 charts in `dashboard/pages/*.md` into semantic `<h3>` (`.sl-card-title`) and `<p>` (`.sl-card-subtitle`) elements using `rem`, unitless `line-height`, `overflow-wrap: break-word`, `text-wrap: balance` (headings), and `text-wrap: pretty` (subtitles).
3. **Grid Track Restraint:** Replace `1fr` with `minmax(0, 1fr)` in mobile grids and enforce `min-inline-size: 0; max-inline-size: 100%` on `.sl-grid-2 > *`, `.sl-card`, and `.sl-table-card`, with `overscroll-behavior-x: contain` on `.sl-table-scroll`.
4. **Mobile Heatmap Horizontal Scroll (`.sl-heatmap-scroll`):** Wrap the two heatmaps (`clusters-cnae.md`, `pulso-varejo.md`) in a responsive container that stays `100%` width on desktop (`> 768px`) and provides internal horizontal scroll (`min-inline-size: 640px` for 12-column CNAE, `480px` for 5-column Retail) below `768px` so all cell percentages render cleanly in portrait orientation.

## Alternatives Considered

### Global `setQueryFunction` Wrapper in `+layout.svelte` + `{#key $page.url.pathname}` + `preload-code`
- **Pros:** Fixed mobile client-side SPA `Dropdown` timeout without full-page navigation on `.sl-mobile-link`.
- **Cons:** Measured directly against live production (`https://leoserpa.github.io/sidralake/`) in headless Chromium: routing all `<Dropdown>` queries through `data.__db.query` and disabling hover data preloading caused severe desktop latency regression (initial `networkidle`: `4.94s -> 7.27s`, Demografia: `466ms -> 833ms`, Trabalho: `690ms -> 970ms`, Comparador: `637ms -> 771ms`). Even after restoring `preload-data="hover"` and removing `{#key}`, keeping `setQueryFunction` in `+layout.svelte` still forced every dropdown into `database_initialization` queuing on route changes (`networkidle` remained ~`7.27s` vs. `4.94s`).
- **Rejected:** Violated the non-negotiable requirement that mobile support must impose zero desktop performance penalty. Confirmed empirically after reverting in `d260c07` and re-benchmarking `90a161a` (6-tab desktop average `806ms` vs. baseline `812ms`).

### Shortening Chart Subtitles or Removing Cell Labels on Mobile
- **Pros:** Required no HTML restructuring inside `.md` pages.
- **Cons:** Sacrifices analytical context (CNAE section legend, unit notes, highlight thresholds) across desktop too, and fails on `320–390px` screens where even 50-character subtitles clip.
- **Rejected:** Semantic HTML headers and internal heatmap scroll preserve 100% of analytical content cleanly.

## Consequences
- **Zero desktop latency impact:** Desktop navigation runs identical JavaScript and CSS paths to pre-mobile builds (`+layout.svelte` contains only `@media` rules, zero extra JS).
- **Trade-off on mobile page transitions:** Tapping a link inside `.sl-mobile-drawer` triggers a browser navigation (`data-sveltekit-reload`) instead of SvelteKit client-side routing; browser HTTP cache serves `.wasm` and `.parquet` assets, trading instant DOM morphing for guaranteed clean `Dropdown` initialization on mobile.
- **Regression safety:** `dashboard/scripts/smoke_test_build.mjs` enforces E2E checks at both `1440x900` desktop and `390x844` mobile (menu button positioned left of brand, `overflowingCards === 0`, `overflowPx <= 4`, `brokenDropdowns === 0` across drawer navigation).
