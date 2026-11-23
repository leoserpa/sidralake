> 🌐 **Language:** [Português (BR)](README.md) | **English** · [Full Documentation (Diátaxis)](docs/en/README.md)

# SidraLake — IBGE Market Intelligence 360 (Medallion Data Pipeline)

**SidraLake** is a Data Engineering pipeline built on the **Medallion Architecture (Bronze → Silver → Gold)** for **360° Market Intelligence** powered by official **IBGE** (Brazilian Institute of Geography and Statistics) APIs (Localities, CNAE 2.0, Municipal GDP, 2022 Census, Population Estimates, Municipal & Sectoral CEMPRE Business Registry, IPCA Inflation, and Monthly Retail Survey - PMC).

The project implements a **Local-First Modern Data Stack** focused on reliability, data contracts, and governance: **Delta Lake** with ACID transactions and Time Travel, **DuckDB + dbt-duckdb** for Silver/SCD Type 2/Gold modeling, **Polars + Pandera + Pydantic v2** as ingestion quality gates, and **Dagster** for asset-oriented orchestration, partitions, freshness sensors, and end-to-end lineage.

---

## Tech Stack

- **ACID Lakehouse**: Delta Lake (`deltalake`) across Bronze, Silver, and Gold layers (`_delta_log`, `replace_where`, `MERGE`, `OPTIMIZE`, `VACUUM`)
- **Analytical Engine & Transformation**: DuckDB + `dbt-duckdb` (`delta_scan()`, Staging, Intermediate, SCD Type 2 via `dbt snapshot`, Gold Star Schema + OBT Marts, Enforced Model Contracts, dbt Unit Tests, and accounting singular tests)
- **Ingestion & Data Contracts**: Python `>=3.12,<3.14` (`uv`), asynchronous `httpx` with semaphore concurrency and adaptive UF/semester chunking, `tenacity` exponential backoff with jitter, `Pydantic v2`, `Polars`, `Pandera[polars]`
- **Orchestration & Lineage**: Dagster (`dagster-dbt`, annual static partitions, blocking Asset Checks, IBGE API Freshness Sensor, and Schedules)
- **Quality & Observability**: `structlog` JSON logging, `ruff`, `mypy`, `sqlfluff`, `pytest` + `respx`, GitHub Actions CI

---

## Quick Start

```bash
make setup              # Creates .venv via uv and installs dbt packages (dbt_utils)
make materialize-smoke  # Fast smoke run (SP/MT) Bronze -> Silver -> Gold + Delta Export
make materialize-full   # Full Brazil load (5,571 municipalities, 2018-2026)
make inspect-gold       # Prints IMS rankings, CNAE clusters (LQ), and PMC x IPCA pulse
make dagster-dev        # Starts Dagster UI (39-asset graph, partitions, 155 checks)
make dbt-docs           # Builds and serves the dbt Docs catalog and SQL lineage (port 8080)
make test               # Runs ruff, mypy, pytest (unit + E2E), and dbt unit tests
```

---

## Technical Documentation (Diátaxis)

All documentation follows the **Diátaxis** framework with mirrored bilingual editions (`docs/pt-br/` and `docs/en/`). Visit the [Central Documentation Hub](docs/README.md) or browse the English quadrants directly:

| Diátaxis Quadrant | Purpose | Document |
| :--- | :--- | :--- |
| **Tutorial** | Hands-on walkthrough to set up and run the pipeline for the first time | [Getting Started](docs/en/tutorials/getting-started.md) |
| **How-to Guide** | Run full loads, surgical partition backfills, Time Travel, and Delta maintenance | [Backfill, Reprocessing, and Delta Maintenance](docs/en/how-to/backfill-and-reprocess.md) |
| **How-to Guide** | Recalibrate IMS Score weights and integrate a new SIDRA aggregate | [Tune IMS Weights and Add an IBGE Source](docs/en/how-to/tune-ims-and-add-ibge-source.md) |
| **How-to Guide** | Run local quality gates and troubleshoot common pipeline failures | [Run Quality Gates and Troubleshoot CI](docs/en/how-to/run-quality-gates-and-ci.md) |
| **Reference** | `ibge-pipeline` CLI, `Makefile` targets, `IBGE_*` env vars, `profiles.yml`, and CI | [Configuration, CLI, and Environment](docs/en/reference/configuration-and-cli.md) |
| **Reference** | Catalog of all 9 IBGE sources, SIDRA special codes, and Pydantic/Pandera contracts | [IBGE Sources and Data Contracts](docs/en/reference/ibge-sources-and-contracts.md) |
| **Reference** | Bronze/Silver/Gold data dictionary, dbt tests, and Dagster inventory | [Lakehouse Data Dictionary and Inventory](docs/en/reference/data-dictionary-lakehouse.md) |
| **Explanation** | Medallion design decisions, resilience patterns, and real IBGE edge cases | [Medallion Architecture and Engineering Design](docs/en/explanation/medallion-architecture-and-design.md) |
| **Explanation** | Economic and statistical rationale behind IPCA deflation, HHI, IMS, LQ, and PMC | [Market Intelligence Methodology](docs/en/explanation/market-intelligence-methodology.md) |

---

## License and Data Attribution

The source code of this project is licensed under the **[GNU General Public License v3.0 (GPL-3.0)](LICENSE)**. The extracted primary data belongs to the **Brazilian Institute of Geography and Statistics (IBGE)** and is publicly accessible under the Brazilian Federal Government Open Data Policy.
