# ADR-004: Dynamic SIDRA Period Discovery, Dynamic Calendar, and Dagster Partitions

## Status
Accepted

## Date
2026-11-24

## Context
Early versions hardcoded year lists (for example `["2018", ..., "2025"]`) across `catalogs.py`, `partitions.py`, `dim_tempo.sql`, and BI scripts. Every time IBGE published a new month (IPCA `1737`, PMC `8883`, PMS `5906`), quarter (PNAD `4099`, `5436`), or annual release (GDP `5938`, Population `6579`, CEMPRE `9509`/`9418`), manual code edits and commits were required across multiple files before the pipeline or sensor could ingest the new period.

## Decision
1. **Runtime Period Discovery (`discover_available_years` in `src/ibge_market_intel/ingestion/catalogs.py`):** Query `/api/v3/agregados/{id}/periodos` at runtime (bounded by `min_year` per survey and falling back cleanly to conservative defaults when offline) to determine available annual partitions without hardcoding end years.
2. **Dynamic dbt Calendar (`dim_tempo.sql`, `time_spine_daily.sql`):** Compute the end horizon dynamically from current execution date / max observed source periods (`2018-01` through current year + 1) instead of static end-date bounds.
3. **Dagster `DynamicPartitionsDefinition` & Unified Sensor (`partitions.py`, `sensors.py`):** Register dynamic partitions for all **10 SIDRA aggregates** and poll `/periodos` every 3600 seconds in `ibge_new_period_sensor` (`pms_servicos_uf`, `pnad_desocupacao_uf`, `pnad_rendimento_uf`, `ipca_mensal`, `pmc_varejo_uf`, `pib_municipal`, `cempre_municipal`, `cempre_setorial_uf`, `estimativa_populacao`, `censo_populacao`) to add new partitions and trigger runs automatically.
4. **Automated Monthly GitHub Pages Refresh (`.github/workflows/pages.yml`):** Schedule monthly runs (`cron: "0 11 16 * *"` — day 16 after monthly IBGE IPCA/PMC/PMS releases) and persist `.github/last_data_refresh.json` via `record-freshness` (keeping GitHub's 60-day schedule activity timer alive while powering the `<DataFooter />` freshness strip in the BI dashboard).

## Alternatives Considered

### Manually Updated Year Constants per Release
- **Pros:** Zero network metadata calls before ingestion; deterministic offline constants.
- **Cons:** Guarantees staleness whenever IBGE publishes new quarters, years, or monthly revisions until an engineer edits multiple Python and SQL files.
- **Rejected:** High operational toil and silent data freshness lag.

### Unbounded Historical Backfills Starting from 2001/2012
- **Pros:** Longer historical charts.
- **Cons:** Multiplies API calls and hits methodological discontinuities (such as CEMPRE `1685` vs `9509` and pre-2018 macro regimes).
- **Rejected:** Lower signal-to-noise ratio and slower runs; kept bounded via `min_year` (`2018` macro/GDP/PNAD/IPCA, `2020` PMC/PMS, `2022` CEMPRE new series/Census).

## Consequences
- **Zero-touch new period onboarding:** Annual, quarterly, and monthly IBGE publications flow automatically into Bronze, Silver/Gold, and GitHub Pages without code changes.
- **Sensor and offline test safety:** `discover_available_years` requires a reliable HTTP timeout and offline fallback so unit/integration tests in `tests/` remain deterministic without network access.
- **GitHub Actions `record-freshness` trade-off:** Scheduled runs commit `.github/last_data_refresh.json` with `[skip ci]` to record freshness and prevent GitHub from automatically disabling cron workflows after 60 days of repository inactivity.
