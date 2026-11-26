# ADR-001: Local-First Medallion Stack with Delta Lake, DuckDB, dbt, Polars, Pandera, and Dagster

## Status
Accepted

## Date
2026-11-23

## Context
SidraLake processes official Brazilian macroeconomic and municipal datasets (5,571 municipalities from 2018 onward across 12 IBGE APIs). The engineering requirements were:
- ACID storage with Time Travel and partition-level idempotency without managed cloud infrastructure or recurring compute bills.
- Strict data quality enforcement at ingestion (handling IBGE special symbols `-`, `..`, `...`, `X` and schema quirks such as nullable `microrregiao` in newly emancipated municipalities).
- Reproducible SQL modeling with SCD Type 2 history, enforced schema contracts, native SQL unit tests, and end-to-end Python-to-SQL lineage.

## Decision
Build a Local-First Medallion pipeline (`Bronze -> Silver -> Gold`) combining:
- **Delta Lake (`deltalake` / delta-rs)** for ACID storage across `data/bronze/`, `data/silver/`, and `data/gold/`.
- **Polars (`LazyFrame` / `DataFrame`) + Pydantic v2 + Pandera** for deterministic flattening, hashing (`_payload_hash`), and blocking Bronze quality contracts (`@asset_check(blocking=True)`).
- **DuckDB + `dbt-duckdb`** reading Bronze Delta tables directly via `delta_scan()`, maintaining SCD Type 2 snapshots (`snap_ibge_municipios`, `snap_ibge_cnae_secoes`), enforced Gold contracts, singular accounting tests, and dbt Semantic Layer definitions.
- **Dagster (`dagster-dbt`)** unifying Python ingestion assets, dbt models, blocking checks, and zero-copy Arrow Delta exports (`to_arrow_table()`) into one lineage graph.

## Alternatives Considered

### Managed Cloud Data Warehouse (BigQuery / Snowflake + Cloud Object Storage)
- **Pros:** Elastic multi-user concurrency, managed storage lifecycle, built-in IAM.
- **Cons:** Requires cloud billing, credentials setup for contributors, and external storage orchestration even though total dataset volume fits comfortably in local Parquet/Delta files.
- **Rejected:** Violates the local-first, zero-cloud-cost reproducibility goal.

### PostgreSQL as Primary Warehouse
- **Pros:** Strong concurrency control and mature relational tooling.
- **Cons:** No native zero-copy Delta Lake reading or columnar Parquet compression for analytical scans across multi-year municipal tables; requires separate ETL copies into analytics stores.
- **Rejected:** DuckDB + Delta Lake eliminates ingestion-to-warehouse copies via `delta_scan()` and Apache Arrow exports.

### Apache Spark (PySpark + Delta Lake)
- **Pros:** Industry standard for multi-terabyte distributed workloads.
- **Cons:** Heavy JVM/driver startup overhead for megabyte-to-tens-of-megabytes IBGE tables; poor developer ergonomics for fast CI test execution.
- **Rejected:** Overkill for IBGE scale; DuckDB + Polars completes a full national run (5,571 municipalities, 2018–2026) in roughly 108 seconds on a single developer machine.

## Consequences
- **Zero infrastructure cost:** contributors run `make setup` and execute the entire stack locally in Python 3.12 via `uv`.
- **Zero-copy interoperability:** Bronze Delta is read directly via `delta_scan()` and Silver/Gold tables are exported back to Delta via Apache Arrow.
- **Concurrency constraint:** DuckDB permits only **one writer process per `.duckdb` file at a time**. Parallel runs (for example, running `sqlfluff` with dbt templater while `dagster dev` or `dbt build` holds a write lock) must wait or override `IBGE_DUCKDB_PATH` to an isolated path.
- **Migration path:** Because curated outputs live in open Delta Lake tables with Arrow schemas, migrating compute later to Databricks, Trino, or DuckDB in cloud object storage requires changing IO paths rather than rewriting models.
