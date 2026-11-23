> 🌐 **Language:** [Português (BR)](../../pt-br/guias-praticos/ajustar-ims-e-adicionar-fonte-ibge.md) | **English** · [Index](../README.md)

# How to Tune IMS Weights and Add an IBGE Source

This guide covers two common evolution tasks: recalibrating the **Market Attractiveness Index (`IMS`)** weights and integrating a **new IBGE SIDRA v3 aggregate** end to end.

---

## Recipe 1: Recalibrate IMS Score Weights

The four pillars in `gold.mart_inteligencia_mercado_municipal` are driven by dbt `vars` in `dbt_project/dbt_project.yml`:

```yaml
vars:
  ims_weight_market_size: 0.35
  ims_weight_purchasing_power: 0.30
  ims_weight_dynamism: 0.20
  ims_weight_business_maturity: 0.15
```

### Option A: One-Off CLI Override (Without Editing Files)

To experiment with a calibration skewed toward market size and purchasing power:

```bash
IBGE_BRONZE_DIR="$PWD/data/bronze" IBGE_DUCKDB_PATH="$PWD/data/warehouse/ibge_market_intel.duckdb" \
uv run dbt build \
  --select mart_inteligencia_mercado_municipal \
  --vars '{"ims_weight_market_size": 0.45, "ims_weight_purchasing_power": 0.35, "ims_weight_dynamism": 0.10, "ims_weight_business_maturity": 0.10}' \
  --project-dir dbt_project --profiles-dir dbt_project
```

### Option B: Permanent Project Change

1. Update the weights in `dbt_project/dbt_project.yml` (keep the sum at `1.0` for clarity, though the SQL divides by the active non-null pillar weight sum).
2. Rebuild the mart and validate the singular test `assert_ims_score_bounds_and_distribution`:
   ```bash
   uv run dbt build --select mart_inteligencia_mercado_municipal --project-dir dbt_project --profiles-dir dbt_project
   ```
3. Re-export the Gold Delta tables and inspect the updated ranking:
   ```bash
   uv run dagster asset materialize --select lakehouse/gold_delta_export -m ibge_market_intel.orchestration.definitions
   make inspect-gold
   ```

---

## Recipe 2: Add a New IBGE SIDRA Aggregate

Follow this 7-step checklist to add a new SIDRA survey (for instance, Monthly Services Survey or Municipal Agricultural Production) with full contracts, Dagster lineage, and Delta export:

### Step 1: Inspect Live Metadata on the IBGE API

Check variables, supported territorial levels (`N1`, `N3`, `N6`), classifications, and available periods:

```bash
uv run python -c "
import json, urllib.request
ag = 5457  # example: PAM
with urllib.request.urlopen(f'https://servicodados.ibge.gov.br/api/v3/agregados/{ag}/metadados') as r:
    m = json.loads(r.read())
print(m['nome'], '| levels:', m['nivelTerritorial'])
print('vars:', [(v['id'], v['nome']) for v in m['variaveis'][:5]])
print('classifications:', [(c['id'], c['nome']) for c in m['classificacoes']])
"
```

### Step 2: Declare `AgregadoSpec` and Year Window

In `src/ibge_market_intel/ingestion/catalogs.py`:
- Define the year tuple (e.g., `PAM_YEARS`) and an `AgregadoSpec(...)` instance.
- Set `chunk_by_uf=True` whenever `nivel_territorial == "N6"` with multiple variables to prevent SIDRA backend timeouts.
- Register the spec in `ALL_SIDRA_SPECS`.

### Step 3: Add Partition, Bronze Asset, and Blocking Asset Check

1. In `src/ibge_market_intel/orchestration/partitions.py`, add `StaticPartitionsDefinition(list(PAM_YEARS))`.
2. In `src/ibge_market_intel/orchestration/assets_bronze.py`, define `@asset(key_prefix=["bronze"], name="<table>", ...)` reusing `_ingest_sidra_partition(...)`.
3. Add the asset to `BRONZE_ASSETS` and include the table name in the `_make_sidra_check(...)` tuple inside `BRONZE_ASSET_CHECKS`.
4. To include it in `ibge-pipeline run`, append `(SPEC, YEARS)` to `plan` inside `src/ibge_market_intel/cli.py`.

### Step 4: Register the Delta Source in `bronze_sources.yml`

In `dbt_project/models/bronze_sources.yml`, register the table with the matching Dagster `asset_key`:

```yaml
      - name: <table>
        description: "SIDRA <id>: survey description."
        meta:
          external_location: "delta_scan('{{ env_var('IBGE_BRONZE_DIR', 'data/bronze') }}/<table>')"
          dagster:
            asset_key: ["bronze", "<table>"]
```

### Step 5: Create the Silver Staging Model

Create `dbt_project/models/silver/staging/stg_ibge__<table>.sql`:
- Read from `{{ source('bronze_ibge', '<table>') }}`.
- Parse values using `{{ parse_ibge_value('valor_bruto') }}` and `{{ parse_ibge_status('valor_bruto') }}`.
- Deduplicate on natural keys with `qualify row_number() over (... order by _ingested_at_utc desc) = 1`.
- Add schema tests in `dbt_project/models/silver/staging/_staging.yml`.

### Step 6: Add Gold Model (with Enforced Contract) and Delta Export

1. Create the fact or mart model under `dbt_project/models/gold/facts/` or `marts/`.
2. Declare explicit `data_type` definitions and `config: { contract: { enforced: true } }` in `dbt_project/models/gold/_gold.yml`.
3. Append the model name to `SILVER_EXPORT_TABLES` or `GOLD_EXPORT_TABLES` in `src/ibge_market_intel/orchestration/assets_gold_export.py`.

### Step 7: Verify Lineage and Quality

Run dbt parsing, SQL linting, and the unified Dagster + dbt asset graph check:

```bash
make dbt-parse
make sql-lint
uv run python -c "
from dagster import AssetKey
from ibge_market_intel.orchestration.definitions import defs

ag = defs.resolve_asset_graph()
assert not ag.external_asset_keys, f'Orphan sources: {ag.external_asset_keys}'

bronze_key = AssetKey(['bronze', '<table>'])
gold_key = AssetKey(['gold', '<gold_model>'])
export_key = AssetKey(['lakehouse', 'gold_delta_export'])
assert bronze_key in ag.get_ancestor_asset_keys(gold_key), 'Bronze asset does not reach Gold model'
assert gold_key in ag.get_ancestor_asset_keys(export_key), 'Gold model does not reach Gold Delta export'
print('OK:', len(ag.materializable_asset_keys), 'connected assets with verified end-to-end lineage')
"
```

When `external_asset_keys` is empty **and** the downstream/upstream path assertions pass, your new dataset is verified end to end from Bronze ingestion through Gold modeling to Delta Lake export.
