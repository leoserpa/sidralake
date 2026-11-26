# ADR-003: Static BI in Evidence.dev (DuckDB-WASM), ZSTD Parquet Optimization, and 3-Layer Guardrails

## Status
Accepted

## Date
2026-11-24

## Context
SidraLake needed an interactive BI interface across 5,571 municipalities, state sector clusters, retail/services pulse, labor, and demographics hosted publicly on GitHub Pages with zero backend servers. Two engineering constraints emerged early:
1. All data files shipped inside the static site are downloaded into the visitor's browser for client-side **DuckDB-WASM** execution (`duckdb-eh.wasm` + Parquet files). Large uncompressed or Snappy Parquets slow down initial page load on residential and mobile connections.
2. Evidence.dev runs DuckDB-WASM inside the browser (`@duckdb/duckdb-wasm`), which coerces `BIGINT` and `DECIMAL` query columns to JavaScript `DOUBLE` (`castBigIntToDouble`, `castDecimalToDouble`), causing silent bugs in native Node/Python DuckDB tests if unchecked (such as `"2022.0"` year formatting, `100x` percentage scaling errors, or silent empty views when `WHERE` filters encounter default/null dropdown values).

## Decision
1. **Static Evidence.dev BI + GitHub Pages (`dashboard/`):** Compile SQL + Markdown pages into static HTML/JS/Arrow bundles served from `https://leoserpa.github.io/sidralake/`, executing live interactive queries locally in the browser via DuckDB-WASM.
2. **ZSTD Parquet BI Export (`src/ibge_market_intel/analytics/bi_export.py`):** Filter SCD2 dimensions (`dim_geografia`, `dim_cnae`) to `is_current = true`, drop audit columns (`_*`), surrogate keys (`sk_*`), and SCD2 metadata (`valid_from`, `valid_to`, `is_current`), sort by `("ano_referencia", "data_referencia", "sigla_uf")`, and write with `compression="zstd"`. This reduced total BI Parquet payload across the 10 exported tables by **50.7%** (`11.28 MB` -> `5.56 MB`).
3. **3-Layer Automated BI Guardrail (`src/ibge_market_intel/quality/dashboard_guard.py` + `dashboard/scripts/smoke_test_build.mjs`):**
   - **Layer 1 (Static Contracts):** Parses all `dashboard/pages/*.md` and `+layout.svelte`, enforcing required frontmatter, layout props, non-empty chart series color maps, valid `DataTable` formats, and percentage scaling rules.
   - **Layer 2 (SQL Emulation Engine):** Executes all **78 SQL queries** across default/SSR and edge-case filter permutations (`TODAS`, empty strings, non-matching cascading UF/Region combinations) against the real Parquet files inside DuckDB configured to match Evidence's `cast_big_int_to_double` / `cast_decimal_to_double` behavior.
   - **Layer 3 (Post-Build + Headless Chromium E2E):** `sidralake validate-bi --check-build` verifies built artifacts (zero unrendered SQL queries, zero `.0` year suffixes, zero raw template markers), and `smoke_test_build.mjs` loads all 9 routes in headless Chromium verifying hydration, canvas rendering, interactive filter cascades, hidden `QueryViewer` SQL blocks, and mobile layout (`390x844`).

## Alternatives Considered

### Server-Rendered BI (Streamlit / Dash / Superset / Metabase)
- **Pros:** Native Python/SQL execution without browser WASM limits or `DOUBLE` coercion quirks.
- **Cons:** Requires persistent cloud hosting, container orchestration, and cold-start management instead of free static GitHub Pages.
- **Rejected:** Breaks static GitHub Pages deployment and zero-cost hosting.

### Unoptimized Snappy Parquets in `dashboard/sources/sidralake/data/`
- **Pros:** Zero column stripping logic needed.
- **Cons:** Doubles client download weight (`11.28 MB` vs. `5.56 MB`), duplicating redundant `sk_*` hashes and historical SCD2 rows never queried by the dashboard.
- **Rejected:** Direct penalty on visitor initial load time.

## Consequences
- **Zero-cost public hosting:** Every push touching `dashboard/`, `dbt_project/`, or `src/` (plus the monthly schedule) rebuilds and deploys to GitHub Pages only after all 3 guardrail layers pass.
- **Strict SQL discipline in Evidence pages:** Because DuckDB-WASM converts `BIGINT` to `DOUBLE`, page authors must explicitly format integer years/codes and guard cascading dropdowns against empty or mismatched filter states. Any violation fails CI before deployment.
- **Residual initial payload bottleneck:** Even after ZSTD compression, `mart_inteligencia_mercado_municipal.parquet` accounts for roughly `4.0 MB` (~72% of BI Parquet size) alongside `duckdb-eh.wasm` (~`7.8 MB` gzipped), which sets the floor on uncached first-visit load time.
