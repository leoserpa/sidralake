> 🌐 **Language:** [Português (BR)](../../pt-br/guias-praticos/backfill-e-reprocessamento.md) | **English** · [Index](../README.md)

# How to Backfill, Reprocess, and Maintain Delta Lake

This guide provides practical recipes to run full national loads, idempotently reprocess individual partitions, inspect historical snapshots with Delta Time Travel, and compact files across the Lakehouse.

---

## 1. Run a Full Brazil Backfill

To ingest all **5,571 municipalities** across the dynamic window (`2018+`, discovered from the IBGE API), run the full `dbt build`, and export all curated layers to Delta Lake:

```bash
make materialize-full
```

---

## 2. Restrict Ingestion to Specific States (`UF`) for Dev/Staging

Set the `IBGE_UF_FILTER` environment variable (a JSON list of IBGE state codes) before running the pipeline:

```bash
IBGE_UF_FILTER='[35, 33]' uv run ibge-pipeline run --mode full
```

This filter applies automatically to municipal tables (`N6`), state tables (`N3`), and the localities reference table.

---

## 3. Reprocess or Backfill a Single Year Partition

All SIDRA tables in the Bronze layer are partitioned by `ano_referencia` and written via `replace_where` (`predicate="ano_referencia = '<year>'"`), guaranteeing zero duplicate rows.

### Option A: Via Dagster UI (Declarative Backfill)

1. Start the UI with `make dagster-dev`.
2. Open **Assets** and select the target asset (for example, `bronze/pib_municipal` or `bronze/cempre_municipal`).
3. Click **Materialize** and pick only the desired year (or partition range).
4. Once the blocking Pandera **Asset Check** passes, run `dbt_medallion_job` to refresh Silver, Gold, and Delta exports.

### Option B: Programmatically via Python (Surgical Reload)

Run the snippet below, replacing the spec (`PIB_MUNICIPAL_SPEC`) and target year (`"2023"`):

```bash
uv run python - << 'EOF'
import asyncio
from ibge_market_intel.config import get_settings
from ibge_market_intel.ingestion.catalogs import PIB_MUNICIPAL_SPEC
from ibge_market_intel.ingestion.client import IBGEAsyncClient
from ibge_market_intel.ingestion.delta_writer import DeltaLakeWriter
from ibge_market_intel.quality.contracts import validate_sidra_contract

async def backfill_year(ano: str) -> None:
    settings = get_settings()
    settings.ensure_directories()
    async with IBGEAsyncClient(settings) as client:
        res = await client.fetch_agregado_for_year(PIB_MUNICIPAL_SPEC, ano=ano, uf_codes=settings.uf_filter)
    report = validate_sidra_contract(res.df, PIB_MUNICIPAL_SPEC.table_name)
    if not report.passed:
        raise RuntimeError(report.error_message)
    writer = DeltaLakeWriter(settings.resolved_bronze_dir)
    out = writer.write_partition_overwrite(
        res.df,
        PIB_MUNICIPAL_SPEC.table_name,
        partition_col="ano_referencia",
        partition_value=ano,
        ingestion_id=f"manual-backfill-{ano}",
        source_url=res.source_urls[0] if res.source_urls else "",
    )
    print(f"Partition {ano} written: delta_v={out.delta_version}, rows={out.rows_written}")

asyncio.run(backfill_year("2023"))
EOF
```

Then rebuild downstream dbt models and re-export to Delta Lake:

```bash
make dbt-build
uv run dagster asset materialize --select lakehouse/silver_delta_export,lakehouse/gold_delta_export -m ibge_market_intel.orchestration.definitions
```

> **Tip:** To load a year outside the default window (e.g., GDP `2017`), add `"2017"` to `PIB_YEARS` in `src/ibge_market_intel/ingestion/catalogs.py` so it is also registered in Dagster's `PIB_PARTITIONS`.

---

## 4. Audit History and Read Earlier Versions (Delta Time Travel)

Every write to `data/bronze/`, `data/silver/`, or `data/gold/` creates an immutable transaction entry in `_delta_log`.

Inspect commit history and read an older snapshot:

```bash
uv run python - << 'EOF'
from deltalake import DeltaTable
import polars as pl

path = "data/bronze/pib_municipal"
dt = DeltaTable(path)
print("Current version:", dt.version())
for entry in dt.history(limit=5):
    print(entry.get("version"), entry.get("timestamp"), entry.get("operation"))

# Read version 0 for comparison
dt_v0 = DeltaTable(path, version=0)
df_v0 = pl.from_arrow(dt_v0.to_pyarrow_table())
print("Rows in version 0:", df_v0.height)
EOF
```

---

## 5. Compact Small Files and Prune Unreferenced Parquet Files (`OPTIMIZE` + `VACUUM`)

Repeated partition reloads create multiple small Parquet files and stale versions on disk. Run the Lakehouse ACID maintenance routine:

```bash
make delta-maintenance
```

This command walks `data/bronze/`, `data/silver/`, and `data/gold/`, executing:
- `dt.optimize.compact()` — merges small files into read-optimized Parquet files.
- `dt.vacuum(retention_hours=168, dry_run=False, enforce_retention_duration=True)` — deletes physical files unreferenced for over 7 days (168 hours), preserving the recent Time Travel window.

You can also trigger `delta_maintenance_job` manually from the **Jobs** tab in Dagster UI.
