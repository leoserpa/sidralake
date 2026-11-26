# AGENTS.md — SidraLake Engineering & Documentation Guide

This guide documents project conventions, verified commands, non-negotiable architectural invariants, and known gotchas for humans and AI coding agents working in SidraLake (`v0.5.0`).

---

## Project Snapshot

- **Scope:** Local-First Medallion Lakehouse (`Bronze -> Silver -> Gold` in Delta Lake + DuckDB + `dbt-duckdb` + Polars + Pandera + Dagster) + Static BI as Code (**Evidence.dev** compiled to DuckDB-WASM on GitHub Pages).
- **Scale:** `12` official IBGE sources, `5,571` municipalities (`2018+`), `49` Dagster assets, `204` asset checks, `193` dbt data tests, `11` SQL dbt unit tests, `9` BI dashboard pages, `38` charts, and `78` validated BI SQL queries.
- **Architectural Rationale:** Always consult [`docs/decisions/README.md`](docs/decisions/README.md) (`ADR-001` through `ADR-006`) before altering core stack, scoring, deployment, mobile navigation, or regional boundary behavior.

---

## Verified Commands

| Task | Command | Notes |
| :--- | :--- | :--- |
| Bootstrap Python & dbt | `make setup` | Runs `uv sync --dev` and `dbt deps` |
| Full standard quality gate | `make test` | `ruff` lint/format + `mypy src` + `pytest` (unit + integration) + `dbt parse` + `11` SQL unit tests |
| SQL style lint | `make sql-lint` | Runs `sqlfluff lint` (`duckdb` dialect, `dbt` templater) |
| Documentation & ADR check | `make check-docs` | Verifies relative Markdown links, ADR headings, and git doc-vs-code drift |
| Strict documentation drift audit | `uv run python scripts/check_doc_drift.py --strict-drift` | Exits non-zero if any mapped doc is `stale` relative to its code paths |
| Smoke pipeline run (SP/MT) | `uv run sidralake run --mode smoke` | Fast live IBGE ingestion + `dbt build` + ACID Delta exports |
| Full Brazil pipeline run | `uv run sidralake run --mode full` | All `5,571` municipalities, dynamic periods (`2018+`) |
| Export BI Parquets (ZSTD) | `uv run sidralake export-bi` | Exports `10` Gold tables to `dashboard/parquet_data/` |
| Validate BI contracts & SQL | `uv run sidralake validate-bi --check-build` | Static contracts + `78` SQL queries under DuckDB-WASM `DOUBLE` emulation + `dashboard/build/` |
| Build & E2E test BI UI | `cd dashboard && npm run build && touch build/.nojekyll && CHROME_PATH=/usr/bin/google-chrome npm run test:e2e` | Audits all `9` routes at `1440x900`, interactive filters, and `390x844` mobile |
| Dagster UI | `make dagster-dev` | Starts local Dagster webserver at `http://127.0.0.1:3000` |

---

## Non-Negotiable Invariants & Known Gotchas

### 1. Desktop Navigation & Mobile Drawer Performance (`ADR-005`)
- **Do not** call `setQueryFunction` or wrap `<slot />` in `{#key $page.url.pathname}` inside [`dashboard/pages/+layout.svelte`](dashboard/pages/+layout.svelte). Empirical benchmarking proved this regresses desktop initial `networkidle` (`4.94s -> 7.27s`) and route switches (`+300ms`–`+370ms`).
- Keep `data-sveltekit-preload-data="hover"` on desktop `.sl-nav-link` links and keep `data-sveltekit-reload` **exclusively** on `.sl-mobile-link` inside [`dashboard/components/TopNavBar.svelte`](dashboard/components/TopNavBar.svelte).
- Keep the mobile menu trigger button (`button.sl-mobile-menu-btn`) positioned on the **left** of the brand lockup; [`smoke_test_build.mjs`](dashboard/scripts/smoke_test_build.mjs) asserts `menuRect.left < brandRect.left`.

### 2. Chart Headers, Grids, and Mobile Heatmaps (`ADR-005`)
- **Never** pass `title=` or `subtitle=` props inside Evidence chart tags (`<LineChart>`, `<BarChart>`, `<ScatterPlot>`, `<BubbleChart>`, `<Heatmap>`); ECharts renders canvas titles on one line and clips them on mobile. Always place titles in `<div class="sl-chart-head"><h3 class="sl-card-title">...</h3><p class="sl-card-subtitle">...</p></div>` above the chart.
- Keep `minmax(0, 1fr)` (never bare `1fr`) on `.sl-grid-2` / responsive grids and `min-inline-size: 0` on `.sl-card` and `.sl-table-card` so wide `ExecTable` containers never overflow narrow viewports.
- Multi-column heatmaps on mobile must stay wrapped in `.sl-heatmap-scroll` + `.sl-heatmap-inner`.

### 3. DuckDB-WASM Type Coercion & BI Guardrails (`ADR-003`)
- Evidence's browser engine (`@duckdb/duckdb-wasm`) coerces `BIGINT` and `DECIMAL` results to IEEE-754 `DOUBLE`. Cast integer IDs/years cleanly when needed and validate all queries with `uv run sidralake validate-bi`.
- **Never** expose Evidence `QueryViewer` SQL accordions in production UI and never remove required layout props checked by [`src/ibge_market_intel/quality/dashboard_guard.py`](src/ibge_market_intel/quality/dashboard_guard.py).
- Note that BI Parquets live in `dashboard/parquet_data/` (gitignored), **outside** `dashboard/sources/sidralake/data/`, and BI SQL source queries must reference `parquet_data/<table>.parquet` rather than `../../parquet_data/...`.

### 4. IBGE Domain & Warehouse Constraints (`ADR-001`, `ADR-002`, `ADR-006`)
- **Single DuckDB Writer Lock:** DuckDB allows only one writer process on `data/warehouse/ibge_market_intel.duckdb` at a time. When running parallel checks (e.g. `sqlfluff` with `dbt` templater while Dagster or `dbt build` holds the file), pass `IBGE_DUCKDB_PATH=/tmp/sandbox.duckdb`.
- **Enforced Gold Contracts:** Every Gold dimension, fact, and mart requires `contract: { enforced: true }` in `dbt_project/models/gold/_gold.yml` matching explicit SQL `cast(...)` column names and types. Never drop `enforced: true` to bypass a schema error.
- **Nullable `microrregiao` (`5101837`):** Newly emancipated *Boa Esperança do Norte - MT* returns `"microrregiao": null` from IBGE Localidades v1 (`schemas.py`, `contracts.py`). Always derive state/region hierarchy via `regiao-imediata`.
- **Official Immediate Regions (`ADR-006`):** `municipio.md` neighbor comparisons strictly use IBGE `nome_regiao_imediata` (e.g., *Amparo* belongs to RGI *Amparo* while *Pedreira* belongs to RGI *Campinas*); do not alter this boundary with distance heuristics.
- **IMS Partial-Year Caveat (`ADR-002`):** Years with incomplete pillars re-normalize available pillar weights to stay on `[0, 100]` and are **not** directly comparable YoY against complete-pillar years; longitudinal comparisons must match identical pillar coverage or filter `is_ultimo_ano_completo = true`.

### 5. Documentation & ADR Workflow
- Preserve **1:1 parity** between [`docs/pt-br/`](docs/pt-br/README.md) and [`docs/en/`](docs/en/README.md), and update both [`README.md`](README.md) and [`README.en.md`](README.en.md).
- Append a dated entry to [`CHANGELOG.md`](CHANGELOG.md) when shipping user-facing features or architectural changes; never rewrite historical release entries.
- Add a sequential ADR in [`docs/decisions/`](docs/decisions/README.md) for any significant architectural or irreversible trade-off, then verify with `make check-docs`.
- Do not install untracked agent directories (such as `.agents/`) inside the repository working tree.
