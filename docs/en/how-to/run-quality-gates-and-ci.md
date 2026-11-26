> 🌐 **Language:** [Português (BR)](../../pt-br/guias-praticos/portoes-de-qualidade-e-ci.md) | **English** · [Index](../README.md) · [ADRs](../../decisions/README.md)

# How to Run Quality Gates and Troubleshoot CI

This guide explains how to run the exact CI quality gates locally, validate the BI layer under DuckDB-WASM emulation, check documentation links/drift, and diagnose common failures.

---

## 1. Run Local Quality Gates

### 1.1 Python & dbt Gates

Run the standard test suite via `Makefile`:

```bash
make test
```

This target runs sequentially:
1. `make lint` — `ruff check src tests` and `ruff format --check src tests`
2. `make typecheck` — `mypy src`
3. `make test-unit` — `pytest tests/unit -v --cov=ibge_market_intel` (`34` unit tests using `respx`, BI guardrails, and realistic IBGE fixtures)
4. `make test-integration` — `pytest tests/integration -v` (`2` E2E integration tests covering offline Medallion pipeline and live BI checks)
5. `make test-dbt` — `dbt parse` + `dbt test --select test_type:unit` (`11` standalone dbt SQL unit tests)

To also run the dbt SQL linter (included in `.github/workflows/ci.yml`):

```bash
make sql-lint
```

### 1.2 3-Layer BI Quality Gate (`dashboard/`)

After exporting BI Parquets (`uv run sidralake export-bi`), validate static contracts, all `78` SQL queries under DuckDB-WASM `DOUBLE` coercion emulation, the Evidence.dev build, and headless Chromium E2E checks (`1440×900`, interactive filter cascades, and `390×844` mobile layout):

```bash
uv run sidralake validate-bi --check-build
cd dashboard && CHROME_PATH=/usr/bin/google-chrome npm run test:e2e
```

### 1.3 Documentation Links, ADRs & Drift Check

```bash
make check-docs
# Strict mode fails if any mapped doc is stale relative to its source code:
uv run python scripts/check_doc_drift.py --strict-drift
```

---

## 2. Diagnose and Resolve Common Failures

### 2.1 Pandera Circuit Breaker Triggered in Bronze

**Symptom:** `ValueError` or `RuntimeError: Circuit Breaker Pandera em bronze/<table> (<year>)` reporting a failure in `BronzeSidraSchema`, `BronzeLocalidadesSchema`, or `BronzeCnaeSchema`.

**Diagnosis and fix:**
- Inspect the reported metrics (`duplicate_key_rows`, `invalid_value_rows`, and `failure case examples`).
- **If `invalid_value_rows > 0`**: IBGE returned an unexpected token in `valor_bruto` outside numbers and `{"-", "..", "...", "X", ""}`. Verify its meaning in `/api/v3/agregados/{id}/metadados` before updating `_IBGE_VALUE_REGEX` in `src/ibge_market_intel/quality/contracts.py` and `dbt_project/macros/parse_ibge_numeric.sql`.
- **If `duplicate_key_rows > 0`**: inspect `flatten_sidra_response` in `src/ibge_market_intel/ingestion/schemas.py` to check whether the aggregate introduced a third classification not captured by `classificacao_1_id`/`classificacao_2_id`.
- **If an API field became nullable**: update the corresponding Pydantic model in `schemas.py` and Pandera field in `contracts.py`.

### 2.2 Broken dbt Enforced Model Contract

**Symptom:** `dbt build` fails on a `dim_*`, `fct_*`, or `mart_*` model with `Contract Error: column mismatch` or `data_type mismatch`.

**Diagnosis and fix:**
- Compare the final `SELECT` in `dbt_project/models/gold/` against the schema declaration in `dbt_project/models/gold/_gold.yml`.
- Models with `contract: { enforced: true }` require explicit `cast(... as <type>)` expressions matching exact column names and types (`varchar`, `integer`, `bigint`, `double`, `date`, `timestamp`, `boolean`) in `_gold.yml`.
- Do not disable `enforced: true`; align the SQL output or make a deliberate, documented contract update.

### 2.3 Singular Accounting or Integrity Test Failure

**Symptom:** failure in one of the 4 tests under `dbt_project/tests/`:
- `assert_pib_contabilidade_consistente.sql` (`|PIB - (VAB_total + Impostos)| > max(5.0, 0.01 * |PIB|)`)
- `assert_vab_setores_soma_total.sql` (`|VAB_total - sum(4 sectors)| > max(5.0, 0.01 * |VAB_total|)`)
- `assert_ims_score_bounds_and_distribution.sql` (`ims_score_0_100` out of `[0, 100]`, `NaN`/`Inf`, or NULL when both GDP and CEMPRE exist)
- `assert_no_orphan_municipios_gold.sql` (municipality in fact tables missing an `is_current = true` row in `dim_geografia`)

**Diagnosis and fix:**
- Query the failing rows directly in DuckDB to inspect offending `codigo_ibge_municipio` and `ano_referencia` keys.
- For orphan municipalities, refresh `bronze/localidades` and run `dbt snapshot` (`snap_ibge_municipios`) before rebuilding facts.

### 2.4 DuckDB File Concurrency Lock Error

**Symptom:** `IO Error: Could not set lock on file ".../ibge_market_intel.duckdb": Conflicting lock is held in /usr/bin/python3.12`.

**Cause and fix:**
- DuckDB allows only **one writer process at a time** on a `.duckdb` file. This happens when `sqlfluff` (dbt templater), `dbt build`, `dagster dev`, or tests run concurrently against the same database file.
- Wait for the other command to complete (or stop the conflicting process) and run write commands sequentially.
- For isolated parallel checks, point `IBGE_DUCKDB_PATH` to a dedicated file:
  ```bash
  IBGE_DUCKDB_PATH=/tmp/ibge_sandbox.duckdb uv run dbt parse --project-dir dbt_project --profiles-dir dbt_project
  ```

### 2.5 BI Guardrail Failure (`validate-bi` or `test:e2e`)

**Symptom:** failure reported by `dashboard_guard.py` (year `.0` formatting, `100x` `_pct` scaling, broken `Dropdown` error badge, or mobile card overflow at `390px`).

**Diagnosis and fix:**
- Ensure integer IDs/years are explicitly cast cleanly against DuckDB-WASM `DOUBLE` coercion (`ADR-003`).
- Follow the BI HTML/CSS invariants in `AGENTS.md` and `ADR-005` (`.sl-chart-head` HTML headers, `minmax(0, 1fr)` grids, `min-inline-size: 0`, and left-aligned mobile menu button).
