> 🌐 **Idioma:** **Português (BR)** | [English](README.en.md) · [Documentação Completa (Diátaxis)](docs/pt-br/README.md)

# SidraLake — Inteligência de Mercado IBGE 360 (Pipeline de Dados Medalhão)

**SidraLake** é um pipeline de Engenharia de Dados em **Arquitetura Medalhão (Bronze → Silver → Gold)** para **Inteligência de Mercado 360°** com dados oficiais do **IBGE** (Localidades, CNAE 2.0, PIB Municipal, Censo Demográfico 2022, Estimativas Populacionais, CEMPRE Municipal/Setorial, IPCA e Pesquisa Mensal de Comércio - PMC).

O projeto adota uma **Arquitetura de Dados Moderna Local-First** com foco em confiabilidade, contratos de dados e governança: **Delta Lake** com transações ACID e histórico temporal (*Time Travel*), **DuckDB + dbt-duckdb** para modelagem Silver/SCD Tipo 2/Gold, **Polars + Pandera + Pydantic v2** como barreiras de qualidade na ingestão e **Dagster** para orquestração orientada a ativos (*assets*), partições, sensores de frescor e linhagem ponta a ponta.

---

## Tecnologias Utilizadas

- **Lakehouse ACID**: Delta Lake (`deltalake`) nas camadas Bronze, Silver e Gold (`_delta_log`, `replace_where`, `MERGE`, `OPTIMIZE`, `VACUUM`)
- **Motor Analítico, Contratos & Camada Semântica**: DuckDB + `dbt-duckdb` 1.12 (`delta_scan()`, Staging, Intermediate, SCD Tipo 2 via `dbt snapshot`, Esquema Estrela + 3 Data Marts OBT com **Contratos Obrigatórios** em 100% da camada Gold, **dbt Semantic Layer** com 3 modelos semânticos, 12 métricas governadas e `time_spine_daily`, **10 testes unitários SQL** e testes singulares contábeis)
- **Ingestão & Consultas Lazy**: Python `>=3.12,<3.14` (`uv`), `httpx` assíncrono com semáforo e fatiamento adaptativo por UF/semestre, `tenacity` backoff com jitter, `Pydantic v2`, **Polars Lazy API** (`scan_delta` + hash determinístico Arrow IPC), `Pandera[polars]`
- **Orquestração & Linhagem**: Dagster (`dagster-dbt`, partições estáticas anuais, Verificações de Ativos bloqueantes, **Declarative Automation `AutomationCondition.eager()`**, Sensor de Frescor blindado na API do IBGE e Agendamentos)
- **Qualidade & Observabilidade**: `structlog` JSON, `ruff`, `mypy --strict`, `sqlfluff`, `pytest` (`>85%` de cobertura) + `respx`, GitHub Actions CI

---

## Linhagem da DAG (dbt Manifest)

```mermaid
graph LR
    %% Sources (Blue)
    s_loc["localidades"]:::source
    s_cnae["cnae_secoes"]:::source
    s_pib["pib_municipal"]:::source
    s_censo["censo_populacao"]:::source
    s_est["estimativa_populacao"]:::source
    s_cemp_m["cempre_municipal"]:::source
    s_cemp_uf["cempre_setorial_uf"]:::source
    s_ipca["ipca_mensal"]:::source
    s_pmc["pmc_varejo_uf"]:::source

    %% Staging (Bronze)
    stg_loc["stg_ibge__localidades"]:::staging
    stg_cnae["stg_ibge__cnae_secoes"]:::staging
    stg_pib["stg_ibge__pib_municipal"]:::staging
    stg_censo["stg_ibge__censo_populacao"]:::staging
    stg_est["stg_ibge__estimativa_populacao"]:::staging
    stg_cemp_m["stg_ibge__cempre_municipal"]:::staging
    stg_cemp_uf["stg_ibge__cempre_setorial_uf"]:::staging
    stg_ipca["stg_ibge__ipca_mensal"]:::staging
    stg_pmc["stg_ibge__pmc_varejo_uf"]:::staging

    %% Silver Intermediate & SCD2 Snapshots (Silver)
    snap_mun["snap_ibge_municipios (SCD2)"]:::silver
    snap_cnae["snap_ibge_cnae_secoes (SCD2)"]:::silver
    int_ipca["int_ipca_deflator_anual"]:::silver
    int_pib["int_pib_municipal_deflacionado"]:::silver
    int_pop["int_populacao_municipal_unificada"]:::silver
    int_cemp["int_cempre_municipal_deflacionado"]:::silver

    %% Gold Dimensions, Facts & Marts (Gold)
    dim_geo["dim_geografia"]:::gold
    dim_cnae["dim_cnae"]:::gold
    dim_var["dim_atividade_varejo"]:::gold
    dim_tempo["dim_tempo / time_spine_daily"]:::gold
    fct_pib["fct_pib_municipal"]:::gold
    fct_pop["fct_populacao_municipal"]:::gold
    fct_cemp_m["fct_cempre_municipal"]:::gold
    fct_cemp_uf["fct_cempre_setorial_uf"]:::gold
    fct_ipca["fct_ipca_mensal"]:::gold
    fct_pmc["fct_pmc_varejo_mensal"]:::gold
    mart_ims["mart_inteligencia_mercado_municipal"]:::gold
    mart_cl["mart_clusters_setoriais_uf"]:::gold
    mart_pmc["mart_pulso_consumo_macro"]:::gold

    %% Lineage edges (extraidas do dbt manifest.json)
    s_loc --> stg_loc --> snap_mun --> dim_geo
    s_cnae --> stg_cnae --> snap_cnae --> dim_cnae
    s_ipca --> stg_ipca --> int_ipca
    stg_ipca --> fct_ipca
    s_pib --> stg_pib --> int_pib
    int_ipca --> int_pib --> fct_pib
    dim_geo --> fct_pib
    s_censo --> stg_censo --> int_pop
    s_est --> stg_est --> int_pop --> fct_pop
    dim_geo --> fct_pop
    s_cemp_m --> stg_cemp_m --> int_cemp
    int_ipca --> int_cemp --> fct_cemp_m
    dim_geo --> fct_cemp_m
    s_cemp_uf --> stg_cemp_uf --> fct_cemp_uf
    dim_cnae --> fct_cemp_uf
    int_ipca --> fct_cemp_uf
    s_pmc --> stg_pmc --> dim_var --> fct_pmc
    stg_pmc --> fct_pmc

    dim_geo --> mart_ims
    fct_pib --> mart_ims
    fct_pop --> mart_ims
    fct_cemp_m --> mart_ims
    dim_geo --> mart_cl
    dim_cnae --> mart_cl
    fct_cemp_uf --> mart_cl
    dim_geo --> mart_pmc
    dim_var --> mart_pmc
    fct_pmc --> mart_pmc
    fct_ipca --> mart_pmc

    classDef source fill:#1E88E5,stroke:#0D47A1,color:#FFFFFF
    classDef staging fill:#CD7F32,stroke:#7B4B16,color:#FFFFFF
    classDef silver fill:#B0BEC5,stroke:#455A64,color:#111111
    classDef gold fill:#FBC02D,stroke:#F57F17,color:#111111
```

> **Legenda:** 🔵 **Fontes Bronze Delta** · 🟤 **Staging (`stg_*`)** · ⚪ **Intermediate (`int_*`) & Snapshots SCD2** · 🟡 **Camada Gold (Dimensões, Fatos, Marts & Camada Semântica)**

---

## Início Rápido

```bash
uv sync --dev                        # Cria .venv com uv e instala dependencias
uv run sidralake run --mode smoke    # Validacao rapida (SP/MT) Bronze -> Silver -> Gold + Delta
uv run sidralake run --mode full     # Carga completa Brasil (5.571 municipios, 2018-2026)
uv run sidralake insights --top 10   # Rankings imediatos via Polars Lazy API (scan_delta) na Gold
uv run sidralake inspect             # Sanity check completo no DuckDB e Delta Lake Gold
uv run sidralake test                # Roda ruff, mypy, pytest (unitario + E2E) e 10 dbt unit tests
make dagster-dev                     # Sobe a interface Dagster (ativos, particoes, verificacoes)
```

---

## Documentação Técnica (Diátaxis)

Toda a documentação está organizada segundo o framework **Diátaxis** em versões bilíngues espelhadas (`docs/pt-br/` e `docs/en/`). Veja o [Portal Central de Documentação](docs/README.md) ou navegue diretamente pelos quadrantes em Português:

| Quadrante Diátaxis | Propósito | Documento |
| :--- | :--- | :--- |
| **Tutorial** | Aprender na prática subindo e executando o pipeline pela primeira vez | [Primeiros Passos](docs/pt-br/tutoriais/primeiros-passos.md) |
| **Guia Prático** | Executar carga completa, backfill cirúrgico, histórico Delta e manutenção | [Backfill, Reprocessamento e Manutenção Delta](docs/pt-br/guias-praticos/backfill-e-reprocessamento.md) |
| **Guia Prático** | Recalibrar pesos do Score IMS e integrar um novo agregado SIDRA | [Ajustar Pesos do IMS e Adicionar Fonte IBGE](docs/pt-br/guias-praticos/ajustar-ims-e-adicionar-fonte-ibge.md) |
| **Guia Prático** | Rodar portões de qualidade localmente e diagnosticar falhas comuns | [Executar Portões de Qualidade e Diagnosticar Falhas](docs/pt-br/guias-praticos/portoes-de-qualidade-e-ci.md) |
| **Referência** | CLI `ibge-pipeline`, alvos do `Makefile`, variáveis `IBGE_*`, `profiles.yml` e CI | [Configuração, CLI e Ambiente](docs/pt-br/referencia/configuracao-e-cli.md) |
| **Referência** | Catálogo das 9 fontes IBGE, códigos especiais SIDRA e contratos Pydantic/Pandera | [Fontes IBGE e Contratos de Dados](docs/pt-br/referencia/fontes-ibge-e-contratos.md) |
| **Referência** | Dicionário das camadas Bronze/Silver/Gold, testes dbt e grafo Dagster | [Dicionário de Dados e Inventário do Lakehouse](docs/pt-br/referencia/dicionario-de-dados-lakehouse.md) |
| **Explicação** | Decisões de arquitetura Medalhão, resiliência e casos de borda reais do IBGE | [Arquitetura Medalhão e Decisões de Engenharia](docs/pt-br/explicacoes/arquitetura-medalhao-e-design.md) |
| **Explicação** | Racional econômico e estatístico de IPCA, HHI, Score IMS, QL e PMC | [Metodologia de Inteligência de Mercado](docs/pt-br/explicacoes/metodologia-inteligencia-de-mercado.md) |

---

## Licença e Fonte dos Dados

O código-fonte deste projeto é licenciado sob a **[GNU General Public License v3.0 (GPL-3.0)](LICENSE)**. Os dados primários extraídos pertencem ao **Instituto Brasileiro de Geografia e Estatística (IBGE)** e são de acesso público nos termos da Política de Dados Abertos do Governo Federal.
