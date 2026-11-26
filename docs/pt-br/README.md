> 🌐 **Idioma:** **Português (BR)** | [English](../en/README.md) · [Portal](../README.md) · [ADRs](../decisions/README.md) · [README Principal](../../README.md)

# Documentação Técnica — SidraLake (`v0.5.0`, Português - BR)

Esta documentação segue o framework **Diátaxis** para **Engenheiros de Dados, Analytics Engineers e agentes de código** que operam, validam e estendem o Lakehouse **SidraLake** e sua camada **BI as Code**.

---

## Escopo

- **Incluído**: ambiente Python com `uv`, ingestão assíncrona das 12 fontes IBGE, contratos Pydantic v2 e Pandera, camadas Bronze/Silver/Gold em Delta Lake e DuckDB, snapshots SCD Tipo 2 e modelos `dbt-duckdb`, camada semântica dbt, orquestração Dagster (`49` ativos, `204` checks, partições dinâmicas, sensor e agendamentos), exportação Parquet ZSTD + dashboard **Evidence.dev** (`dashboard/`, 9 páginas em DuckDB-WASM) com guardrails em 3 camadas e CI/Deploy GitHub Actions.
- **Fora de escopo**: implantação em provedores cloud (AWS/GCP/Azure) e orquestração em containers (Docker/Kubernetes).

---

## Navegação pelos Quadrantes e ADRs

### 1. Tutoriais (Aprendizado Prático)
- [Primeiros Passos: do Zero à Camada Gold](tutoriais/primeiros-passos.md) — Suba o ambiente com `uv`, execute a carga rápida contra a API real do IBGE, consulte a Gold no DuckDB e explore Dagster UI, dbt Docs e o export BI.

### 2. Guias Práticos (Receitas Operacionais)
- [Backfill, Reprocessamento e Manutenção Delta Lake](guias-praticos/backfill-e-reprocessamento.md) — Rode a carga completa do Brasil, faça backfill cirúrgico por partição, recupere versões com *Time Travel* e execute `OPTIMIZE`/`VACUUM`.
- [Ajustar Pesos do Score IMS e Adicionar Nova Fonte IBGE](guias-praticos/ajustar-ims-e-adicionar-fonte-ibge.md) — Recalibre os pesos do Score IMS e siga o roteiro de 7 passos para integrar novos agregados SIDRA.
- [Executar Portões de Qualidade e Diagnosticar Falhas de CI](guias-praticos/portoes-de-qualidade-e-ci.md) — Rode os portões Python, dbt, BI (guardrails em 3 camadas) e documentação (`make check-docs`), além de diagnosticar falhas comuns.

### 3. Referência (Especificação Técnica)
- [Configuração, CLI e Ambiente](referencia/configuracao-e-cli.md) — Referência da CLI `sidralake` (e alias `ibge-pipeline`), alvos do `Makefile`, variáveis `IBGE_*`, `profiles.yml` e workflows `.github/workflows/`.
- [Fontes IBGE e Contratos de Dados](referencia/fontes-ibge-e-contratos.md) — Catálogo técnico das 12 fontes oficiais, códigos especiais do SIDRA (`-`, `..`, `...`, `X`), schemas Pydantic v2, contratos Pandera e colunas de auditoria.
- [Dicionário de Dados e Inventário do Lakehouse](referencia/dicionario-de-dados-lakehouse.md) — Tabelas Bronze/Silver/Gold, grãos, chaves, contratos obrigatórios, `193`+`11` testes dbt e inventário completo do Dagster (`49` ativos / `204` checks).

### 4. Explicações (Arquitetura e Metodologia)
- [Arquitetura Medalhão e Decisões de Engenharia](explicacoes/arquitetura-medalhao-e-design.md) — Racional da arquitetura local-first, fluxo zero-copy `delta_scan()`/Arrow, camada BI as Code, resiliência e casos de borda do IBGE.
- [Metodologia de Inteligência de Mercado](explicacoes/metodologia-inteligencia-de-mercado.md) — Base conceitual de IPCA, interpolação de 2023, HHI, Score IMS, QL, PMC, Serviços (PMS), Trabalho/Renda (PNAD) e Demografia Municipal.

### 5. Decisões Arquiteturais (ADRs) & Governança
- [Índice de ADRs (`ADR-001` a `ADR-006`)](../decisions/README.md)
- [Guia para Agentes e Invariantes (`AGENTS.md`)](../../AGENTS.md) · [Histórico de Versões (`CHANGELOG.md`)](../../CHANGELOG.md)

---

## Mapa do Repositório

```text
projeto ibge/
├── .github/workflows/
│   ├── ci.yml                            # CI (ruff, mypy, dbt parse/unit tests, sqlfluff, pytest)
│   └── pages.yml                         # Build & Deploy mensal/push do BI no GitHub Pages
├── AGENTS.md                             # Invariantes de engenharia, comandos e armadilhas conhecidas
├── CHANGELOG.md                          # Historico cronologico append-only das versoes
├── Makefile                              # Atalhos operacionais locais (incluindo `check-docs`)
├── pyproject.toml                        # Versao 0.5.0, dependencias e scripts (`sidralake` / `ibge-pipeline`)
├── scripts/
│   └── check_doc_drift.py                # Verificador de links Markdown, ADRs e drift via Git
├── src/ibge_market_intel/
│   ├── cli.py                            # CLI `sidralake` (`run`, `maintain`, `inspect`, `insights`, `export-bi`, `validate-bi`, `test`)
│   ├── config.py                         # PipelineSettings (variaveis IBGE_*)
│   ├── logging.py                        # Logging estruturado via structlog
│   ├── ingestion/                        # 12 catalogos IBGE, descoberta de periodos, cliente async, Pydantic e DeltaLakeWriter
│   ├── quality/                          # Contratos Pandera Bronze e `dashboard_guard.py` (DuckDB-WASM)
│   ├── analytics/                        # `insights.py` (Polars Lazy) e `bi_export.py` (Parquet ZSTD)
│   └── orchestration/                    # 49 ativos, 204 checks, sensor e agendamentos Dagster
├── dbt_project/
│   ├── dbt_project.yml                   # Configuracao dbt e pesos IMS (`vars`)
│   ├── profiles.yml                      # Perfis DuckDB (`dev` e `ci`) com extensoes delta/parquet
│   ├── macros/                           # `parse_ibge_numeric.sql`, `normalize_percentile.sql`, `generate_schema_name.sql`
│   ├── snapshots/                        # SCD Tipo 2 (`snap_ibge_municipios`, `snap_ibge_cnae_secoes`)
│   ├── models/
│   │   ├── bronze_sources.yml            # 12 fontes externas Delta lidas via `delta_scan()`
│   │   ├── silver/                       # 12 views staging + 4 tabelas intermediate (+ 6 unit tests)
│   │   └── gold/                         # 5 dimensoes (c/ time_spine_daily) + 6 fatos + 6 marts OBT + 3 modelos semanticos (+ 5 unit tests)
│   └── tests/                            # 4 testes singulares de reconciliacao e integridade
├── dashboard/
│   ├── pages/                            # 9 paginas Evidence.dev (.md) + `+layout.svelte` (desktop + mobile CSS)
│   ├── components/                       # TopNavBar, KpiCard, ExecTable, CityHero, DonutPanel, ResetFilters, MethodologyCard, DataFooter
│   ├── sources/sidralake/                # 10 fontes SQL lendo `parquet_data/*.parquet`
│   └── scripts/smoke_test_build.mjs      # Auditoria Chromium E2E (1440x900, filtros e 390x844 mobile)
├── tests/                                # 34 testes unitarios e 2 testes de integracao
└── docs/                                 # Documentacao Diataxis bilingue (`pt-br/` / `en/`) + `decisions/` (ADRs)
```
