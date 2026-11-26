# ADR-002: Constant-Price IPCA Deflation, 2023 Linear Interpolation, and Winsorized IMS Scoring

## Status
Accepted

## Date
2026-11-23

## Context
Official IBGE indicators span incompatible temporal bases and skewed distributions:
- Municipal GDP (`SIDRA 5938`) and CEMPRE payroll/wages (`SIDRA 9509`) are published in nominal BRL, distorting multi-year comparisons due to inflation.
- The 2022 Demographic Census (`SIDRA 4714`) replaced the annual Population Estimate (`SIDRA 6579`), leaving year **2023 without an annual population release**, which breaks per-capita and entrepreneurship-density metrics.
- Municipal size metrics follow extreme power-law distributions (São Paulo/SP vs. rural municipalities with fewer than 2,000 residents), collapsing linear min-max scores near zero.
- CEMPRE `9509` starts in 2022 after a methodological break from discontinued `1685` (through 2021), while GDP municipal data lags behind population/CEMPRE releases in the latest year.

## Decision
1. **Constant-Price Deflation (`int_ipca_deflator_anual`):** Deflate all nominal municipal monetary series using the official monthly IPCA index number (`SIDRA 1737`, variable `2266`, base Dec/1993 = 100) referenced to the latest available IPCA month (`ano_mes_base_deflator`).
2. **Exact 2023 Linear Interpolation (`int_populacao_municipal_unificada`):** Propagate `area_km2` from the 2022 Census and derive 2023 population via `round((pop_2022 + pop_2024) / 2.0)`, recording explicit provenance (`CENSO_2022`, `ESTIMATIVA_IBGE`, `INTERPOLACAO_LINEAR`) and `is_interpolado`.
3. **4-Pillar Winsorized Score IMS (`mart_inteligencia_mercado_municipal`):** Normalize components using `ln(1 + x)` on magnitude indicators (GDP, population, payroll, GDP per capita) combined with percentile winsorization (`P1–P99` for levels, `P5–P95` for volatile YoY/CAGR growth rates via `normalize_winsorized`) using configurable pillar weights (`0.35` Market Size, `0.30` Purchasing Power, `0.20` Economic Dynamism, `0.15` Business Maturity).
4. **Partial-Year Weight Re-normalization:** When a pillar is absent in an incomplete year (pre-2022 before CEMPRE `9509`, or latest years awaiting GDP `5938`), divide the weighted sum strictly by the weights of available pillars so scores stay bounded in `[0, 100]`.

## Alternatives Considered

### Nominal Monetary Comparisons and Raw Linear Min-Max Scaling
- **Pros:** Simpler SQL without joining IPCA or computing percentile bounds.
- **Cons:** Multi-year GDP/wage growth conflates inflation with real expansion, and top-5 cities compress 99% of municipalities into `[0, 5]` on the `0–100` scale.
- **Rejected:** Fails analytical comparability across time and city tiers.

### Dropping 2023 Population Rows or Concatenating Legacy CEMPRE `1685`
- **Pros:** Avoids interpolation logic or partial-pillar re-weighting.
- **Cons:** Leaves 2023 GDP per capita `NULL` across all 5,570 municipalities, or introduces artificial discontinuities from the 2022 eSocial/RFB methodological break in CEMPRE.
- **Rejected:** Distorts economic rankings and growth rates.

## Consequences
- **Comparable real-term series:** Historical GDP, payroll, and wages share the same constant purchasing-power basis updated on each IPCA refresh.
- **Full-series continuity:** 2023 municipal per-capita indicators render cleanly without masking interpolation provenance (`origem_dado`, `is_interpolado`).
- **Explicit longitudinal caveat:** Because partial years use different active pillar subsets than complete years (when both GDP `5938` and CEMPRE `9509` exist), **scores across years with different pillar coverage are not directly comparable as year-over-year changes**. Cross-sectional rankings should filter `is_ultimo_ano_completo = true` or compare years with identical pillar coverage (e.g., `2022` vs. `2023`).
- **Testability:** Edge cases (2023 interpolation, negative GVA, incomplete pillars, winsorization bounds) are locked by dbt SQL `unit_tests` (`_intermediate.yml`, `_gold.yml`) and singular tests (`dbt_project/tests/`).
