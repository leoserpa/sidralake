# Documentação Técnica / Technical Documentation — SidraLake (Inteligência de Mercado IBGE 360)

Bem-vindo à documentação do **SidraLake** (*Inteligência de Mercado IBGE 360*). Esta suíte segue o framework **[Diátaxis](https://diataxis.fr/)** e está disponível integralmente em **Português (BR)** e **Inglês**, com paridade 1:1 entre todos os documentos.

Welcome to the **SidraLake** (*IBGE Market Intelligence 360*) pipeline documentation. This suite follows the **[Diátaxis](https://diataxis.fr/)** framework and is fully available in **Portuguese (BR)** and **English**, with 1:1 parity across every document.

---

## Escolha seu Idioma / Choose Your Language

| Idioma / Language | Índice Completo / Full Index | README Principal / Root README |
| :--- | :--- | :--- |
| **Português (BR)** | [Documentação em Português (pt-BR)](pt-br/README.md) | [README.md](../README.md) |
| **English** | [Documentation in English (en)](en/README.md) | [README.en.md](../README.en.md) |

---

## Mapa Rápido dos Quadrantes Diátaxis / Diátaxis Quadrants

| Quadrante / Quadrant | Orientação / Focus | Quando Consultar / When to Read |
| :--- | :--- | :--- |
| **Tutoriais / Tutorials** | Aprendizado prático / Learning-oriented | Primeira execução guiada do ambiente até a inspeção da camada Gold |
| **Guias Práticos / How-to Guides** | Tarefas específicas / Problem-oriented | Receitas passo a passo para backfill, manutenção Delta, ajuste de pesos IMS, novas fontes IBGE e resolução de falhas |
| **Referência / Reference** | Consulta técnica / Information-oriented | Especificação exata de CLI, variáveis `IBGE_*`, APIs IBGE, contratos Pandera/dbt, colunas e inventário Dagster |
| **Explicações / Explanation** | Compreensão / Understanding-oriented | Decisões de arquitetura Medalhão, casos de borda reais do IBGE e metodologia econômica (IPCA, HHI, IMS, QL, PMC) |

---

## Escopo da Documentação / Documentation Scope

- **Público-alvo / Target Audience**: Engenheiros de Dados e Analytics Engineers responsáveis por operar, validar e estender o Lakehouse local.
- **Incluído / Included**: ciclo local completo (`uv`, Python 3.12, ingestão assíncrona das APIs do IBGE, Delta Lake ACID, contratos Pydantic v2 e Pandera, transformações `dbt-duckdb` Silver/SCD2/Gold, *Enforced Model Contracts*, testes dbt unitários e singulares, Dagster assets/partições/checks/sensor/schedules, manutenção `OPTIMIZE`/`VACUUM`, `pytest`/`ruff`/`mypy`/`sqlfluff` e CI GitHub Actions).
- **Fora de escopo / Out of Scope**: deploy em nuvem (AWS, GCP, Azure), containerização (Docker, Kubernetes) e construção de dashboards em ferramentas de BI.
