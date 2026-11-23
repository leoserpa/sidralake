> 🌐 **Idioma:** **Português (BR)** | [English](../en/README.md) · [Portal](../../docs/README.md) · [README Principal](../../README.md)

# Documentação Técnica — SidraLake (Português - BR)

Esta documentação foi estruturada segundo o framework **Diátaxis** para **Engenheiros de Dados e Analytics Engineers** que precisam compreender a arquitetura, subir o ambiente local, operar o pipeline ponta a ponta e estender o Lakehouse **SidraLake (Inteligência de Mercado IBGE 360)** com autonomia.

---

## Escopo

- **Incluído**: ambiente Python com `uv`, ingestão assíncrona nas APIs do IBGE, contratos Pydantic v2 e Pandera, camadas Bronze/Silver/Gold em Delta Lake e DuckDB, snapshots SCD Tipo 2 e modelos `dbt-duckdb`, orquestração Dagster (ativos, partições, verificações bloqueantes, sensor e agendamentos), manutenção `OPTIMIZE`/`VACUUM`, suíte de testes e CI GitHub Actions.
- **Fora de escopo**: implantação em provedores cloud (AWS/GCP/Azure), orquestração em containers (Docker/Kubernetes) e ferramentas externas de visualização/BI.

---

## Navegação pelos 4 Quadrantes

### 1. Tutoriais (Aprendizado Prático)
- [Primeiros Passos: do Zero à Camada Gold](tutoriais/primeiros-passos.md) — Suba o ambiente com `uv`, execute a carga rápida contra a API real do IBGE, consulte a Gold no DuckDB e explore a interface Dagster e o dbt Docs.

### 2. Guias Práticos (Receitas Operacionais)
- [Backfill, Reprocessamento e Manutenção Delta Lake](guias-praticos/backfill-e-reprocessamento.md) — Rode a carga completa do Brasil, faça backfill cirúrgico por partição, recupere versões com histórico temporal (*Time Travel*) e execute `OPTIMIZE`/`VACUUM`.
- [Ajustar Pesos do Score IMS e Adicionar Nova Fonte IBGE](guias-praticos/ajustar-ims-e-adicionar-fonte-ibge.md) — Recalibre os pesos do Índice de Atratividade Municipal e siga o roteiro completo para integrar novos agregados SIDRA.
- [Executar Portões de Qualidade e Diagnosticar Falhas de CI](guias-praticos/portoes-de-qualidade-e-ci.md) — Rode os portões de qualidade (`ruff`, `mypy`, `sqlfluff`, `pytest`, `dbt`) e resolva erros comuns de contrato, reconciliação e bloqueio do DuckDB.

### 3. Referência (Especificação Técnica)
- [Configuração, CLI e Ambiente](referencia/configuracao-e-cli.md) — Referência da CLI `ibge-pipeline`, todos os alvos do `Makefile`, variáveis de ambiente `IBGE_*`, `profiles.yml` e pipeline de CI.
- [Fontes IBGE e Contratos de Dados](referencia/fontes-ibge-e-contratos.md) — Catálogo técnico das 9 fontes oficiais, códigos especiais do SIDRA (`-`, `..`, `...`, `X`), schemas Pydantic v2, contratos Pandera e colunas de auditoria.
- [Dicionário de Dados e Inventário do Lakehouse](referencia/dicionario-de-dados-lakehouse.md) — Tabelas Bronze/Silver/Gold, grãos, chaves, Contratos de Modelo Obrigatórios, testes singulares/unitários do dbt e inventário completo do Dagster.

### 4. Explicações (Arquitetura e Metodologia)
- [Arquitetura Medalhão e Decisões de Engenharia](explicacoes/arquitetura-medalhao-e-design.md) — Racional da arquitetura local-first, fluxo zero-copy `delta_scan()`/Arrow, resiliência de ingestão, idempotência e casos de borda reais do IBGE.
- [Metodologia de Inteligência de Mercado](explicacoes/metodologia-inteligencia-de-mercado.md) — Base conceitual e matemática de deflação pelo IPCA, interpolação populacional de 2023, HHI, Score IMS (0–100), Quociente Locacional (QL) e Pulso de Consumo (PMC × IPCA).

---

## Mapa do Repositório

```text
projeto ibge/
├── .github/workflows/ci.yml              # Pipeline de CI (ruff, mypy, dbt, sqlfluff, pytest)
├── Makefile                              # Atalhos operacionais locais
├── pyproject.toml                        # Configuracao do pacote, dependencias e ferramentas
├── src/ibge_market_intel/
│   ├── cli.py                            # CLI `ibge-pipeline` (run, maintain, inspect)
│   ├── config.py                         # PipelineSettings (variaveis IBGE_*)
│   ├── logging.py                        # Logging estruturado via structlog
│   ├── ingestion/                        # Catalogos IBGE, cliente HTTP async, Pydantic e DeltaLakeWriter
│   ├── quality/                          # Contratos Pandera (Disjuntores Bronze)
│   └── orchestration/                    # Ativos Bronze/dbt/Export, Verificacoes, Sensor e Agendamentos Dagster
├── dbt_project/
│   ├── dbt_project.yml                   # Configuracao do projeto dbt e pesos IMS (`vars`)
│   ├── profiles.yml                      # Perfis DuckDB (`dev` e `ci`) com extensoes delta/parquet
│   ├── macros/                           # `parse_ibge_numeric.sql`, `normalize_percentile.sql`, `generate_schema_name.sql`
│   ├── snapshots/                        # SCD Tipo 2 (`snap_ibge_municipios`, `snap_ibge_cnae_secoes`)
│   ├── models/
│   │   ├── bronze_sources.yml            # Fontes externas Delta lidas via `delta_scan()`
│   │   ├── silver/                       # 9 views staging + 4 tabelas intermediate (+ testes unitarios dbt)
│   │   └── gold/                         # 4 dimensoes + 6 fatos (contratos obrigatorios) + 3 marts OBT
│   └── tests/                            # 4 testes singulares de reconciliacao e integridade
├── tests/                                # Testes unitarios (respx/mocks) e integracao E2E offline
└── docs/                                 # Documentacao Diataxis bilingue (pt-br / en)
    ├── pt-br/                            # tutoriais/, guias-praticos/, referencia/, explicacoes/
    └── en/                               # tutorials/, how-to/, reference/, explanation/
```
