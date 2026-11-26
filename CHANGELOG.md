# Changelog

All notable changes to SidraLake are documented in this file.

> **Maintenance Policy:** Append new dated entries or release sections chronologically. Never rewrite, collapse, or delete published release entries; git preserves file diffs while this log preserves the reasoning behind each change.

## [Unreleased]

### Added
- Architecture Decision Records under [`docs/decisions/`](docs/decisions/README.md) (`ADR-001` through `ADR-006`) covering the local-first stack, IPCA deflation & IMS scoring, DuckDB-WASM/ZSTD BI guardrails, dynamic SIDRA period discovery, lightweight mobile layout trade-offs, and strict IBGE immediate region boundaries.
- Agent and contributor guide [`AGENTS.md`](AGENTS.md) with verified commands, DuckDB-WASM/Evidence invariants, and documentation maintenance rules.
- Automated documentation link, ADR structure, and git-ancestry drift checker in [`scripts/check_doc_drift.py`](scripts/check_doc_drift.py) wired to `make check-docs`.

### Changed
- Synchronized [`README.md`](README.md), [`README.en.md`](README.en.md), and the bilingual Diátaxis documentation suite (`docs/pt-br/` and `docs/en/`) with `v0.5.0` metrics (`12` IBGE sources, `17` Gold models / `6` OBT marts, `193` dbt data tests + `11` SQL unit tests, `49` Dagster assets / `204` checks, `34` pytest unit + `2` integration tests, `9` BI pages, `38` charts, and `78` validated SQL queries).
- Updated ZSTD Parquet description in [`src/ibge_market_intel/cli.py`](src/ibge_market_intel/cli.py) and step titles in [`.github/workflows/pages.yml`](.github/workflows/pages.yml) to match current behavior.

---

## [0.5.0] - 2026-11-25

### Added
- Left-aligned mobile hamburger menu button and 3x3 navigation drawer in [`TopNavBar.svelte`](dashboard/components/TopNavBar.svelte) using `data-sveltekit-reload` exclusively on mobile drawer links for clean route initialization without mobile `Dropdown` errors.
- Pure-CSS responsive layout adjustments across [`+layout.svelte`](dashboard/pages/+layout.svelte), [`CityHero.svelte`](dashboard/components/CityHero.svelte), and [`ExecTable.svelte`](dashboard/components/ExecTable.svelte) for screens `<= 768px`, leaving desktop (`> 768px`) runtime JavaScript unchanged.
- Internal horizontal scroll container (`.sl-heatmap-scroll`) for the multi-column heatmaps on [`clusters-cnae.md`](dashboard/pages/clusters-cnae.md) and [`pulso-varejo.md`](dashboard/pages/pulso-varejo.md) so all percentage labels stay visible in portrait mobile view.
- Mobile viewport (`390x844`) Playwright Chromium E2E audit in [`smoke_test_build.mjs`](dashboard/scripts/smoke_test_build.mjs) verifying left menu alignment, zero viewport overflow, zero overflowing cards, and drawer navigation without broken dropdowns.

### Changed
- Extracted chart `title` and `subtitle` props across all 38 Evidence charts in `dashboard/pages/*.md` into semantic HTML headers (`.sl-chart-head` using `rem` sizing, `text-wrap: balance`, and `text-wrap: pretty`) to prevent ECharts `<canvas>` single-line text clipping on mobile.
- Replaced `1fr` with `minmax(0, 1fr)` on responsive grids and added `min-inline-size: 0` on cards/tables to stop wide `ExecTable` blocks from pushing grid tracks past the viewport.
- Expanded full CNAE section names (`I`, `M`, `N`, and all 12 columns) in the [`clusters-cnae.md`](dashboard/pages/clusters-cnae.md) heatmap subtitle.

### Fixed
- Restored desktop `data-sveltekit-preload-data="hover"` and eliminated `setQueryFunction` / `{#key}` wrappers after empirical benchmarking showed mobile SPA wrappers regressed desktop route switching (`4.94s -> 7.27s` initial `networkidle`). See [`ADR-005`](docs/decisions/ADR-005-lightweight-mobile-layout-without-query-wrapper.md).
- Changed the [`MethodologyCard.svelte`](dashboard/components/MethodologyCard.svelte) info icon to neutral gray (`#9ca3a0`) matching secondary UI chrome.

---

## [0.4.0] - 2026-11-24

### Added
- Three new official IBGE data sources integrated end to end: **PMS Services** (`SIDRA 5906` -> `mart_pulso_servicos_uf`), **PNAD Contínua Labor & Earnings** (`SIDRA 4099` and `5436` -> `mart_mercado_trabalho_uf`), and consolidated **`mart_demografia_municipal`** with strict 2022 Census baseline (`49` total Dagster assets, `11` dbt SQL unit tests).
- New BI pages for **Demografia & Polos Regionais** (`/demografia/`) and **Mercado de Trabalho & Renda** (`/trabalho/`), CNAE Location Quotient specialization views (`/clusters-cnae/`), and PMS Services UF ranking (`/pulso-varejo/`).
- Dynamic SIDRA period discovery (`discover_available_years`), dynamic dbt calendar bounds (`dim_tempo` / `time_spine_daily`), and monthly GitHub Actions schedule with `.github/last_data_refresh.json` and [`DataFooter.svelte`](dashboard/components/DataFooter.svelte).
- UI components [`ResetFilters.svelte`](dashboard/components/ResetFilters.svelte) across all filterable pages, [`MethodologyCard.svelte`](dashboard/components/MethodologyCard.svelte) glossary on `index.md`, and SidraLake 360 vector branding in [`TopNavBar.svelte`](dashboard/components/TopNavBar.svelte).
- Cascading `Região -> UF -> Município` filter safety guards across SQL queries (`not exists` orphan-UF guard and `sel_ids`/`alvo` resolution) plus interactive Playwright filter tests in [`smoke_test_build.mjs`](dashboard/scripts/smoke_test_build.mjs).

### Changed
- Optimized BI Parquet export in [`bi_export.py`](src/ibge_market_intel/analytics/bi_export.py) using ZSTD compression, stripping `sk_*`, `_` audit, and SCD2 technical columns, and sorting rows (`11.28 MB -> 5.56 MB`, `-50.7%`).
- Enhanced [`ExecTable.svelte`](dashboard/components/ExecTable.svelte) conditional formatting (`barInvert`, directional growth indicators, and solid Cidade A / Cidade B badges matching chart colors).

### Fixed
- Hid Evidence `QueryViewer` SQL accordions via `:has()` CSS and guarded against exposure in E2E smoke tests.
- Hardened HTTP retries for Cloudflare `5xx` responses from IBGE SIDRA endpoints.

---

## [0.3.0] - 2026-11-23

### Added
- Matte graphite charcoal design system (`#191c1d` canvas, `#0b0f0d` surface, `#3b82f6` focal accent) across all BI pages and custom components (`TopNavBar`, `KpiCard`, `ExecTable`, `CityHero`, `DonutPanel`).
- Automated 3-layer BI quality gate: static contract validation (`dashboard_guard.py`), DuckDB-WASM `DOUBLE` coercion query emulation (`sidralake validate-bi`), and headless Chromium post-build E2E smoke suite (`smoke_test_build.mjs`).

### Fixed
- Resolved Evidence DuckDB-WASM `BIGINT`/`DECIMAL` -> `DOUBLE` `.0` year formatting bugs, `100x` percentage scaling issues, stacked bar label clipping, and responsive axis bounds.

---

## [0.2.0] - 2026-11-23

### Added
- Static **Evidence.dev** (`dashboard/`) BI layer powered by DuckDB-WASM and automated deployment workflow to **GitHub Pages** (`.github/workflows/pages.yml`).
- Export command `sidralake export-bi` and **Polars Lazy API** (`scan_delta`) analytical module (`insights`).
- **dbt Semantic Layer** definitions (`3` semantic models, `12` governed metrics, and `time_spine_daily`) alongside `contract: { enforced: true }` across Gold models.

---

## [0.1.0] - 2026-11-23

### Added
- Initial **Medallion Architecture (`Bronze -> Silver -> Gold`)** Lakehouse built on Delta Lake, DuckDB + `dbt-duckdb`, Polars, Pydantic v2, Pandera blocking asset checks, and Dagster orchestration.
- Asynchronous IBGE ingestion (`Localidades`, `CNAE 2.0`, `PIB 5938`, `Censo 4714`, `Estimativa 6579`, `CEMPRE 9509`/`9418`, `IPCA 1737`, `PMC 8883`), SCD Type 2 municipal/CNAE snapshots, constant-price IPCA deflation, 2023 population linear interpolation, Score IMS (0–100), Location Quotient, and Retail Pulse (`PMC × IPCA`).
- Bilingual Diátaxis documentation suite (`docs/pt-br/` and `docs/en/`), unit/integration tests, and GitHub Actions CI (`ruff`, `mypy`, `dbt`, `sqlfluff`, `pytest`).
