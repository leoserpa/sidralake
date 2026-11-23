> 🌐 **Language:** [Português (BR)](../../pt-br/referencia/dicionario-de-dados-lakehouse.md) | **English** · [Index](../README.md)

# Reference: Lakehouse Data Dictionary and Inventory

Structural specification of the **Bronze, Silver, and Gold** layers in Delta Lake and DuckDB, enforced dbt model contracts, test catalog, and the unified Dagster resource inventory.

---

## 1. Physical Lakehouse Layout (`data/`)

| Path | Contents | Storage Format |
| :--- | :--- | :--- |
| `data/bronze/<table>` | 9 raw tables (SIDRA tables partitioned by `ano_referencia`) | Delta Lake (`_delta_log` + Parquet) |
| `data/silver/<table>` | 4 curated `intermediate` tables exported after `dbt build` | Delta Lake (`_delta_log` + Parquet) |
| `data/gold/<table>` | 13 Gold tables (4 dimensions, 6 facts, 3 OBT marts) exported after `dbt build` | Delta Lake (`_delta_log` + Parquet) |
| `data/warehouse/ibge_market_intel.duckdb` | Analytical warehouse containing `silver`, `snapshots`, and `gold` schemas | DuckDB (`delta` and `parquet` extensions) |

---

## 2. Bronze Layer (Delta Lake)

| Table (`data/bronze/*`) | Partitioning | Write Mode | Grain |
| :--- | :--- | :--- | :--- |
| `localidades` | Unpartitioned | `write_full_overwrite` | 1 row per `municipio_id` (`5,571` municipalities) |
| `cnae_secoes` | Unpartitioned | `write_full_overwrite` | 1 row per `secao_codigo` (`21` sections `A–U`) |
| `pib_municipal` | `ano_referencia` | `write_partition_overwrite` | `(localidade_id, ano_referencia, variavel_id)` |
| `censo_populacao` | `ano_referencia` | `write_partition_overwrite` | `(localidade_id, ano_referencia, variavel_id)` |
| `estimativa_populacao` | `ano_referencia` | `write_partition_overwrite` | `(localidade_id, ano_referencia, variavel_id)` |
| `cempre_municipal` | `ano_referencia` | `write_partition_overwrite` | `(localidade_id, ano_referencia, variavel_id)` |
| `cempre_setorial_uf` | `ano_referencia` | `write_partition_overwrite` | `(localidade_id, ano_referencia, categoria_1_id, variavel_id)` |
| `ipca_mensal` | `ano_referencia` | `write_partition_overwrite` | `(periodo_id, variavel_id)` |
| `pmc_varejo_uf` | `ano_referencia` | `write_partition_overwrite` | `(localidade_id, periodo_id, categoria_1_id, categoria_2_id, variavel_id)` |

---

## 3. Silver Layer (`dbt` + Delta Export)

### 3.1 Staging Views (`schema: silver`, materialization: `view`)

| Model | Bronze Source | Applied Transformations |
| :--- | :--- | :--- |
| `stg_ibge__localidades` | `bronze_ibge.localidades` | Strict casting and deduplication by `municipio_id` (`_ingested_at_utc desc`) |
| `stg_ibge__cnae_secoes` | `bronze_ibge.cnae_secoes` | Uppercase `codigo_secao` normalization and deduplication |
| `stg_ibge__pib_municipal` | `bronze_ibge.pib_municipal` | `N6` filter, `parse_ibge_value`, `parse_ibge_status`, deduplication |
| `stg_ibge__censo_populacao` | `bronze_ibge.censo_populacao` | Pivots population (`93`), area (`6318`), and density (`614`) |
| `stg_ibge__estimativa_populacao` | `bronze_ibge.estimativa_populacao` | Casting and filtering of variable `9324` (`N6`) |
| `stg_ibge__cempre_municipal` | `bronze_ibge.cempre_municipal` | `N6` filter, IBGE token parsing, deduplication |
| `stg_ibge__cempre_setorial_uf` | `bronze_ibge.cempre_setorial_uf` | `N3` + classification `12762` filter, extracts `codigo_secao_cnae` |
| `stg_ibge__ipca_mensal` | `bronze_ibge.ipca_mensal` | Pivots all 6 IPCA variables (`2266`, `63`, `2263`, `2264`, `69`, `2265`) |
| `stg_ibge__pmc_varejo_uf` | `bronze_ibge.pmc_varejo_uf` | Maps `tipo_indice` (`RECEITA_NOMINAL`/`VOLUME_VENDAS`) and activity (`85`) |

### 3.2 SCD Type 2 Snapshots (`schema: snapshots`)

| Snapshot | Source Model | Unique Key | Strategy & Monitored Columns (`check_cols`) |
| :--- | :--- | :--- | :--- |
| `snap_ibge_municipios` | `stg_ibge__localidades` | `codigo_ibge_municipio` | `check` + `invalidate_hard_deletes=True` on `nome_municipio`, `sigla_uf`, `nome_uf`, `nome_regiao_imediata`, `nome_regiao_intermediaria` |
| `snap_ibge_cnae_secoes` | `stg_ibge__cnae_secoes` | `codigo_secao` | `check` + `invalidate_hard_deletes=True` on `descricao_secao`, `categoria_sidra_12762_id`, `observacoes` |

### 3.3 Intermediate Tables (`schema: silver`, exported to `data/silver/*`)

| Model | Grain | Key Output Columns |
| :--- | :--- | :--- |
| `int_populacao_municipal_unificada` | `(codigo_ibge_municipio, ano_referencia)` | `populacao_residente`, `area_km2`, `densidade_demografica`, `origem_dado` (`CENSO_2022` \| `ESTIMATIVA_IBGE` \| `INTERPOLACAO_LINEAR`), `is_interpolado` |
| `int_ipca_deflator_anual` | `ano_referencia` | `ano_mes_base_deflator`, `numero_indice_medio_anual`, `fator_deflator_anual`, `meses_observados_no_ano` |
| `int_pib_municipal_deflacionado` | `(codigo_ibge_municipio, ano_referencia)` | `pib_nominal_mil_brl`, `pib_real_mil_brl`, `impostos_liquidos_mil_brl`, 4 `vab_*_mil_brl`, 4 `share_vab_*`, `hhi_setorial`, `indice_diversificacao_setorial`, `crescimento_pib_real_yoy_pct`, `cagr_pib_real_3a_pct` |
| `int_cempre_municipal_deflacionado` | `(codigo_ibge_municipio, ano_referencia)` | `num_unidades_locais`, `num_empresas_atuantes`, `pessoal_ocupado_total`, `pessoal_ocupado_assalariado`, `pessoal_assalariado_medio`, `massa_salarial_nominal_mil_brl`, `massa_salarial_real_mil_brl`, `salario_medio_sm`, `salario_medio_nominal_brl`, `salario_medio_real_brl`, `taxa_assalariamento_formal`, `crescimento_empresas_yoy_pct`, `crescimento_emprego_yoy_pct` |

---

## 4. Gold Layer (`schema: gold` + `data/gold/*`)

### 4.1 Dimensions (All with Enforced Model Contracts)

| Dimension | Grain | Primary Key (`sk_*`) | Key Attributes |
| :--- | :--- | :--- | :--- |
| `dim_geografia` | SCD2 version of municipality | `sk_municipio` (`varchar`) | `codigo_ibge_municipio`, `nome_municipio`, `codigo_uf`/`sigla_uf`/`nome_uf`, `codigo_regiao`/`sigla_regiao`/`nome_regiao`, `codigo_regiao_imediata`/`nome_regiao_imediata`, `codigo_regiao_intermediaria`/`nome_regiao_intermediaria`, `codigo_microrregiao`/`nome_microrregiao`, `codigo_mesorregiao`/`nome_mesorregiao`, `valid_from`, `valid_to`, `is_current` |
| `dim_tempo` | Month (`2018-01` to `2026-12`) | `sk_tempo` (`integer`, `YYYYMM`) | `data_referencia`, `ano_referencia`, `mes_referencia`, `ano_mes`, `trimestre`, `semestre`, `is_ano_censitario` (`year = 2022`) |
| `dim_cnae` | SCD2 version of CNAE section | `sk_cnae_secao` (`varchar`) | `codigo_secao` (`A–U`), `descricao_secao`, `categoria_sidra_12762_id`, `valid_from`, `valid_to`, `is_current` |
| `dim_atividade_varejo` | PMC retail activity | `sk_atividade_varejo` (`varchar`) | `codigo_atividade_pmc`, `nome_atividade_pmc`, `grupo_consumo` (`ALIMENTACAO_ATACAREJO`, `BENS_DURAVEIS_LAR`, `AUTOMOTIVO_CONSTRUCAO`, `COMBUSTIVEIS`, `FARMACIA_VESTUARIO_CONVENIENCIA`) |

### 4.2 Facts (All with Enforced Model Contracts)

| Fact Table | Grain | Foreign & Natural Keys | Primary Metrics |
| :--- | :--- | :--- | :--- |
| `fct_pib_municipal` | Municipality × Year | `sk_municipio`, `codigo_ibge_municipio`, `ano_referencia` | `pib_nominal_mil_brl`, `pib_real_mil_brl`, `vab_*_mil_brl`, `share_vab_*`, `hhi_setorial`, `indice_diversificacao_setorial`, `crescimento_pib_real_yoy_pct`, `cagr_pib_real_3a_pct` |
| `fct_populacao_municipal` | Municipality × Year | `sk_municipio`, `codigo_ibge_municipio`, `ano_referencia` | `populacao_residente` (`bigint`), `area_km2`, `densidade_demografica`, `origem_dado`, `is_interpolado` |
| `fct_cempre_municipal` | Municipality × Year | `sk_municipio`, `codigo_ibge_municipio`, `ano_referencia` | `num_unidades_locais`, `num_empresas_atuantes`, `pessoal_ocupado_total`, `pessoal_ocupado_assalariado`, `massa_salarial_real_mil_brl`, `salario_medio_real_brl`, `taxa_assalariamento_formal`, YoY growth metrics |
| `fct_cempre_setorial_uf` | State × CNAE Section × Year | `codigo_uf`, `sk_cnae_secao`, `codigo_secao_cnae`, `ano_referencia` | `num_empresas`, `pessoal_ocupado_total`, `pessoal_ocupado_assalariado`, `massa_salarial_nominal_mil_brl`, `massa_salarial_real_mil_brl`, `has_sigilo_estatistico` |
| `fct_ipca_mensal` | Month (`ano_mes`) | `ano_mes` (PK), `ano_referencia`, `mes_referencia`, `data_referencia` | `numero_indice_ipca`, `variacao_mensal_pct`, `variacao_acum_3m_pct`, `variacao_acum_6m_pct`, `variacao_acum_ano_pct`, `variacao_acum_12m_pct`, `ano_mes_base_deflator`, `fator_deflator_base_atual` |
| `fct_pmc_varejo_mensal` | State × Activity × Month | `codigo_uf`, `sk_atividade_varejo`, `codigo_atividade_pmc`, `ano_mes` | `indice_receita_nominal`, `indice_receita_nominal_sa`, `var_mom_sa_receita_pct`, `var_yoy_receita_nominal_pct`, `var_acum_12m_receita_pct`, plus `*_volume_*` equivalents |

### 4.3 Data Marts / OBTs (`gold/marts/*`)

| Mart OBT | Grain | Key Output Columns | Enums / Tiers |
| :--- | :--- | :--- | :--- |
| `mart_inteligencia_mercado_municipal` | Municipality × Year | `sk_inteligencia_municipal`, `is_ultimo_ano_completo`, `pib_per_capita_real_brl`, `empresas_por_1000_hab`, 4 pillar sub-scores (`score_tamanho_mercado`, `score_poder_compra`, `score_dinamismo`, `score_maturidade_empresarial`), `ims_score_0_100`, `rank_nacional_ims`, `rank_estadual_ims`, `rank_regional_ims`, `tier_mercado` | `Tier 1 - Polo Nacional`, `Tier 2 - Expansao Prioritaria`, `Tier 3 - Emergente`, `Tier 4 - Local / Nicho`, `SEM_CLASSIFICACAO` |
| `mart_clusters_setoriais_uf` | State × CNAE Section × Year | `sk_cluster_setorial`, `quociente_locacional_emprego`, `quociente_locacional_massa_salarial`, `market_share_uf_no_setor_pct`, `crescimento_emprego_setor_yoy_pct`, `has_sigilo_estatistico`, `perfil_especializacao` | `CLUSTER_DOMINANTE` (`>=1.50`), `CLUSTER_ESPECIALIZADO` (`>=1.25`), `EQUILIBRADO_MEDIA_NACIONAL` (`>=0.85`), `SUB_REPRESENTADO`, `SIGILO_OU_INDISPONIVEL` |
| `mart_pulso_consumo_macro` | State × Retail Activity × Month | `sk_pulso_consumo`, `spread_preco_vs_volume_yoy_pp`, `spread_volume_vs_ipca_12m_pp`, `media_movel_3m_volume`, `media_movel_12m_volume`, `ipca_variacao_mensal_pct`, `ipca_variacao_acum_12m_pct`, `regime_consumo` | `EXPANSAO_REAL`, `PRESSAO_INFLACIONARIA`, `ESTABILIDADE`, `RETRACAO`, `SEM_DADO` |

---

## 5. dbt Tests & Dagster Inventory

### 5.1 dbt Tests (`147` Data Tests + `4` Unit Tests)

- **Singular Tests (`dbt_project/tests/`)**:
  - `assert_pib_contabilidade_consistente.sql`
  - `assert_vab_setores_soma_total.sql`
  - `assert_ims_score_bounds_and_distribution.sql`
  - `assert_no_orphan_municipios_gold.sql`
- **Native dbt Unit Tests (`format: sql`)**:
  - `test_populacao_interpolacao_2023` (`int_populacao_municipal_unificada`)
  - `test_ipca_deflator_calculo_constante` (`int_ipca_deflator_anual`)
  - `test_pib_deflacao_e_hhi_setorial` (`int_pib_municipal_deflacionado`)
  - `test_quociente_locacional_cluster_especializado` (`mart_clusters_setoriais_uf`)

### 5.2 Unified Dagster Inventory (`src/ibge_market_intel/orchestration/definitions.py`)

- **Assets**: `39` materializable assets (`0` orphan external assets) grouped into `bronze`, `silver_staging`, `silver_scd2`, `silver_intermediate`, `gold_dimensions`, `gold_facts`, `gold_marts`, and `lakehouse_export`.
- **Asset Checks**: `155` total checks (`9` blocking Pandera checks in Bronze + `146` dbt checks).
- **Jobs**: `dbt_medallion_job`, `macro_refresh_job`, `delta_maintenance_job`.
- **Sensor**: `ibge_new_period_sensor` (`minimum_interval_seconds=3600`, polls `/periodos` for `ipca_mensal`, `pmc_varejo_uf`, `pib_municipal`, and `cempre_municipal`).
- **Schedules (`America/Sao_Paulo`)**:
  - `monthly_macro_refresh_schedule`: cron `0 8 15 * *` (runs `macro_refresh_job`)
  - `weekly_delta_maintenance_schedule`: cron `0 3 * * 0` (runs `delta_maintenance_job`)
