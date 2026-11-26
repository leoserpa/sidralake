> 🌐 **Language:** [Português (BR)](../../pt-br/referencia/dicionario-de-dados-lakehouse.md) | **English** · [Index](../README.md) · [ADRs](../../decisions/README.md)

# Reference: Lakehouse Data Dictionary and Inventory

Structural specification of the **Bronze, Silver, and Gold** layers in Delta Lake and DuckDB, enforced dbt model contracts, dbt Semantic Layer, test catalog (`193` data tests + `11` unit tests), and the unified Dagster resource inventory (`49` assets / `204` checks).

---

## 1. Physical Lakehouse Layout (`data/`)

| Path | Contents | Storage Format |
| :--- | :--- | :--- |
| `data/bronze/<table>` | `12` raw tables (SIDRA tables partitioned by `ano_referencia`) | Delta Lake (`_delta_log` + Parquet) |
| `data/silver/<table>` | `4` curated `intermediate` tables exported after `dbt build` | Delta Lake (`_delta_log` + Parquet) |
| `data/gold/<table>` | `16` Gold tables (`4` dimensions, `6` facts, `6` OBT marts) exported after `dbt build` | Delta Lake (`_delta_log` + Parquet) |
| `data/warehouse/ibge_market_intel.duckdb` | Analytical warehouse containing `silver`, `snapshots`, and `gold` (`17` Gold models incl. `time_spine_daily`) | DuckDB (`delta` and `parquet` extensions) |
| `dashboard/parquet_data/<table>.parquet` | `10` BI tables exported as ZSTD Parquet without technical columns (`_`, `sk_*`, SCD2) | ZSTD Parquet (DuckDB-WASM) |

---

## 2. Bronze Layer (Delta Lake — `12` Tables)

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
| `pms_servicos_uf` | `ano_referencia` | `write_partition_overwrite` | `(localidade_id, periodo_id, categoria_1_id, variavel_id)` |
| `pnad_desocupacao_uf` | `ano_referencia` | `write_partition_overwrite` | `(localidade_id, periodo_id, variavel_id)` |
| `pnad_rendimento_uf` | `ano_referencia` | `write_partition_overwrite` | `(localidade_id, periodo_id, categoria_1_id, variavel_id)` |

---

## 3. Silver Layer (`dbt` + Delta Export)

### 3.1 Staging Views (`schema: silver`, materialization: `view` — `12` Models)

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
| `stg_ibge__pms_servicos_uf` | `bronze_ibge.pms_servicos_uf` | `N3` + classification `11046` filter (`56725` `RECEITA_NOMINAL`, `56726` `VOLUME_SERVICOS`) |
| `stg_ibge__pnad_desocupacao_uf` | `bronze_ibge.pnad_desocupacao_uf` | `N3` filter, parses `YYYYQQ` -> `ano_trimestre` / `data_referencia`, deduplication |
| `stg_ibge__pnad_rendimento_uf` | `bronze_ibge.pnad_rendimento_uf` | `N3` + classification `2` (`TOTAL`, `HOMENS`, `MULHERES`) filter for variable `5933` |

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

### 4.1 Dimensions (Enforced Contracts — `5` Models, `4` Exported to Gold Delta)

| Dimension | Grain | Primary Key | Key Attributes |
| :--- | :--- | :--- | :--- |
| `dim_geografia` | SCD2 version of municipality | `sk_municipio` (`varchar`) | `codigo_ibge_municipio`, `nome_municipio`, `codigo_uf`/`sigla_uf`/`nome_uf`, `codigo_regiao`/`sigla_regiao`/`nome_regiao`, `codigo_regiao_imediata`/`nome_regiao_imediata`, `codigo_regiao_intermediaria`/`nome_regiao_intermediaria`, `codigo_microrregiao`/`nome_microrregiao`, `codigo_mesorregiao`/`nome_mesorregiao`, `valid_from`, `valid_to`, `is_current` |
| `dim_tempo` | Month (`2018-01` through current year + 1) | `sk_tempo` (`integer`, `YYYYMM`) | `data_referencia`, `ano_referencia`, `mes_referencia`, `ano_mes`, `trimestre`, `semestre`, `is_ano_censitario` (`year = 2022`) |
| `time_spine_daily` | Day (`2018-01-01` through current year + 1) | `date_day` (`date`) | Daily calendar table required by **dbt Semantic Layer** (not exported separately to Gold Delta) |
| `dim_cnae` | SCD2 version of CNAE section | `sk_cnae_secao` (`varchar`) | `codigo_secao` (`A–U`), `descricao_secao`, `categoria_sidra_12762_id`, `valid_from`, `valid_to`, `is_current` |
| `dim_atividade_varejo` | PMC retail activity | `sk_atividade_varejo` (`varchar`) | `codigo_atividade_pmc`, `nome_atividade_pmc`, `grupo_consumo` (`ALIMENTACAO_ATACAREJO`, `BENS_DURAVEIS_LAR`, `AUTOMOTIVO_CONSTRUCAO`, `COMBUSTIVEIS`, `FARMACIA_VESTUARIO_CONVENIENCIA`) |

### 4.2 Facts (All with Enforced Model Contracts — `6` Tables)

| Fact Table | Grain | Foreign & Natural Keys | Primary Metrics |
| :--- | :--- | :--- | :--- |
| `fct_pib_municipal` | Municipality × Year | `sk_municipio`, `codigo_ibge_municipio`, `ano_referencia` | `pib_nominal_mil_brl`, `pib_real_mil_brl`, `vab_*_mil_brl`, `share_vab_*`, `hhi_setorial`, `indice_diversificacao_setorial`, `crescimento_pib_real_yoy_pct`, `cagr_pib_real_3a_pct` |
| `fct_populacao_municipal` | Municipality × Year | `sk_municipio`, `codigo_ibge_municipio`, `ano_referencia` | `populacao_residente` (`bigint`), `area_km2`, `densidade_demografica`, `origem_dado`, `is_interpolado` |
| `fct_cempre_municipal` | Municipality × Year | `sk_municipio`, `codigo_ibge_municipio`, `ano_referencia` | `num_unidades_locais`, `num_empresas_atuantes`, `pessoal_ocupado_total`, `pessoal_ocupado_assalariado`, `massa_salarial_real_mil_brl`, `salario_medio_real_brl`, `taxa_assalariamento_formal`, YoY growth metrics |
| `fct_cempre_setorial_uf` | State × CNAE Section × Year | `codigo_uf`, `sk_cnae_secao`, `codigo_secao_cnae`, `ano_referencia` | `num_empresas`, `pessoal_ocupado_total`, `pessoal_ocupado_assalariado`, `massa_salarial_nominal_mil_brl`, `massa_salarial_real_mil_brl`, `has_sigilo_estatistico` |
| `fct_ipca_mensal` | Month (`ano_mes`) | `ano_mes` (PK), `ano_referencia`, `mes_referencia`, `data_referencia` | `numero_indice_ipca`, `variacao_mensal_pct`, `variacao_acum_3m_pct`, `variacao_acum_6m_pct`, `variacao_acum_ano_pct`, `variacao_acum_12m_pct`, `ano_mes_base_deflator`, `fator_deflator_base_atual` |
| `fct_pmc_varejo_mensal` | State × Activity × Month | `codigo_uf`, `sk_atividade_varejo`, `codigo_atividade_pmc`, `ano_mes` | `indice_receita_nominal`, `indice_receita_nominal_sa`, `var_mom_sa_receita_pct`, `var_yoy_receita_nominal_pct`, `var_acum_12m_receita_pct`, plus `*_volume_*` equivalents |

### 4.3 Data Marts / OBTs (`gold/marts/*` — `6` OBT Marts)

| Mart OBT | Grain | Key Output Columns | Enums / Tiers |
| :--- | :--- | :--- | :--- |
| `mart_inteligencia_mercado_municipal` | Municipality × Year | `sk_inteligencia_municipal`, `is_ultimo_ano_completo`, `pib_per_capita_real_brl`, `empresas_por_1000_hab`, 4 pillar sub-scores (`score_tamanho_mercado`, `score_poder_compra`, `score_dinamismo`, `score_maturidade_empresarial`), `ims_score_0_100`, `rank_nacional_ims`, `rank_estadual_ims`, `rank_regional_ims`, `tier_mercado` | `Tier 1 - Polo Nacional`, `Tier 2 - Expansao Prioritaria`, `Tier 3 - Emergente`, `Tier 4 - Local / Nicho`, `SEM_CLASSIFICACAO` |
| `mart_clusters_setoriais_uf` | State × CNAE Section × Year | `sk_cluster_setorial`, `quociente_locacional_emprego`, `quociente_locacional_massa_salarial`, `market_share_uf_no_setor_pct`, `crescimento_emprego_setor_yoy_pct`, `has_sigilo_estatistico`, `perfil_especializacao` | `CLUSTER_DOMINANTE` (`>=1.50`), `CLUSTER_ESPECIALIZADO` (`>=1.25`), `EQUILIBRADO_MEDIA_NACIONAL` (`>=0.85`), `SUB_REPRESENTADO`, `SIGILO_OU_INDISPONIVEL` |
| `mart_pulso_consumo_macro` | State × Retail Activity × Month | `sk_pulso_consumo`, `spread_preco_vs_volume_yoy_pp`, `spread_volume_vs_ipca_12m_pp`, `media_movel_3m_volume`, `media_movel_12m_volume`, `ipca_variacao_mensal_pct`, `ipca_variacao_acum_12m_pct`, `regime_consumo` | `EXPANSAO_REAL`, `PRESSAO_INFLACIONARIA`, `ESTABILIDADE`, `RETRACAO`, `SEM_DADO` |
| `mart_pulso_servicos_uf` | State × Month | `sk_pulso_servicos`, `indice_receita_nominal`, `indice_volume_servicos`, `indice_volume_servicos_sa`, `var_mom_sa_volume_pct`, `var_yoy_volume_pct`, `spread_preco_vs_volume_yoy_pp`, `spread_volume_vs_ipca_12m_pp`, `media_movel_3m_volume`, `media_movel_12m_volume`, `regime_servicos` | `EXPANSAO_REAL`, `PRESSAO_INFLACIONARIA`, `ESTABILIDADE`, `RETRACAO`, `SEM_DADO` |
| `mart_mercado_trabalho_uf` | State × Quarter (`ano_trimestre`) | `sk_mercado_trabalho`, `label_trimestre`, `is_ultimo_trimestre`, `taxa_desocupacao_pct`, `taxa_subutilizacao_composta_pct`, `var_yoy_desocupacao_pp`, `rendimento_medio_real_brl`, `rendimento_homens_real_brl`, `rendimento_mulheres_real_brl`, `var_yoy_rendimento_real_pct`, `hiato_salarial_genero_pct` | — |
| `mart_demografia_municipal` | Current Municipality | `codigo_ibge_municipio`, `codigo_regiao_imediata`, `nome_regiao_imediata`, `ano_populacao_atual`, `populacao_atual`, `populacao_censo_2022`, `saldo_populacional_desde_2022`, `crescimento_populacional_desde_2022_pct`, `rank_populacao_uf`, `area_km2`, `densidade_demografica`, `pib_real_mil_brl`, `massa_salarial_real_mil_brl`, `ims_score_0_100` | — |

### 4.4 Semantic Layer (`dbt_project/models/gold/_gold.yml`)

- **`3` semantic models**: `mart_inteligencia_mercado_municipal` (entity `municipio`), `mart_clusters_setoriais_uf` (`cluster_setorial`), and `mart_pulso_consumo_macro` (`pulso_consumo`), anchored on `time_spine_daily`.
- **`12` governed metrics**: `pib_real_total_mil_brl`, `populacao_residente_total`, `massa_salarial_real_total_mil_brl`, `empresas_atuantes_total`, `ims_score_medio`, `pib_real_per_capita_agregado_brl` (derived), `emprego_setorial_total`, `massa_salarial_setorial_real_mil_brl`, `ql_emprego_medio`, `volume_varejo_medio`, `var_yoy_volume_media_pct`, and `spread_preco_volume_medio_pp`.

---

## 5. dbt Tests & Dagster Inventory

### 5.1 dbt Tests (`193` Data Tests + `11` SQL Unit Tests)

- **Singular Tests (`dbt_project/tests/`)**:
  - `assert_pib_contabilidade_consistente.sql`
  - `assert_vab_setores_soma_total.sql`
  - `assert_ims_score_bounds_and_distribution.sql`
  - `assert_no_orphan_municipios_gold.sql`
- **Native dbt Unit Tests (`format: sql`, `11` total)**:
  - **Intermediate Layer (`_intermediate.yml`, `6`)**: `test_populacao_interpolacao_2023`, `test_ipca_deflator_calculo_constante`, `test_pib_deflacao_e_hhi_setorial`, `test_pib_gap_de_ano_e_setores_nulos`, `test_pib_hhi_com_vab_negativo`, `test_cempre_deflacao_e_yoy`.
  - **Gold Layer (`_gold.yml`, `5`)**: `test_quociente_locacional_cluster_especializado`, `test_quociente_locacional_particao_incompleta_retorna_null`, `test_pulso_consumo_regimes_e_spread`, `test_ims_score_tiers_e_ranking`, `test_mart_demografia_municipal`.

### 5.2 Unified Dagster Inventory (`src/ibge_market_intel/orchestration/definitions.py`)

- **Assets**: `49` materializable assets (`0` orphan external assets) grouped into `bronze`, `silver_staging`, `silver_scd2`, `silver_intermediate`, `gold_dimensions`, `gold_facts`, `gold_marts`, and `lakehouse_export`.
- **Asset Checks**: `204` total checks (`12` blocking Pandera checks in Bronze + `192` dbt checks).
- **Jobs**: `dbt_medallion_job`, `macro_refresh_job`, `delta_maintenance_job`.
- **Sensor**: `ibge_new_period_sensor` (`minimum_interval_seconds=3600`, polls `/periodos` across all 10 SIDRA sources — `ipca_mensal`, `pmc_varejo_uf`, `pms_servicos_uf`, `pnad_desocupacao_uf`, `pnad_rendimento_uf`, `pib_municipal`, `cempre_municipal`, `cempre_setorial_uf`, `estimativa_populacao`, and `censo_populacao` — registering new years via `DynamicPartitionsDefinition`).
- **Schedules (`America/Sao_Paulo`)**:
  - `monthly_macro_refresh_schedule`: cron `0 8 15 * *` (runs `macro_refresh_job`)
  - `weekly_delta_maintenance_schedule`: cron `0 3 * * 0` (runs `delta_maintenance_job`)
