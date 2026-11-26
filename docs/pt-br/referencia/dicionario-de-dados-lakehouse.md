> 🌐 **Idioma:** **Português (BR)** | [English](../../en/reference/data-dictionary-lakehouse.md) · [Índice](../README.md) · [ADRs](../../decisions/README.md)

# Referência: Dicionário de Dados e Inventário do Lakehouse

Inventário estrutural das camadas **Bronze, Silver e Gold** em Delta Lake e DuckDB, contratos *enforced*, camada semântica dbt, catálogo de testes (`193` testes de dados + `11` unit tests) e recursos do grafo unificado Dagster (`49` ativos / `204` checks).

---

## 1. Layout Físico do Lakehouse (`data/`)

| Caminho | Conteúdo | Formato |
| :--- | :--- | :--- |
| `data/bronze/<table>` | `12` tabelas brutas particionadas (tabelas SIDRA particionadas por `ano_referencia`) | Delta Lake (`_delta_log` + Parquet) |
| `data/silver/<table>` | `4` tabelas `intermediate` curadas exportadas após o `dbt build` | Delta Lake (`_delta_log` + Parquet) |
| `data/gold/<table>` | `16` tabelas Gold (`4` dimensões, `6` fatos e `6` marts OBT) exportadas após o `dbt build` | Delta Lake (`_delta_log` + Parquet) |
| `data/warehouse/ibge_market_intel.duckdb` | Warehouse analítico com schemas `silver`, `snapshots` e `gold` (`17` modelos Gold incluindo `time_spine_daily`) | DuckDB (extensões `delta`, `parquet`) |
| `dashboard/parquet_data/<table>.parquet` | `10` tabelas BI exportadas em Parquet ZSTD sem colunas técnicas (`_`, `sk_*`, SCD2) | Parquet ZSTD (DuckDB-WASM) |

---

## 2. Camada Bronze (Delta Lake — `12` Tabelas)

| Tabela (`data/bronze/*`) | Particionamento | Modo de Escrita | Grão |
| :--- | :--- | :--- | :--- |
| `localidades` | Não particionada | `write_full_overwrite` | 1 linha por `municipio_id` (`5.571` municípios) |
| `cnae_secoes` | Não particionada | `write_full_overwrite` | 1 linha por `secao_codigo` (`21` seções `A–U`) |
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

## 3. Camada Silver (`dbt` + Exportação Delta)

### 3.1 Views de Preparação (*Staging*, `schema: silver`, materialização: `view` — `12` Modelos)

| Modelo | Fonte Bronze | Transformações Aplicadas |
| :--- | :--- | :--- |
| `stg_ibge__localidades` | `bronze_ibge.localidades` | Tipagem estrita e deduplicação por `municipio_id` (`_ingested_at_utc desc`) |
| `stg_ibge__cnae_secoes` | `bronze_ibge.cnae_secoes` | Padronização `codigo_secao` e deduplicação |
| `stg_ibge__pib_municipal` | `bronze_ibge.pib_municipal` | Filtro `N6`, `parse_ibge_value`, `parse_ibge_status` e deduplicação |
| `stg_ibge__censo_populacao` | `bronze_ibge.censo_populacao` | Pivot de população (`93`), área (`6318`) e densidade (`614`) |
| `stg_ibge__estimativa_populacao` | `bronze_ibge.estimativa_populacao` | Tipagem e extração da variável `9324` (`N6`) |
| `stg_ibge__cempre_municipal` | `bronze_ibge.cempre_municipal` | Filtro `N6`, conversão semântica IBGE e deduplicação |
| `stg_ibge__cempre_setorial_uf` | `bronze_ibge.cempre_setorial_uf` | Filtro `N3` + classificação `12762`, extração de `codigo_secao_cnae` |
| `stg_ibge__ipca_mensal` | `bronze_ibge.ipca_mensal` | Pivot das 6 variáveis do IPCA (`2266`, `63`, `2263`, `2264`, `69`, `2265`) |
| `stg_ibge__pmc_varejo_uf` | `bronze_ibge.pmc_varejo_uf` | Mapeamento de `tipo_indice` (`RECEITA_NOMINAL`/`VOLUME_VENDAS`) e atividade (`85`) |
| `stg_ibge__pms_servicos_uf` | `bronze_ibge.pms_servicos_uf` | Filtro `N3` + classificação `11046` (`56725` `RECEITA_NOMINAL`, `56726` `VOLUME_SERVICOS`) |
| `stg_ibge__pnad_desocupacao_uf` | `bronze_ibge.pnad_desocupacao_uf` | Filtro `N3`, conversão `YYYYQQ` -> `ano_trimestre` / `data_referencia` e deduplicação |
| `stg_ibge__pnad_rendimento_uf` | `bronze_ibge.pnad_rendimento_uf` | Filtro `N3` + classificação `2` (`TOTAL`, `HOMENS`, `MULHERES`) para variável `5933` |

### 3.2 Snapshots SCD Tipo 2 (`schema: snapshots`)

| Snapshot | Modelo Fonte | Chave Única | Estratégia & Colunas Monitoradas (`check_cols`) |
| :--- | :--- | :--- | :--- |
| `snap_ibge_municipios` | `stg_ibge__localidades` | `codigo_ibge_municipio` | `check` + `invalidate_hard_deletes=True` em `nome_municipio`, `sigla_uf`, `nome_uf`, `nome_regiao_imediata`, `nome_regiao_intermediaria` |
| `snap_ibge_cnae_secoes` | `stg_ibge__cnae_secoes` | `codigo_secao` | `check` + `invalidate_hard_deletes=True` em `descricao_secao`, `categoria_sidra_12762_id`, `observacoes` |

### 3.3 Tabelas Intermediárias (*Intermediate*, `schema: silver`, exportadas para `data/silver/*`)

| Modelo | Grão | Colunas Principais |
| :--- | :--- | :--- |
| `int_populacao_municipal_unificada` | `(codigo_ibge_municipio, ano_referencia)` | `populacao_residente`, `area_km2`, `densidade_demografica`, `origem_dado` (`CENSO_2022` \| `ESTIMATIVA_IBGE` \| `INTERPOLACAO_LINEAR`), `is_interpolado` |
| `int_ipca_deflator_anual` | `ano_referencia` | `ano_mes_base_deflator`, `numero_indice_medio_anual`, `fator_deflator_anual`, `meses_observados_no_ano` |
| `int_pib_municipal_deflacionado` | `(codigo_ibge_municipio, ano_referencia)` | `pib_nominal_mil_brl`, `pib_real_mil_brl`, `impostos_liquidos_mil_brl`, 4 `vab_*_mil_brl`, 4 `share_vab_*`, `hhi_setorial`, `indice_diversificacao_setorial`, `crescimento_pib_real_yoy_pct`, `cagr_pib_real_3a_pct` |
| `int_cempre_municipal_deflacionado` | `(codigo_ibge_municipio, ano_referencia)` | `num_unidades_locais`, `num_empresas_atuantes`, `pessoal_ocupado_total`, `pessoal_ocupado_assalariado`, `pessoal_assalariado_medio`, `massa_salarial_nominal_mil_brl`, `massa_salarial_real_mil_brl`, `salario_medio_sm`, `salario_medio_nominal_brl`, `salario_medio_real_brl`, `taxa_assalariamento_formal`, `crescimento_empresas_yoy_pct`, `crescimento_emprego_yoy_pct` |

---

## 4. Camada Gold (`schema: gold` + `data/gold/*`)

### 4.1 Dimensões (Contratos Obrigatórios — `5` Modelos, `4` Exportados para Delta Gold)

| Dimensão | Grão | Chave Primária | Principais Atributos |
| :--- | :--- | :--- | :--- |
| `dim_geografia` | Versão SCD2 do município | `sk_municipio` (`varchar`) | `codigo_ibge_municipio`, `nome_municipio`, `codigo_uf`/`sigla_uf`/`nome_uf`, `codigo_regiao`/`sigla_regiao`/`nome_regiao`, `codigo_regiao_imediata`/`nome_regiao_imediata`, `codigo_regiao_intermediaria`/`nome_regiao_intermediaria`, `codigo_microrregiao`/`nome_microrregiao`, `codigo_mesorregiao`/`nome_mesorregiao`, `valid_from`, `valid_to`, `is_current` |
| `dim_tempo` | Mês (`2018-01` até ano atual + 1) | `sk_tempo` (`integer`, `YYYYMM`) | `data_referencia`, `ano_referencia`, `mes_referencia`, `ano_mes`, `trimestre`, `semestre`, `is_ano_censitario` (`ano = 2022`) |
| `time_spine_daily` | Dia (`2018-01-01` até ano atual + 1) | `date_day` (`date`) | Espinha temporal diária exigida pela **dbt Semantic Layer** (não exportada separadamente para Delta Gold) |
| `dim_cnae` | Versão SCD2 da seção CNAE | `sk_cnae_secao` (`varchar`) | `codigo_secao` (`A–U`), `descricao_secao`, `categoria_sidra_12762_id`, `valid_from`, `valid_to`, `is_current` |
| `dim_atividade_varejo` | Atividade comercial PMC | `sk_atividade_varejo` (`varchar`) | `codigo_atividade_pmc`, `nome_atividade_pmc`, `grupo_consumo` (`ALIMENTACAO_ATACAREJO`, `BENS_DURAVEIS_LAR`, `AUTOMOTIVO_CONSTRUCAO`, `COMBUSTIVEIS`, `FARMACIA_VESTUARIO_CONVENIENCIA`) |

### 4.2 Fatos (Contratos Obrigatórios — `6` Tabelas)

| Fato | Grão | Chaves Estrangeiras & Negócio | Principais Métricas |
| :--- | :--- | :--- | :--- |
| `fct_pib_municipal` | Município × Ano | `sk_municipio`, `codigo_ibge_municipio`, `ano_referencia` | `pib_nominal_mil_brl`, `pib_real_mil_brl`, `vab_*_mil_brl`, `share_vab_*`, `hhi_setorial`, `indice_diversificacao_setorial`, `crescimento_pib_real_yoy_pct`, `cagr_pib_real_3a_pct` |
| `fct_populacao_municipal` | Município × Ano | `sk_municipio`, `codigo_ibge_municipio`, `ano_referencia` | `populacao_residente` (`bigint`), `area_km2`, `densidade_demografica`, `origem_dado`, `is_interpolado` |
| `fct_cempre_municipal` | Município × Ano | `sk_municipio`, `codigo_ibge_municipio`, `ano_referencia` | `num_unidades_locais`, `num_empresas_atuantes`, `pessoal_ocupado_total`, `pessoal_ocupado_assalariado`, `massa_salarial_real_mil_brl`, `salario_medio_real_brl`, `taxa_assalariamento_formal`, crescimentos YoY |
| `fct_cempre_setorial_uf` | UF × Seção CNAE × Ano | `codigo_uf`, `sk_cnae_secao`, `codigo_secao_cnae`, `ano_referencia` | `num_empresas`, `pessoal_ocupado_total`, `pessoal_ocupado_assalariado`, `massa_salarial_nominal_mil_brl`, `massa_salarial_real_mil_brl`, `has_sigilo_estatistico` |
| `fct_ipca_mensal` | Mês (`ano_mes`) | `ano_mes` (PK), `ano_referencia`, `mes_referencia`, `data_referencia` | `numero_indice_ipca`, `variacao_mensal_pct`, `variacao_acum_3m_pct`, `variacao_acum_6m_pct`, `variacao_acum_ano_pct`, `variacao_acum_12m_pct`, `ano_mes_base_deflator`, `fator_deflator_base_atual` |
| `fct_pmc_varejo_mensal` | UF × Atividade × Mês | `codigo_uf`, `sk_atividade_varejo`, `codigo_atividade_pmc`, `ano_mes` | `indice_receita_nominal`, `indice_receita_nominal_sa`, `var_mom_sa_receita_pct`, `var_yoy_receita_nominal_pct`, `var_acum_12m_receita_pct`, equivalentes `*_volume_*` |

### 4.3 Data Marts / Tabelas Analíticas (`gold/marts/*` — `6` Marts OBT)

| Mart OBT | Grão | Colunas de Saída Chave | Enums / Classificações |
| :--- | :--- | :--- | :--- |
| `mart_inteligencia_mercado_municipal` | Município × Ano | `sk_inteligencia_municipal`, `is_ultimo_ano_completo`, `pib_per_capita_real_brl`, `empresas_por_1000_hab`, 4 subscores (`score_tamanho_mercado`, `score_poder_compra`, `score_dinamismo`, `score_maturidade_empresarial`), `ims_score_0_100`, `rank_nacional_ims`, `rank_estadual_ims`, `rank_regional_ims`, `tier_mercado` | `Tier 1 - Polo Nacional`, `Tier 2 - Expansao Prioritaria`, `Tier 3 - Emergente`, `Tier 4 - Local / Nicho`, `SEM_CLASSIFICACAO` |
| `mart_clusters_setoriais_uf` | UF × Seção CNAE × Ano | `sk_cluster_setorial`, `quociente_locacional_emprego`, `quociente_locacional_massa_salarial`, `market_share_uf_no_setor_pct`, `crescimento_emprego_setor_yoy_pct`, `has_sigilo_estatistico`, `perfil_especializacao` | `CLUSTER_DOMINANTE` (`>=1.50`), `CLUSTER_ESPECIALIZADO` (`>=1.25`), `EQUILIBRADO_MEDIA_NACIONAL` (`>=0.85`), `SUB_REPRESENTADO`, `SIGILO_OU_INDISPONIVEL` |
| `mart_pulso_consumo_macro` | UF × Atividade PMC × Mês | `sk_pulso_consumo`, `spread_preco_vs_volume_yoy_pp`, `spread_volume_vs_ipca_12m_pp`, `media_movel_3m_volume`, `media_movel_12m_volume`, `ipca_variacao_mensal_pct`, `ipca_variacao_acum_12m_pct`, `regime_consumo` | `EXPANSAO_REAL`, `PRESSAO_INFLACIONARIA`, `ESTABILIDADE`, `RETRACAO`, `SEM_DADO` |
| `mart_pulso_servicos_uf` | UF × Mês | `sk_pulso_servicos`, `indice_receita_nominal`, `indice_volume_servicos`, `indice_volume_servicos_sa`, `var_mom_sa_volume_pct`, `var_yoy_volume_pct`, `spread_preco_vs_volume_yoy_pp`, `spread_volume_vs_ipca_12m_pp`, `media_movel_3m_volume`, `media_movel_12m_volume`, `regime_servicos` | `EXPANSAO_REAL`, `PRESSAO_INFLACIONARIA`, `ESTABILIDADE`, `RETRACAO`, `SEM_DADO` |
| `mart_mercado_trabalho_uf` | UF × Trimestre (`ano_trimestre`) | `sk_mercado_trabalho`, `label_trimestre`, `is_ultimo_trimestre`, `taxa_desocupacao_pct`, `taxa_subutilizacao_composta_pct`, `var_yoy_desocupacao_pp`, `rendimento_medio_real_brl`, `rendimento_homens_real_brl`, `rendimento_mulheres_real_brl`, `var_yoy_rendimento_real_pct`, `hiato_salarial_genero_pct` | — |
| `mart_demografia_municipal` | Município atual | `codigo_ibge_municipio`, `codigo_regiao_imediata`, `nome_regiao_imediata`, `ano_populacao_atual`, `populacao_atual`, `populacao_censo_2022`, `saldo_populacional_desde_2022`, `crescimento_populacional_desde_2022_pct`, `rank_populacao_uf`, `area_km2`, `densidade_demografica`, `pib_real_mil_brl`, `massa_salarial_real_mil_brl`, `ims_score_0_100` | — |

### 4.4 Camada Semântica (`dbt_project/models/gold/_gold.yml`)

- **`3` modelos semânticos habilitados**: `mart_inteligencia_mercado_municipal` (entidade `municipio`), `mart_clusters_setoriais_uf` (`cluster_setorial`) e `mart_pulso_consumo_macro` (`pulso_consumo`), apoiados em `time_spine_daily`.
- **`12` métricas governadas**: `pib_real_total_mil_brl`, `populacao_residente_total`, `massa_salarial_real_total_mil_brl`, `empresas_atuantes_total`, `ims_score_medio`, `pib_real_per_capita_agregado_brl` (derivada), `emprego_setorial_total`, `massa_salarial_setorial_real_mil_brl`, `ql_emprego_medio`, `volume_varejo_medio`, `var_yoy_volume_media_pct` e `spread_preco_volume_medio_pp`.

---

## 5. Testes dbt & Inventário Dagster

### 5.1 Testes dbt (`193` Testes de Dados + `11` Testes Unitários SQL)

- **Testes Singulares (`dbt_project/tests/`)**:
  - `assert_pib_contabilidade_consistente.sql`
  - `assert_vab_setores_soma_total.sql`
  - `assert_ims_score_bounds_and_distribution.sql`
  - `assert_no_orphan_municipios_gold.sql`
- **Testes Unitários Nativos (`format: sql`, `11` ao todo)**:
  - **Camada Intermediate (`_intermediate.yml`, `6`)**: `test_populacao_interpolacao_2023`, `test_ipca_deflator_calculo_constante`, `test_pib_deflacao_e_hhi_setorial`, `test_pib_gap_de_ano_e_setores_nulos`, `test_pib_hhi_com_vab_negativo`, `test_cempre_deflacao_e_yoy`.
  - **Camada Gold (`_gold.yml`, `5`)**: `test_quociente_locacional_cluster_especializado`, `test_quociente_locacional_particao_incompleta_retorna_null`, `test_pulso_consumo_regimes_e_spread`, `test_ims_score_tiers_e_ranking`, `test_mart_demografia_municipal`.

### 5.2 Inventário Unificado Dagster (`src/ibge_market_intel/orchestration/definitions.py`)

- **Assets**: `49` materializáveis (`0` fontes externas desconectadas) distribuídos nos grupos `bronze`, `silver_staging`, `silver_scd2`, `silver_intermediate`, `gold_dimensions`, `gold_facts`, `gold_marts` e `lakehouse_export`.
- **Asset Checks**: `204` no total (`12` checks Pandera bloqueantes na Bronze + `192` checks integrados do `dbt`).
- **Jobs**: `dbt_medallion_job`, `macro_refresh_job`, `delta_maintenance_job`.
- **Sensor**: `ibge_new_period_sensor` (intervalo mínimo `3600s`, monitora `/periodos` para todas as 10 fontes SIDRA — `ipca_mensal`, `pmc_varejo_uf`, `pms_servicos_uf`, `pnad_desocupacao_uf`, `pnad_rendimento_uf`, `pib_municipal`, `cempre_municipal`, `cempre_setorial_uf`, `estimativa_populacao` e `censo_populacao` — registrando novas partições via `DynamicPartitionsDefinition`).
- **Schedules (`America/Sao_Paulo`)**:
  - `monthly_macro_refresh_schedule`: cron `0 8 15 * *` (executa `macro_refresh_job`)
  - `weekly_delta_maintenance_schedule`: cron `0 3 * * 0` (executa `delta_maintenance_job`)
