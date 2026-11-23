> 🌐 **Language:** [Português (BR)](../pt-br/README.md) | **English** · [Hub](../../docs/README.md) · [Root README](../../README.en.md)

# Technical Documentation — SidraLake (English)

This documentation follows the **Diátaxis** framework and is designed for **Data Engineers and Analytics Engineers** who need to understand the architecture, set up the local environment, operate the pipeline end to end, and safely extend the **SidraLake (IBGE Market Intelligence 360)** Lakehouse.

---

## Scope

- **Included**: local Python environment with `uv`, asynchronous IBGE API ingestion, Pydantic v2 and Pandera data contracts, Bronze/Silver/Gold layers in Delta Lake and DuckDB, SCD Type 2 snapshots and `dbt-duckdb` models, Dagster orchestration (assets, partitions, blocking Asset Checks, freshness sensor, schedules), `OPTIMIZE`/`VACUUM` maintenance, test pyramid, and GitHub Actions CI.
- **Out of Scope**: cloud infrastructure deployment (AWS/GCP/Azure), containerization (Docker/Kubernetes), and external BI visualization dashboards.

---

## Navigating the 4 Quadrants

### 1. Tutorials (Learning-Oriented)
- [Getting Started: From Zero to the Gold Layer](tutorials/getting-started.md) — Set up the environment with `uv`, execute a live smoke run against IBGE APIs, query Gold tables via DuckDB, and explore Dagster UI and dbt Docs.

### 2. How-to Guides (Problem-Oriented)
- [Backfill, Reprocessing, and Delta Maintenance](how-to/backfill-and-reprocess.md) — Run a full Brazil backfill, reprocess single partitions, inspect historical versions via Time Travel, and execute `OPTIMIZE`/`VACUUM`.
- [Tune IMS Weights and Add an IBGE Source](how-to/tune-ims-and-add-ibge-source.md) — Recalibrate the Market Attractiveness Index (IMS) weights and follow the 7-step checklist to integrate a new SIDRA aggregate.
- [Run Quality Gates and Troubleshoot CI](how-to/run-quality-gates-and-ci.md) — Execute the local quality pyramid (`ruff`, `mypy`, `sqlfluff`, `pytest`, `dbt`) and troubleshoot Pandera, dbt contract, accounting, and DuckDB lock errors.

### 3. Reference (Information-Oriented)
- [Configuration, CLI, and Environment](reference/configuration-and-cli.md) — Complete specification of `ibge-pipeline` CLI, `Makefile` targets, `IBGE_*` environment variables, `profiles.yml`, and CI workflow.
- [IBGE Sources and Data Contracts](reference/ibge-sources-and-contracts.md) — Technical catalog of all 9 IBGE sources, SIDRA special codes (`-`, `..`, `...`, `X`), Pydantic v2 schemas, Pandera contracts, and audit columns.
- [Lakehouse Data Dictionary and Inventory](reference/data-dictionary-lakehouse.md) — Bronze/Silver/Gold tables, grain, keys, enforced dbt contracts, singular/unit tests, and complete Dagster inventory.

### 4. Explanation (Understanding-Oriented)
- [Medallion Architecture and Engineering Design](explanation/medallion-architecture-and-design.md) — Rationale behind the local-first stack, zero-copy `delta_scan()`/Arrow flow, ingestion resilience, idempotency, and real IBGE API edge cases.
- [Market Intelligence Methodology](explanation/market-intelligence-methodology.md) — Economic and statistical foundations of IPCA deflation, 2023 population interpolation, HHI diversification, IMS Score (0–100), Location Quotient (LQ), and Retail Pulse (PMC × IPCA).

---

## Repository Map

```text
projeto ibge/
├── .github/workflows/ci.yml              # CI pipeline (ruff, mypy, dbt, sqlfluff, pytest)
├── Makefile                              # Local operational shortcuts
├── pyproject.toml                        # Package metadata, dependencies, and tool settings
├── src/ibge_market_intel/
│   ├── cli.py                            # `ibge-pipeline` CLI (run, maintain, inspect)
│   ├── config.py                         # PipelineSettings (`IBGE_*` environment variables)
│   ├── logging.py                        # Structured JSON/console logging via structlog
│   ├── ingestion/                        # IBGE catalogs, async HTTP client, Pydantic & DeltaLakeWriter
│   ├── quality/                          # Pandera contracts (Bronze Circuit Breakers)
│   └── orchestration/                    # Dagster Bronze/dbt/Export assets, checks, sensor, schedules
├── dbt_project/
│   ├── dbt_project.yml                   # dbt project configuration and IMS weights (`vars`)
│   ├── profiles.yml                      # DuckDB profiles (`dev` and `ci`) with delta/parquet extensions
│   ├── macros/                           # `parse_ibge_numeric.sql`, `normalize_percentile.sql`, `generate_schema_name.sql`
│   ├── snapshots/                        # SCD Type 2 (`snap_ibge_municipios`, `snap_ibge_cnae_secoes`)
│   ├── models/
│   │   ├── bronze_sources.yml            # External Delta sources read via `delta_scan()`
│   │   ├── silver/                       # 9 staging views + 4 intermediate tables (+ dbt unit tests)
│   │   └── gold/                         # 4 dimensions + 6 facts (enforced contracts) + 3 OBT marts
│   └── tests/                            # 4 singular accounting & referential integrity tests
├── tests/                                # Unit tests (respx/mocks) and offline E2E integration test
└── docs/                                 # Bilingual Diátaxis documentation suite (pt-br / en)
```
