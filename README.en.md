> 🌐 **Language:** [Português (BR)](README.md) | **English** · [Full Documentation (Diátaxis)](docs/en/README.md)

# SidraLake — IBGE Market Intelligence 360 (Medallion Data Pipeline)

**SidraLake** is a Data Engineering pipeline built on the **Medallion Architecture (Bronze → Silver → Gold)** for **360° Market Intelligence** powered by official **IBGE** (Brazilian Institute of Geography and Statistics) APIs (Localities, CNAE 2.0, Municipal GDP, 2022 Census, Population Estimates, Municipal & Sectoral CEMPRE Business Registry, IPCA Inflation, Monthly Retail Survey - PMC, Monthly Services Survey - PMS, and Quarterly PNAD Contínua).

The project implements a **Local-First Modern Data Stack** focused on reliability, data contracts, and governance: **Delta Lake** with ACID transactions and Time Travel, **DuckDB + dbt-duckdb** for Silver/SCD Type 2/Gold modeling, **Polars + Pandera + Pydantic v2** as ingestion quality gates, and **Dagster** for asset-oriented orchestration, partitions, freshness sensors, and end-to-end lineage.

---

## Tech Stack

- **ACID Lakehouse**: Delta Lake (`deltalake`) across Bronze, Silver, and Gold layers (`_delta_log`, `replace_where`, `MERGE`, `OPTIMIZE`, `VACUUM`)
- **Analytical Engine, Contracts & Semantic Layer**: DuckDB + `dbt-duckdb` 1.12 (`delta_scan()`, Staging, Intermediate, SCD Type 2 via `dbt snapshot`, Gold Star Schema + 3 OBT Marts with **Enforced Model Contracts** across 100% of Gold models, **dbt Semantic Layer** with 3 semantic models, 12 governed metrics, and `time_spine_daily`, **10 SQL dbt Unit Tests**, and singular accounting tests)
- **Ingestion & Lazy Analytics**: Python `>=3.12,<3.14` (`uv`), asynchronous `httpx` with semaphore concurrency and adaptive UF/semester chunking, `tenacity` exponential backoff with jitter, `Pydantic v2`, **Polars Lazy API** (`scan_delta` + deterministic Arrow IPC hashing), `Pandera[polars]`
- **Orchestration & Lineage**: Dagster (`dagster-dbt`, annual dynamic partitions, blocking Asset Checks, **Declarative Automation `AutomationCondition.eager()`** on dbt models and Delta exports, dynamic IBGE API Freshness Sensor, and Schedules)
- **BI as Code Layer**: **Evidence.dev** (`dashboard/`, 9 pages including Demographics & Regional Poles, PNAD Labor & Income, and PMS Services) in SQL + Markdown compiled to static **DuckDB-WASM** and deployed automatically to **GitHub Pages** (`https://leoserpa.github.io/sidralake/`) via `.github/workflows/pages.yml` with monthly freshness manifest
- **Quality & Observability**: `structlog` JSON logging, `ruff`, `mypy --strict`, `sqlfluff`, `pytest` (`>85%` coverage) + `respx`, GitHub Actions CI

---

## dbt Lineage DAG (from `manifest.json`)

```mermaid
graph LR
    %% Sources (Blue)
    s_loc["localidades"]:::source
    s_cnae["cnae_secoes"]:::source
    s_pib["pib_municipal"]:::source
    s_censo["censo_populacao"]:::source
    s_est["estimativa_populacao"]:::source
    s_cemp_m["cempre_municipal"]:::source
    s_cemp_uf["cempre_setorial_uf"]:::source
    s_ipca["ipca_mensal"]:::source
    s_pmc["pmc_varejo_uf"]:::source

    %% Staging (Bronze)
    stg_loc["stg_ibge__localidades"]:::staging
    stg_cnae["stg_ibge__cnae_secoes"]:::staging
    stg_pib["stg_ibge__pib_municipal"]:::staging
    stg_censo["stg_ibge__censo_populacao"]:::staging
    stg_est["stg_ibge__estimativa_populacao"]:::staging
    stg_cemp_m["stg_ibge__cempre_municipal"]:::staging
    stg_cemp_uf["stg_ibge__cempre_setorial_uf"]:::staging
    stg_ipca["stg_ibge__ipca_mensal"]:::staging
    stg_pmc["stg_ibge__pmc_varejo_uf"]:::staging

    %% Silver Intermediate & SCD2 Snapshots (Silver)
    snap_mun["snap_ibge_municipios (SCD2)"]:::silver
    snap_cnae["snap_ibge_cnae_secoes (SCD2)"]:::silver
    int_ipca["int_ipca_deflator_anual"]:::silver
    int_pib["int_pib_municipal_deflacionado"]:::silver
    int_pop["int_populacao_municipal_unificada"]:::silver
    int_cemp["int_cempre_municipal_deflacionado"]:::silver

    %% Gold Dimensions, Facts & Marts (Gold)
    dim_geo["dim_geografia"]:::gold
    dim_cnae["dim_cnae"]:::gold
    dim_var["dim_atividade_varejo"]:::gold
    dim_tempo["dim_tempo / time_spine_daily"]:::gold
    fct_pib["fct_pib_municipal"]:::gold
    fct_pop["fct_populacao_municipal"]:::gold
    fct_cemp_m["fct_cempre_municipal"]:::gold
    fct_cemp_uf["fct_cempre_setorial_uf"]:::gold
    fct_ipca["fct_ipca_mensal"]:::gold
    fct_pmc["fct_pmc_varejo_mensal"]:::gold
    mart_ims["mart_inteligencia_mercado_municipal"]:::gold
    mart_cl["mart_clusters_setoriais_uf"]:::gold
    mart_pmc["mart_pulso_consumo_macro"]:::gold

    %% Lineage edges (extracted from dbt manifest.json)
    s_loc --> stg_loc --> snap_mun --> dim_geo
    s_cnae --> stg_cnae --> snap_cnae --> dim_cnae
    s_ipca --> stg_ipca --> int_ipca
    stg_ipca --> fct_ipca
    s_pib --> stg_pib --> int_pib
    int_ipca --> int_pib --> fct_pib
    dim_geo --> fct_pib
    s_censo --> stg_censo --> int_pop
    s_est --> stg_est --> int_pop --> fct_pop
    dim_geo --> fct_pop
    s_cemp_m --> stg_cemp_m --> int_cemp
    int_ipca --> int_cemp --> fct_cemp_m
    dim_geo --> fct_cemp_m
    s_cemp_uf --> stg_cemp_uf --> fct_cemp_uf
    dim_cnae --> fct_cemp_uf
    int_ipca --> fct_cemp_uf
    s_pmc --> stg_pmc --> dim_var --> fct_pmc
    stg_pmc --> fct_pmc

    dim_geo --> mart_ims
    fct_pib --> mart_ims
    fct_pop --> mart_ims
    fct_cemp_m --> mart_ims
    dim_geo --> mart_cl
    dim_cnae --> mart_cl
    fct_cemp_uf --> mart_cl
    dim_geo --> mart_pmc
    dim_var --> mart_pmc
    fct_pmc --> mart_pmc
    fct_ipca --> mart_pmc

    classDef source fill:#1E88E5,stroke:#0D47A1,color:#FFFFFF
    classDef staging fill:#CD7F32,stroke:#7B4B16,color:#FFFFFF
    classDef silver fill:#B0BEC5,stroke:#455A64,color:#111111
    classDef gold fill:#FBC02D,stroke:#F57F17,color:#111111
```

> **Legend:** 🔵 **Bronze Delta Sources** · 🟤 **Staging (`stg_*`)** · ⚪ **Intermediate (`int_*`) & SCD2 Snapshots** · 🟡 **Gold Layer (Dimensions, Facts, Marts & Semantic Layer)**

---

## Quick Start

```bash
uv sync --dev                        # Creates .venv via uv and installs dependencies
uv run sidralake run --mode smoke    # Fast smoke run (SP/MT) Bronze -> Silver -> Gold + Delta
uv run sidralake run --mode full     # Full Brazil load (5,571 municipalities, 2018+ dynamic)
uv run sidralake insights --top 10   # Instant market rankings via Polars Lazy API (scan_delta)
uv run sidralake export-bi           # Exports Gold Marts as Snappy Parquet for Evidence.dev BI
uv run sidralake inspect             # Full sanity check against DuckDB and Gold Delta Lake
uv run sidralake test                # Runs ruff, mypy, pytest (unit + E2E), and 10 dbt unit tests
make dagster-dev                     # Starts Dagster UI (assets, partitions, blocking checks)
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
