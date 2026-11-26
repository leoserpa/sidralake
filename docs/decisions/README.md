> 🌐 **Idioma / Language:** Bilíngue (**Português - BR** & **English**) · [Portal de Documentação](../README.md) · [README](../README.md)

# Architecture Decision Records (ADRs) — SidraLake

Registros de Decisão Arquitetural (**ADRs**) documentam o *porquê* das decisões técnicas significativas do SidraLake: contexto, restrições, alternativas avaliadas e consequências aceitas.

*Architecture Decision Records (ADRs) capture the context, constraints, evaluated alternatives, and trade-offs behind SidraLake's architectural choices.*

---

## Índice / Index

| ID | Decisão / Decision | Status | Data / Date |
| :--- | :--- | :--- | :--- |
| [ADR-001](ADR-001-local-first-medallion-delta-duckdb-dbt-dagster.md) | Arquitetura Medalhão Local-First com Delta Lake, DuckDB, dbt e Dagster / *Local-First Medallion Stack* | Accepted | 2026-11-23 |
| [ADR-002](ADR-002-ipca-deflation-and-winsorized-ims-scoring.md) | Deflação por IPCA, Interpolação 2023 e Score IMS Winsorizado / *IPCA Deflation & Winsorized IMS Scoring* | Accepted | 2026-11-23 |
| [ADR-003](ADR-003-evidence-static-bi-zstd-parquet-and-3-layer-guardrails.md) | BI Estático em Evidence.dev (DuckDB-WASM), Parquet ZSTD e Guardrails em 3 Camadas / *Static BI, ZSTD Parquet & 3-Layer Guardrails* | Accepted | 2026-11-24 |
| [ADR-004](ADR-004-dynamic-period-discovery-and-dagster-partitions.md) | Descoberta Dinâmica de Períodos SIDRA e Partições Dagster / *Dynamic SIDRA Discovery & Dagster Partitions* | Accepted | 2026-11-24 |
| [ADR-005](ADR-005-lightweight-mobile-layout-without-query-wrapper.md) | Layout Mobile Leve via CSS Puro e Reload Seletivo no Drawer / *Lightweight Mobile Layout without Query Wrapper* | Accepted | 2026-11-25 |
| [ADR-006](ADR-006-strict-ibge-immediate-region-boundaries.md) | Delimitação Estrita por Região Geográfica Imediata do IBGE / *Strict IBGE Immediate Region Boundaries* | Accepted | 2026-11-25 |

---

## Ciclo de Vida e Convenções / Lifecycle & Conventions

```text
Proposed -> Accepted -> (Superseded by ADR-NNN | Deprecated)
```

- **Nunca apagar ADRs antigos / Never delete old ADRs:** decisões superadas permanecem no repositório com status atualizado para preservar o contexto histórico.
- **Convenção de nomenclatura / Naming convention:** `docs/decisions/ADR-NNN-kebab-case-title.md` com seções `Status`, `Date`, `Context`, `Decision`, `Alternatives Considered` e `Consequences`.
