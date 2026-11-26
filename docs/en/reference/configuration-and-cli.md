> 🌐 **Language:** [Português (BR)](../../pt-br/referencia/configuracao-e-cli.md) | **English** · [Index](../README.md) · [ADRs](../../decisions/README.md)

# Reference: Configuration, CLI, and Environment

Technical specification of the CLI commands, `Makefile` targets, environment variables (`PipelineSettings`), `dbt-duckdb` profiles, and CI/Pages workflows.

---

## 1. `sidralake` CLI (and `ibge-pipeline` alias)

Defined in [`src/ibge_market_intel/cli.py`](../../../src/ibge_market_intel/cli.py) and registered in `pyproject.toml` (`[project.scripts]`).

```bash
uv run sidralake <subcommand> [options]
```

| Command | Options | Behavior |
| :--- | :--- | :--- |
| `sidralake run` | `--mode {smoke,full}` (default: `full`) | Runs the full pipeline: async IBGE ingestion + Pandera validation → Bronze Delta → `dbt build` → ACID Silver & Gold Delta Lake export. In `--mode smoke`, defaults `uf_filter` to `[35, 51]` (unless `IBGE_UF_FILTER` is set) and uses a compact year range. |
| `sidralake maintain` | — | Iterates over `data/bronze/`, `data/silver/`, and `data/gold/`, running `OPTIMIZE` (`compact()`) and `VACUUM` (`retention_hours=168`, `dry_run=False`) on every Delta table. |
| `sidralake inspect` | — | Runs 6 analytical sanity-check queries against DuckDB and Gold Delta Lake (Top 15 IMS Score, Tier distribution, *Boa Esperança do Norte* verification, Top 10 CNAE clusters by LQ, PMC × IPCA pulse, and `_delta_log` table versions). |
| `sidralake insights` | `--top N`, `--uf CODE`, `--year YEAR` | Runs one-shot analytical queries via **Polars Lazy API (`pl.scan_delta`)** directly over Gold Delta Lake Marts (Top municipalities by IMS, fastest 3-year real GDP CAGR, state CNAE clusters, and retail consumption pulse by regime). |
| `sidralake export-bi` | `--output-dir PATH`, `--freshness-file PATH` | Exports all `10` BI tables (`BI_GOLD_TABLES`) to **ZSTD** Parquet (`dashboard/parquet_data/`), filtering `dim_geografia`/`dim_cnae` to `is_current`, stripping `_`, `sk_*`, and technical SCD2 columns, sorting by `("ano_referencia", "data_referencia", "sigla_uf")`, and optionally writing the JSON freshness manifest. |
| `sidralake validate-bi` | `--parquet-dir PATH`, `--check-build`, `--build-dir PATH`, `--allow-empty` | Enforces static BI contracts (`dashboard_guard.py`), validates all **78 SQL queries** under DuckDB-WASM `DOUBLE` coercion emulation (`--allow-empty` allows 0 rows in smoke runs), and with `--check-build` validates static output under `dashboard/build/`. |
| `sidralake test` | — | Runs the full local quality suite (`ruff`, `mypy --strict`, `pytest` unit + E2E, `dbt parse`, and all `11` dbt SQL unit tests). |

---

## 2. `Makefile` Targets

Defined in [`Makefile`](../../../Makefile):

| Target | Underlying Command | Description |
| :--- | :--- | :--- |
| `make setup` | `uv sync --dev` + `uv run dbt deps ...` | Creates `.venv/` and installs Python + `dbt-labs/dbt_utils` dependencies. |
| `make lint` | `ruff check src tests` + `ruff format --check src tests` | Checks Python lint and formatting. |
| `make format` | `ruff format src tests` + `ruff check --fix src tests` | Auto-formats and auto-fixes Python code. |
| `make typecheck` | `uv run mypy src` | Runs static type checking across `src/`. |
| `make sql-lint` | `uv run sqlfluff lint dbt_project/models dbt_project/macros dbt_project/tests` | Lints dbt SQL files (`duckdb` dialect, `dbt` templater). |
| `make check-docs` | `uv run python scripts/check_doc_drift.py` | Verifies relative Markdown links, ADR structure, and git-ancestry doc drift. |
| `make test-unit` | `uv run pytest tests/unit -v --cov=ibge_market_intel` | Runs `34` Python unit tests with coverage. |
| `make test-integration` | `uv run pytest tests/integration -v` | Runs `2` E2E integration tests (offline Medallion E2E and live BI integration where applicable). |
| `make test-dbt` | `dbt parse` + `dbt test --select test_type:unit` | Parses the dbt project and runs all `11` YAML-defined dbt SQL unit tests (`unit_tests:` in `_intermediate.yml` and `_gold.yml`). Does **not** run singular data tests in `dbt_project/tests/`; to run singular assertions after building models, run `uv run dbt test --select test_type:singular --project-dir dbt_project --profiles-dir dbt_project` (or `make dbt-build`). |
| `make test` | `lint` + `typecheck` + `test-unit` + `test-integration` + `test-dbt` | Runs the complete standard quality suite. |
| `make dbt-deps` | `uv run dbt deps --project-dir dbt_project --profiles-dir dbt_project` | Installs dbt packages (`packages.yml`). |
| `make dbt-parse` | `uv run dbt parse ...` | Compiles `manifest.json` without executing queries. |
| `make dbt-build` | `uv run dbt build ...` | Builds snapshots, Silver/Gold models, `193` data tests, and `11` unit tests. |
| `make dbt-docs` | `dbt docs generate` + `dbt docs serve --port 8080` | Generates and serves interactive dbt Docs on port `8080`. |
| `make dagster-dev` | `DAGSTER_HOME="$(CURDIR)/.dagster" uv run dagster dev` | Starts local Dagster webserver and daemon. |
| `make materialize-smoke` | `uv run ibge-pipeline run --mode smoke` | Fast end-to-end SP/MT smoke execution. |
| `make materialize-full` | `uv run ibge-pipeline run --mode full` | Full Brazil execution (5,571 municipalities). |
| `make delta-maintenance` | `uv run ibge-pipeline maintain` | Runs `OPTIMIZE` and `VACUUM` on all Delta tables. |
| `make inspect-gold` | `uv run ibge-pipeline inspect` | Prints Gold analytical metrics to stdout. |

---

## 3. Environment Variables (`PipelineSettings`)

Loaded via `pydantic-settings` (`env_prefix="IBGE_"`, optional UTF-8 `.env` file) in [`src/ibge_market_intel/config.py`](../../../src/ibge_market_intel/config.py):

| Environment Variable | Type | Default | Description / Constraints |
| :--- | :--- | :--- | :--- |
| `IBGE_PROJECT_ROOT` | `Path` | Repository root directory | Root directory used to resolve default relative paths. |
| `IBGE_DATA_DIR` | `Path \| None` | `<project_root>/data` | Local Lakehouse root (`resolved_data_dir`). |
| `IBGE_BRONZE_DIR` | `Path \| None` | `<data_dir>/bronze` | Bronze Delta Lake directory (`resolved_bronze_dir`). |
| `IBGE_SILVER_DIR` | `Path \| None` | `<data_dir>/silver` | Exported Silver Delta Lake directory (`resolved_silver_dir`). |
| `IBGE_GOLD_DIR` | `Path \| None` | `<data_dir>/gold` | Exported Gold Delta Lake directory (`resolved_gold_dir`). |
| `IBGE_DUCKDB_PATH` | `Path \| None` | `<data_dir>/warehouse/ibge_market_intel.duckdb` | DuckDB warehouse file (`resolved_duckdb_path`). |
| `IBGE_DBT_PROJECT_DIR` | `Path \| None` | `<project_root>/dbt_project` | Path to the dbt project (`resolved_dbt_project_dir`). |
| `IBGE_IBGE_BASE_URL` | `str` | `https://servicodados.ibge.gov.br/api` | Base URL for IBGE REST services. |
| `IBGE_MAX_CONCURRENCY` | `int` | `6` | `asyncio.Semaphore` concurrency cap (`1 <= x <= 20`). |
| `IBGE_REQUEST_TIMEOUT_S` | `float` | `40.0` | Per-request HTTP timeout in seconds (`5.0 <= x <= 180.0`). |
| `IBGE_RETRY_MAX_ATTEMPTS` | `int` | `5` | Max retry attempts with exponential jitter backoff (`1 <= x <= 10`). |
| `IBGE_USER_AGENT` | `str` | `ibge-market-intel/0.1.0 (+data-engineering-lakehouse)` | `User-Agent` HTTP header sent to IBGE endpoints. |
| `IBGE_LOG_FORMAT` | `str` | `json` | `structlog` renderer format: `json` or `console`. |
| `IBGE_LOG_LEVEL` | `str` | `INFO` | Minimum log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `IBGE_UF_FILTER` | `list[int] \| None` | `None` | Optional JSON list of IBGE UF state codes (e.g., `[35, 51]`). |

> **Note on `IBGE_IBGE_BASE_URL`:** Because the Pydantic field is named `ibge_base_url` with `env_prefix="IBGE_"`, the resolved environment variable name is `IBGE_IBGE_BASE_URL`.

---

## 4. `dbt-duckdb` Configuration

### `dbt_project/profiles.yml`

| Target | DuckDB Path | Threads | Loaded Extensions | Settings |
| :--- | :--- | :---: | :--- | :--- |
| `dev` (default) | `{{ env_var('IBGE_DUCKDB_PATH', 'data/warehouse/ibge_market_intel.duckdb') }}` | `4` | `delta`, `parquet` | `preserve_insertion_order: false` |
| `ci` | `{{ env_var('IBGE_DUCKDB_PATH', '/tmp/ibge_market_intel_ci.duckdb') }}` | `2` | `delta`, `parquet` | — |

### Variables & Materializations (`dbt_project/dbt_project.yml`)

- **Custom schema names**: `dbt_project/macros/generate_schema_name.sql` strips default target-schema prefixes, keeping clean schema names: `silver`, `snapshots`, and `gold`.
- **Default materializations**:
  - `models.ibge_market_intel.silver.staging`: `view` (tags: `silver`, `staging`)
  - `models.ibge_market_intel.silver.intermediate`: `table` (tags: `silver`, `intermediate`)
  - `snapshots.ibge_market_intel`: `target_schema: snapshots` (tags: `silver`, `scd2`)
  - `models.ibge_market_intel.gold.dimensions`: `table` (tags: `gold`, `dimension`)
  - `models.ibge_market_intel.gold.facts`: `table` (tags: `gold`, `fact`)
  - `models.ibge_market_intel.gold.marts`: `table` (tags: `gold`, `mart`, `obt`)
- **IMS Score Weights (`vars`)**:
  - `ims_weight_market_size`: `0.35`
  - `ims_weight_purchasing_power`: `0.30`
  - `ims_weight_dynamism`: `0.20`
  - `ims_weight_business_maturity`: `0.15`

---

## 5. GitHub Actions Workflows

### 5.1 CI Pipeline ([`.github/workflows/ci.yml`](../../../.github/workflows/ci.yml))

Triggered on `push` (`main`, `master`) and all `pull_request` events on `ubuntu-latest`:

1. Installs `uv` with Python `3.12` (`astral-sh/setup-uv@v5`).
2. Runs `uv sync --dev` and `dbt deps`.
3. Runs `ruff check src tests` and `ruff format --check src tests`.
4. Runs `mypy src`.
5. Runs `dbt parse` and `dbt test --select test_type:unit` (`11` SQL unit tests).
6. Runs `sqlfluff lint dbt_project/models dbt_project/macros dbt_project/tests`.
7. Runs `pytest tests -v --cov=ibge_market_intel`.

### 5.2 Continuous BI Build & GitHub Pages Deploy ([`.github/workflows/pages.yml`](../../../.github/workflows/pages.yml))

Triggered on `push` to `main` (touching `dashboard/**`, `dbt_project/**`, `src/ibge_market_intel/**`, or `pages.yml`), monthly cron schedule (`0 11 16 * *` — day 16 following IPCA/PMC/PMS monthly releases), or manual `workflow_dispatch` (`mode: full | smoke`):

1. Materializes the full Lakehouse (`uv run sidralake run --mode "$SIDRALAKE_MODE"`) and exports 10 ZSTD Parquets + `.github/last_data_refresh.json` (`uv run sidralake export-bi --freshness-file .github/last_data_refresh.json`).
2. Runs pre-build BI gate (`uv run sidralake validate-bi` and `pytest tests/unit/test_dashboard_integrity.py tests/integration/test_dashboard_live_data.py`).
3. Installs Node dependencies and compiles static Evidence.dev output (`npm install && npm run sources:strict && npm run build && touch build/.nojekyll`).
4. Runs post-build artifact checks (`uv run sidralake validate-bi --check-build`) and headless Chromium E2E checks (`npm --prefix dashboard run test:e2e` covering all 9 routes at `1440×900`, interactive filter cascades, and `390×844` mobile layout).
5. Deploys `dashboard/build` to GitHub Pages and, on scheduled runs (`record-freshness`), commits `.github/last_data_refresh.json` with `[skip ci]`. See [`ADR-004`](../../decisions/ADR-004-dynamic-period-discovery-and-dagster-partitions.md).
