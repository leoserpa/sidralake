# Documentação Técnica / Technical Documentation — SidraLake (`v0.5.0`)

Bem-vindo à documentação do **SidraLake** (*Inteligência de Mercado IBGE 360*). Esta suíte combina o framework **[Diátaxis](https://diataxis.fr/)** em versões bilíngues espelhadas (**Português - BR** e **Inglês**) com **ADRs** em [`docs/decisions/`](decisions/README.md).

Welcome to the **SidraLake** (*IBGE Market Intelligence 360*) documentation suite. It combines the **[Diátaxis](https://diataxis.fr/)** framework in mirrored bilingual editions (**Portuguese - BR** and **English**) with **ADRs** under [`docs/decisions/`](decisions/README.md).

---

## Escolha seu Idioma / Choose Your Language

| Idioma / Language | Índice Diátaxis / Diátaxis Index | README Principal / Root README | ADRs & Governança |
| :--- | :--- | :--- | :--- |
| **Português (BR)** | [Documentação em Português (pt-BR)](pt-br/README.md) | [README.md](../README.md) | [ADRs](decisions/README.md) · [AGENTS.md](../AGENTS.md) |
| **English** | [Documentation in English (en)](en/README.md) | [README.en.md](../README.en.md) | [CHANGELOG.md](../CHANGELOG.md) |

---

## Mapa Rápido dos Quadrantes Diátaxis / Diátaxis Quadrants

| Quadrante / Quadrant | Orientação / Focus | Quando Consultar / When to Read |
| :--- | :--- | :--- |
| **Tutoriais / Tutorials** | Aprendizado prático / Learning-oriented | Primeira execução guiada do ambiente até a camada Gold e export BI |
| **Guias Práticos / How-to Guides** | Tarefas específicas / Problem-oriented | Receitas passo a passo para backfill, manutenção Delta, ajuste de pesos IMS, novas fontes IBGE e resolução de falhas de CI/BI |
| **Referência / Reference** | Consulta técnica / Information-oriented | Especificação exata de CLI `sidralake`, variáveis `IBGE_*`, 12 APIs IBGE, contratos Pandera/dbt, colunas e inventário Dagster (49 ativos) |
| **Explicações / Explanation** | Compreensão / Understanding-oriented | Decisões de arquitetura Medalhão, camada BI as Code, casos de borda do IBGE e metodologia econômica (IPCA, HHI, IMS, QL, PMC, PMS, PNAD, Demografia) |
| **Decisões (ADRs)** | Racional técnico / Design rationale | Contexto, alternativas rejeitadas e trade-offs registrados em [`docs/decisions/`](decisions/README.md) |

---

## Escopo da Documentação / Documentation Scope

- **Público-alvo / Target Audience**: Engenheiros de Dados, Analytics Engineers e agentes contribuidores operando e evoluindo o Lakehouse e o BI estático.
- **Incluído / Included**: ciclo local completo (`uv`, Python 3.12, ingestão assíncrona das 12 fontes IBGE, Delta Lake ACID, contratos Pydantic v2 e Pandera, transformações `dbt-duckdb` Silver/SCD2/Gold, contratos *enforced*, `193` testes de dados + `11` unit tests dbt, camada semântica dbt, Dagster `49` ativos / `204` checks, exportação Parquet ZSTD, dashboard Evidence.dev em DuckDB-WASM, guardrails em 3 camadas, `pytest`/`ruff`/`mypy`/`sqlfluff` e workflows GitHub Actions CI + Pages).
- **Fora de escopo / Out of Scope**: implantação em nuvem paga (AWS, GCP, Azure) e orquestração em containers (Docker, Kubernetes).
