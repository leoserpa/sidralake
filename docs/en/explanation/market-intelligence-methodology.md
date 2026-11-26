> 🌐 **Language:** [Português (BR)](../../pt-br/explicacoes/metodologia-inteligencia-de-mercado.md) | **English** · [Index](../README.md)

# Market Intelligence Methodology

This document explains the economic and statistical rationale implemented in the Silver and Gold layers to convert raw IBGE series into comparable indicators of municipal attractiveness, sectoral specialization, and retail momentum.

---

## 1. Monetary Deflation via IPCA (Constant Prices)

Comparing nominal municipal GDP or payroll figures between 2018 and 2024 distorts real economic growth because of cumulative inflation over the period.

In `int_ipca_deflator_anual`, the pipeline uses the official monthly IPCA index number (SIDRA `1737`, variable `2266`, base Dec/1993 = 100):
- **Monthly deflator**: `numero_indice_base_atual / numero_indice_ipca`, where `base_atual` is the latest IPCA month available (`ano_mes_base_deflator`).
- **Annual average deflator**: `numero_indice_base_atual / avg(numero_indice_ipca)` per `ano_referencia`.

Multiplying nominal figures (`pib_nominal_mil_brl`, `massa_salarial_nominal_mil_brl`, `salario_medio_nominal_brl`) by the annual factor expresses the entire historical series in **constant BRL of equal purchasing power**, ensuring valid YoY real growth and 3-year Compound Annual Growth Rate (`cagr_pib_real_3a_pct`) comparisons.

---

## 2. Population Series Unification and the 2023 Census Gap

Official IBGE municipal population series come from two sources:
- **2022 Demographic Census (`4714`)**: provides resident population, territorial area (`area_km2`), and density for 2022.
- **Annual Population Estimates (`6579`)**: cover 2001–2021 and resume in 2024–2026, leaving **2023 without an official annual estimate**.

To avoid missing per-capita denominators in 2023 (`int_populacao_municipal_unificada`):
1. `area_km2` from the 2022 Census is propagated across all years and `densidade_demografica = populacao_residente / area_km2` is recomputed consistently.
2. Year `2023` is derived via exact **linear interpolation** between the 2022 Census and the 2024 Estimate (`round((pop_2022 + pop_2024) / 2.0)`).
3. Lineage stays transparent through `origem_dado` (`CENSO_2022`, `ESTIMATIVA_IBGE`, `INTERPOLACAO_LINEAR`) and `is_interpolado`.

---

## 3. Sectoral Concentration and Diversification (HHI)

In `int_pib_municipal_deflacionado`, the pipeline computes GVA shares across the four main macroeconomic sectors (`share_vab_agropecuaria`, `share_vab_industria`, `share_vab_servicos_privados`, `share_vab_adm_publica`) and derives the **Herfindahl-Hirschman Index (`hhi_setorial`)**:

$$\text{HHI} = \sum_{i=1}^{4} s_i^2$$

- Economies heavily dependent on a single sector approach `HHI = 1.0`.
- A perfectly balanced 4-sector distribution (`0.25` each) yields `HHI = 0.25`.
- The complement `indice_diversificacao_setorial = 1 - HHI` rewards local markets with broader, more resilient economic foundations.

---

## 4. Market Attractiveness Index (`IMS`, 0–100 Scale)

Computed in `mart_inteligencia_mercado_municipal`, the **IMS Score** ranks all Brazilian municipalities per `ano_referencia` across four configurable pillars:

| Pillar | Default Weight | Component Metrics | Statistical Treatment |
| :--- | :---: | :--- | :--- |
| **Market Size** | `0.35` | Real GDP, Resident Population, Real Payroll | `ln(1 + x)` + `P1–P99` winsorization |
| **Purchasing Power** | `0.30` | Real GDP per Capita, Real Average Wage | `ln(1 + GDP pc)` and wage at `P1–P99` |
| **Economic Dynamism** | `0.20` | Real GDP 3y CAGR (or YoY), Firm & Job YoY Growth | `P5–P95` winsorization |
| **Business Maturity** | `0.15` | Firms per 1,000 residents, Formal Employment Rate, `1 - HHI` | `P1–P99` winsorization |

### Why Logarithms + Percentile Winsorization?
Without log scaling and percentile clipping (`normalize_winsorized` in `dbt_project/macros/normalize_percentile.sql`), extreme outliers like São Paulo/SP would compress linear min-max scores for nearly all other 5,570 municipalities near zero. Combining `ln(1 + x)` on magnitude variables with `P1–P99` (and `P5–P95` for volatile growth rates) preserves meaningful spread across the entire `[0, 100]` scale.

### Graceful Re-Weighting on Partial Years
For pre-2022 years (before the active CEMPRE `9509` series) or 2024 (prior to GDP `5938` release), missing pillars remain `NULL` and the weighted average divides strictly by the sum of weights of available pillars, keeping scores bounded on the `[0, 100]` scale.

> **Caution for longitudinal comparisons:** Although re-weighting keeps scores on the `0–100` scale within each year, scores computed from different active pillar subsets (for example, a year without GDP compared against a year with both GDP and CEMPRE) are **not directly comparable** as a consistent year-over-year change. For longitudinal IMS comparisons, compare only years with identical pillar coverage (such as `2022` vs `2023`, or filter `is_ultimo_ano_completo = true` for the latest complete cross-sectional ranking). See also [`ADR-002`](../../decisions/ADR-002-ipca-deflation-and-winsorized-ims-scoring.md).

### Strategic Tier Classification
Using annual `percent_rank()` over `ims_score_0_100`:
- **Tier 1 - Polo Nacional** (`percentile >= 0.98`, Top 2%)
- **Tier 2 - Expansao Prioritaria** (`0.90 <= percentile < 0.98`, Top 10%)
- **Tier 3 - Emergente** (`0.65 <= percentile < 0.90`, Top 35%)
- **Tier 4 - Local / Nicho** (`percentile < 0.65`)

---

## 5. Location Quotient (`LQ`) and Sector Clusters

In `mart_clusters_setoriais_uf`, relative specialization of each CNAE 2.0 section (`A–U`) per state (`UF`) is measured via the classic regional economics **Location Quotient (`QL`)**:

$$\text{LQ}_{state, sector} = \frac{\text{Employment}_{state, sector} / \text{Employment}_{state}}{\text{Employment}_{BR, sector} / \text{Employment}_{BR}}$$

Computed for both headcount (`quociente_locacional_emprego`) and real payroll (`quociente_locacional_massa_salarial`):
- **`LQ >= 1.50` (`CLUSTER_DOMINANTE`)**: dominant regional hub (e.g., Extractive Industries in RJ, Finance in DF, Agriculture in MT/MS).
- **`1.25 <= LQ < 1.50` (`CLUSTER_ESPECIALIZADO`)**: significant specialization above the national share.
- **`0.85 <= LQ < 1.25` (`EQUILIBRADO_MEDIA_NACIONAL`)**: aligned with national economic composition.
- **`LQ < 0.85` (`SUB_REPRESENTADO`)**: below national concentration.
- When IBGE suppresses sensitive values (`X`), `has_sigilo_estatistico = true` surfaces the constraint downstream.

---

## 6. Retail Consumption Pulse (`PMC × IPCA`)

In `mart_pulso_consumo_macro`, state-level nominal retail revenue and sales volume across 14 activities (PMC `8883`) are joined with monthly inflation (IPCA `1737`):
- **`spread_preco_vs_volume_yoy_pp`** (`var_yoy_receita_nominal_pct - var_yoy_volume_pct`): separates price-driven nominal revenue growth from real physical unit demand.
- **3-month and 12-month moving averages** on `indice_volume_vendas` smooth seasonal retail spikes.
- **`regime_consumo`** classifies each State × Activity × Month into:
  - `EXPANSAO_REAL`: YoY volume growth `> +2.0%`
  - `PRESSAO_INFLACIONARIA`: flat/positive volume (`>= 0.0%`) coupled with a nominal-vs-volume spread `> +4.0 pp`
  - `ESTABILIDADE`: YoY volume between `-2.0%` and `+2.0%` without severe price spread
  - `RETRACAO`: real volume contraction (`< -2.0%`)

---

## 7. Monthly Services Pulse (`PMS × IPCA`)

In `mart_pulso_servicos_uf`, the same cyclical framework evaluates IBGE's Monthly Services Survey (`SIDRA 5906`, `N3`, base 2022 = 100 across nominal revenue and service volume):
- **Seasonally adjusted momentum & smoothing**: captures `var_mom_sa_volume_pct` and 3-month / 12-month moving averages over `indice_volume_servicos`.
- **Spreads and regimes (`regime_servicos`)**: computes `spread_preco_vs_volume_yoy_pp` and `spread_volume_vs_ipca_12m_pp`, classifying each State × Month into `EXPANSAO_REAL`, `PRESSAO_INFLACIONARIA`, `ESTABILIDADE`, `RETRACAO`, or `SEM_DADO`.

---

## 8. Labor Market & Gender Earnings Gap (`PNAD Contínua`)

In `mart_mercado_trabalho_uf`, quarterly state-level labor series (`2018+`) combine formal and informal employment metrics:
- **Labor underutilization (`SIDRA 4099`)**: `taxa_desocupacao_pct` (`4099`), `taxa_desocupacao_subocupacao_pct` (`4114`), `taxa_desocupacao_forca_potencial_pct` (`4116`), `taxa_subutilizacao_composta_pct` (`4118`), and year-over-year point change `var_yoy_desocupacao_pp`.
- **Habitual real earnings (`SIDRA 5436`, variable `5933`)**: total, men, and women average real monthly earnings, real YoY wage growth (`var_yoy_rendimento_real_pct`), and `hiato_salarial_genero_pct = ((women - men) / men) * 100.0`.

---

## 9. Municipal Demographics & Official Immediate Regions

In `mart_demografia_municipal`, current municipal demographics are joined strictly against the **2022 Census baseline**:
- **Strict 2022 Census baseline**: `populacao_censo_2022` filters strictly to `ano_referencia = 2022` (no fallback to later years) when computing `saldo_populacional_desde_2022`, `crescimento_populacional_desde_2022_pct`, and `rank_populacao_uf`.
- **Strict adherence to IBGE Immediate Regions**: regional peer tables in `/municipio/` filter strictly on `nome_regiao_imediata` (for example, *Amparo-SP* in RGI *Amparo* [5 cities] vs. *Pedreira-SP* in RGI *Campinas* [18 cities], which share only Intermediate Region *Campinas*). See [`ADR-006`](../../decisions/ADR-006-strict-ibge-immediate-region-boundaries.md).
