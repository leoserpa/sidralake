> 🌐 **Language:** [Português (BR)](../../pt-br/tutoriais/primeiros-passos.md) | **English** · [Index](../README.md)

# Getting Started: From Zero to the Gold Layer

In this hands-on tutorial, you will set up the local environment, run the **IBGE Market Intelligence 360** pipeline in smoke mode against live IBGE APIs, query Gold Delta Lake tables directly with DuckDB, and explore full lineage in **Dagster UI** and **dbt Docs**.

---

## Prerequisites

Make sure your machine has:
- **Operating System**: Linux or macOS
- **Python**: `>=3.12,<3.14`
- **uv**: Python environment and package manager (`uv --version`)
- **git**: required for dbt packages and version control (`git --version`)
- **Outbound HTTP access**: connectivity to `https://servicodados.ibge.gov.br/api`

---

## Step 1: Set Up the Environment and Dependencies

From the repository root (`projeto ibge`), run:

```bash
make setup
```

This command performs two actions:
1. `uv sync --dev` — creates the `.venv/` virtual environment and installs all production and development dependencies defined in `pyproject.toml`.
2. `uv run dbt deps --project-dir dbt_project --profiles-dir dbt_project` — installs `dbt-labs/dbt_utils` into `dbt_project/dbt_packages/`.

Confirm the CLI entrypoint is ready:

```bash
uv run ibge-pipeline --help
```

You should see the `run`, `maintain`, and `inspect` subcommands.

---

## Step 2: Run Your First Pipeline Execution (Smoke Run)

Instead of downloading all 5,571 municipalities across 2018–2026 on your very first run, start with `smoke` mode, which ingests live IBGE data for **São Paulo (`35`)** and **Mato Grosso (`51`)** over a smaller year window:

```bash
make materialize-smoke
```

Watch the structured logs flow through the three stages:
1. **Bronze Ingestion (`_ingest_all_bronze`)**: asynchronous HTTP requests to Localities, CNAE 2.0, and SIDRA endpoints, **Pandera** contract validation, and partitioned writes to `data/bronze/<table>`.
2. **`dbt build` Transformations**: builds Silver staging views and intermediate tables (`silver`), **SCD Type 2** snapshots (`snapshots`), Gold Star Schema + OBT marts (`gold`), and executes schema, accounting, and dbt `unit_tests`.
3. **ACID Delta Export (`silver_delta_export` & `gold_delta_export`)**: exports curated tables to open **Delta Lake** format under `data/silver/` and `data/gold/`.

> **Note:** If you already ran a full Brazil load (`make materialize-full`), running `make materialize-smoke` replaces the target tables with the SP/MT subset. Re-run `make materialize-full` anytime to restore full national coverage.

---

## Step 3: Inspect the Gold Layer

Run the built-in inspection command to print a quick summary of the Gold analytics layer:

```bash
make inspect-gold
```

The output displays:
- **Top 15 municipalities** ranked by `ims_score_0_100`
- **Market Tier breakdown** (`Tier 1 - Polo Nacional` through `Tier 4 - Local / Nicho`)
- Validation of *Boa Esperança do Norte - MT* (`5101837`) inside `gold.dim_geografia`
- **Top state sector clusters** by Location Quotient (`QL`)
- **Monthly retail pulse (PMC × IPCA)** for the latest available period
- Row counts and Delta versions (`_delta_log`) for the 3 Gold Data Marts

Next, run an ad-hoc SQL query directly against the Gold **Delta Lake** table using DuckDB:

```bash
uv run python -c "
import duckdb
con = duckdb.connect()
con.execute('LOAD delta;')
rows = con.execute('''
    SELECT
        rank_nacional_ims,
        nome_municipio,
        sigla_uf,
        ano_referencia,
        ims_score_0_100,
        tier_mercado
    FROM delta_scan('data/gold/mart_inteligencia_mercado_municipal')
    WHERE is_ultimo_ano_completo
    ORDER BY rank_nacional_ims
    LIMIT 5
''').fetchall()
for r in rows:
    print(r)
"
```

---

## Step 4: Explore Lineage and Catalog Visually

### 4.1 Dagster UI (Orchestration, Partitions, and Checks)

Start the local Dagster webserver:

```bash
make dagster-dev
```

Open the URL printed in your terminal (typically `http://127.0.0.1:3000`). Inside the UI:
- Open **Assets → Global Asset Lineage** to inspect the unified **39-asset graph** linking `bronze/*` → `silver/*` → `gold/*` → `lakehouse/*`.
- Click any Bronze asset (e.g., `bronze/pib_municipal`) to inspect year partitions (`ano_referencia`), materialization metadata (`rows_written`, `delta_version`, `payload_hash`), and Pandera **Asset Checks**.
- Open **Automation** to view the `ibge_new_period_sensor` freshness sensor and recurring schedules.

Stop the server with `Ctrl+C` when finished.

### 4.2 dbt Docs (Column Catalog and SQL Lineage)

Generate and serve the interactive dbt documentation site:

```bash
make dbt-docs
```

Open `http://127.0.0.1:8080` in your browser to browse model descriptions, enforced column contracts, macros, and SQL lineage across `bronze_ibge`, `silver`, `snapshots`, and `gold`. Stop with `Ctrl+C`.

---

## Next Steps

Now that you have completed an end-to-end run:
- To load all **5,571 Brazilian municipalities** and learn how to backfill or rewind individual partitions, follow [Backfill, Reprocessing, and Delta Maintenance](../how-to/backfill-and-reprocess.md).
- To understand the architectural choices and real IBGE API edge cases handled by this pipeline, read [Medallion Architecture and Engineering Design](../explanation/medallion-architecture-and-design.md).
