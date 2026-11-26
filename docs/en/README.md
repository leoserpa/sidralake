> 🌐 **Language:** [Português (BR)](../pt-br/README.md) | **English** · [Hub](../README.md) · [ADRs](../decisions/README.md) · [Root README](../../README.en.md)

# Technical Documentation — SidraLake (`v0.5.0`, English)

This documentation follows the **Diátaxis** framework for **Data Engineers, Analytics Engineers, and coding agents** operating, validating, and extending the **SidraLake** Lakehouse and **BI as Code** layer.

---

## Scope

- **Included**: local Python environment with `uv`, asynchronous ingestion across 12 IBGE APIs, Pydantic v2 and Pandera contracts, Bronze/Silver/Gold layers in Delta Lake and DuckDB, SCD Type 2 snapshots and `dbt-duckdb` models, dbt Semantic Layer, Dagster orchestration (`49` assets, `204` checks, dynamic partitions, freshness sensor, schedules), ZSTD Parquet export + **Evidence.dev** dashboard (`dashboard/`, 9 pages in DuckDB-WASM) with 3-layer BI guardrails, and GitHub Actions CI + Pages deployment.
- **Out of Scope**: paid cloud infrastructure deployment (AWS/GCP/Azure) and containerization (Docker/Kubernetes).

---

## Navigating the Quadrants and ADRs

### 1. Tutorials (Learning-Oriented)
- [Getting Started: From Zero to the Gold Layer](tutorials/getting-started.md) — Set up the environment with `uv`, execute a live smoke run, query Gold Delta tables via DuckDB, explore Dagster UI / dbt Docs, and run BI export/validation.

### 2. How-to Guides (Problem-Oriented)
- [Backfill, Reprocessing, and Delta Maintenance](how-to/backfill-and-reprocess.md) — Run a full Brazil load, reprocess single partitions, inspect historical snapshots via Time Travel, and execute `OPTIMIZE`/`VACUUM`.
- [Tune IMS Weights and Add an IBGE Source](how-to/tune-ims-and-add-ibge-source.md) — Recalibrate Score IMS pillar weights and follow the 7-step checklist to integrate a new SIDRA aggregate.
- [Run Quality Gates and Troubleshoot CI](how-to/run-quality-gates-and-ci.md) — Execute Python, dbt, 3-layer BI, and documentation checks (`make check-docs`), plus troubleshoot common failures.

### 3. Reference (Information-Oriented)
- [Configuration, CLI, and Environment](reference/configuration-and-cli.md) — Complete specification of `sidralake` CLI (and `ibge-pipeline` alias), `Makefile` targets, `IBGE_*` environment variables, `profiles.yml`, and `.github/workflows/` pipelines.
- [IBGE Sources and Data Contracts](reference/ibge-sources-and-contracts.md) — Technical catalog of all 12 official IBGE sources, SIDRA special codes (`-`, `..`, `...`, `X`), Pydantic v2 schemas, Pandera contracts, and audit columns.
- [Lakehouse Data Dictionary and Inventory](reference/data-dictionary-lakehouse.md) — Bronze/Silver/Gold tables, grain, keys, enforced contracts, `193`+`11` dbt tests, and unified Dagster inventory (`49` assets / `204` checks).

### 4. Explanation (Understanding-Oriented)
- [Medallion Architecture and Engineering Design](explanation/medallion-architecture-and-design.md) — Rationale behind the local-first stack, zero-copy `delta_scan()`/Arrow flow, BI as Code layer, resilience, and real IBGE edge cases.
- [Market Intelligence Methodology](explanation/market-intelligence-methodology.md) — Economic foundations of IPCA deflation, 2023 population interpolation, HHI, IMS Score, QL, Retail Pulse (PMC), Services (PMS), Labor/Income (PNAD), and Municipal Demographics.

### 5. Architecture Decision Records (ADRs) & Governance
- [ADR Index (`ADR-001` through `ADR-006`)](../decisions/README.md)
- [Agent & Contributor Guide (`AGENTS.md`)](../../AGENTS.md) · [Changelog (`CHANGELOG.md`)](../../CHANGELOG.md)

---

## Repository Map

```text
projeto ibge/
├── .github/workflows/
│   ├── ci.yml                            # CI (ruff, mypy, dbt parse/unit tests, sqlfluff, pytest)
│   └── pages.yml                         # Monthly/push Evidence.dev BI build & GitHub Pages deploy
├── AGENTS.md                             # Engineering invariants, commands, and known gotchas
├── CHANGELOG.md                          # Append-only chronological release history
├── Makefile                              # Local operational shortcuts (including `check-docs`)
├── pyproject.toml                        # Version 0.5.0, dependencies, and scripts (`sidralake` / `ibge-pipeline`)
├── scripts/
│   └── check_doc_drift.py                # Markdown link, ADR compliance, and git-ancestry drift checker
├── src/ibge_market_intel/
│   ├── cli.py                            # `sidralake` CLI (`run`, `maintain`, `inspect`, `insights`, `export-bi`, `validate-bi`, `test`)
│   ├── config.py                         # PipelineSettings (`IBGE_*` environment variables)
│   ├── logging.py                        # Structured JSON/console logging via structlog
│   ├── ingestion/                        # 12 IBGE catalogs, dynamic period discovery, async HTTP client, Pydantic & DeltaLakeWriter
│   ├── quality/                          # Pandera Bronze contracts and `dashboard_guard.py` (DuckDB-WASM)
│   ├── analytics/                        # `insights.py` (Polars Lazy) and `bi_export.py` (ZSTD Parquet)
│   └── orchestration/                    # 49 Dagster assets, 204 checks, sensor, and schedules
├── dbt_project/
│   ├── dbt_project.yml                   # dbt project configuration and IMS weights (`vars`)
│   ├── profiles.yml                      # DuckDB profiles (`dev` and `ci`) with delta/parquet extensions
│   ├── macros/                           # `parse_ibge_numeric.sql`, `normalize_percentile.sql`, `generate_schema_name.sql`
│   ├── snapshots/                        # SCD Type 2 (`snap_ibge_municipios`, `snap_ibge_cnae_secoes`)
│   ├── models/
│   │   ├── bronze_sources.yml            # 12 external Delta sources read via `delta_scan()`
│   │   ├── silver/                       # 12 staging views + 4 intermediate tables (+ 6 dbt unit tests)
│   │   └── gold/                         # 5 dimensions (incl. time_spine_daily) + 6 facts + 6 OBT marts + 3 semantic models (+ 5 unit tests)
│   └── tests/                            # 4 singular accounting & referential integrity tests
├── dashboard/
│   ├── pages/                            # 9 Evidence.dev Markdown pages + `+layout.svelte` (desktop + mobile CSS)
│   ├── components/                       # TopNavBar, KpiCard, ExecTable, CityHero, DonutPanel, ResetFilters, MethodologyCard, DataFooter
│   ├── sources/sidralake/                # 10 SQL sources querying `parquet_data/*.parquet`
│   └── scripts/smoke_test_build.mjs      # Headless Chromium E2E audit (1440x900, interactive filters, 390x844 mobile)
├── tests/                                # 34 unit tests and 2 integration tests
└── docs/                                 # Bilingual Diátaxis documentation (`pt-br/` / `en/`) + `decisions/` (ADRs)
```
