> 🌐 **Idioma:** **Português (BR)** | [English](../../en/explanation/market-intelligence-methodology.md) · [Índice](../README.md)

# Metodologia de Inteligência de Mercado

Este documento explica os fundamentos econômicos e estatísticos aplicados nas camadas Silver e Gold para transformar séries brutas do IBGE em indicadores comparáveis de atratividade municipal, especialização setorial e pulso do varejo.

---

## 1. Deflação Monetária pelo IPCA (Preços Constantes)

Comparar PIB municipal ou massa salarial entre 2018 e 2024 em valores nominais distorce crescimentos reais devido à inflação acumulada no período.

No modelo `int_ipca_deflator_anual`, utilizamos o número-índice mensal oficial do IPCA (SIDRA `1737`, variável `2266`, base dez/1993 = 100):
- **Deflator mensal**: `numero_indice_base_atual / numero_indice_ipca`, onde `base_atual` é o último mês disponível na série do IPCA (`ano_mes_base_deflator`).
- **Deflator médio anual**: `numero_indice_base_atual / avg(numero_indice_ipca)` por `ano_referencia`.

Multiplicar grandezas nominais (`pib_nominal_mil_brl`, `massa_salarial_nominal_mil_brl`, `salario_medio_nominal_brl`) pelo fator anual traz toda a série histórica para **Reais constantes do mesmo poder de compra**, tornando válidos o cálculo de crescimento real anual (`YoY`) e a Taxa Composta de Crescimento Anual de 3 anos (`cagr_pib_real_3a_pct`).

---

## 2. Unificação Populacional e Lacuna Censitária de 2023

As séries demográficas oficiais do IBGE possuem duas origens:
- **Censo Demográfico 2022 (`4714`)**: fornece população residente, área territorial (`area_km2`) e densidade para 2022.
- **Estimativas de População (`6579`)**: cobrem 2001–2021 e retornam em 2024–2026, deixando **2023 sem publicação anual**.

Para evitar buracos em métricas *per capita* no ano de 2023 (`int_populacao_municipal_unificada`):
1. Propagamos `area_km2` da referência censitária de 2022 para todos os anos e recalculamos `densidade_demografica = populacao_residente / area_km2`.
2. Estimamos `2023` por **interpolação linear** exata entre o Censo 2022 e a Estimativa 2024 (`round((pop_2022 + pop_2024) / 2.0)`).
3. Marcamos explicitamente a rastreabilidade em `origem_dado` (`CENSO_2022`, `ESTIMATIVA_IBGE`, `INTERPOLACAO_LINEAR`) e `is_interpolado`.

---

## 3. Concentração e Diversificação Setorial (HHI)

Em `int_pib_municipal_deflacionado`, calculamos a participação de cada um dos 4 grandes agregados de Valor Adicionado Bruto (`share_vab_agropecuaria`, `share_vab_industria`, `share_vab_servicos_privados`, `share_vab_adm_publica`) e derivamos o **Índice de Herfindahl-Hirschman (`hhi_setorial`)**:

$$\text{HHI} = \sum_{i=1}^{4} s_i^2$$

- Quando a economia depende quase integralmente de um único setor (ex.: município estritamente agrícola ou dependente de administração pública), `HHI` aproxima-se de `1.0`.
- Quando os 4 setores têm peso equilibrado (`0.25` cada), `HHI = 0.25`.
- O complementar `indice_diversificacao_setorial = 1 - HHI` premia mercados locais com base econômica mais resiliente e menos concentrada.

---

## 4. Índice de Atratividade e Potencial de Mercado (`IMS`, 0–100)

Construído em `mart_inteligencia_mercado_municipal`, o **Score IMS** ranqueia todos os municípios brasileiros dentro de cada `ano_referencia` em quatro pilares configuráveis:

| Pilar | Peso Padrão | Variáveis Componentes | Tratamento Estatístico |
| :--- | :---: | :--- | :--- |
| **Tamanho de Mercado** | `0.35` | PIB Real, População Residente, Massa Salarial Real | `ln(1 + x)` + winsorização `P1–P99` |
| **Poder de Compra** | `0.30` | PIB per Capita Real, Salário Médio Real | `ln(1 + PIB pc)` e salário em `P1–P99` |
| **Dinamismo Econômico** | `0.20` | CAGR 3a (ou YoY) do PIB Real, Crescimento YoY de Empresas e Emprego | Winsorização `P5–P95` |
| **Maturidade Empresarial** | `0.15` | Empresas por 1.000 hab., Taxa de Assalariamento Formal, `1 - HHI` | Winsorização `P1–P99` |

### Por Que Logaritmo + Winsorização por Percentis?
Sem transformação logarítmica e sem cortes em percentis (`normalize_winsorized` em `dbt_project/macros/normalize_percentile.sql`), outliers extremos como São Paulo/SP empurrariam a normalização min-max linear de quase todos os demais 5.570 municípios para próximo de zero. Usar `ln(1 + x)` em escalas de grandeza e limitar a faixa de referência entre `P1–P99` (ou `P5–P95` em taxas de variação voláteis) preserva o poder discriminatório da escala `[0, 100]` do interior às metrópoles.

### Reponderação em Anos Parciais
Em anos anteriores a 2022 (quando não há a nova série CEMPRE `9509`) ou em 2024 (ainda sem PIB `5938`), os pilares ausentes ficam nulos e o denominador da média ponderada ajusta-se automaticamente para a soma dos pesos dos pilares disponíveis, mantendo a pontuação na escala `0–100`.

> **Atenção para comparações longitudinais:** Embora a reponderação preserve a escala `0–100` dentro de cada ano, pontuações calculadas com combinações diferentes de pilares (por exemplo, um ano sem PIB comparado a um ano com PIB e CEMPRE) **não são diretamente comparáveis** como variação ano contra ano (YoY). Para análises históricas consistentes do Score IMS, compare apenas anos com a mesma cobertura de pilares (como `2022` vs `2023`, ou filtre `is_ultimo_ano_completo = true` para o ranking consolidado). Veja também [`ADR-002`](../../decisions/ADR-002-ipca-deflation-and-winsorized-ims-scoring.md).

### Classificação em Níveis Estratégicos (*Tiers*)
Com base em `percent_rank()` anual de `ims_score_0_100`:
- **Tier 1 - Polo Nacional** (`percentil >= 0.98`, Top 2%)
- **Tier 2 - Expansão Prioritária** (`0.90 <= percentil < 0.98`, Top 10%)
- **Tier 3 - Emergente** (`0.65 <= percentil < 0.90`, Top 35%)
- **Tier 4 - Local / Nicho** (`percentil < 0.65`)

---

## 5. Quociente Locacional (`QL`) e Clusters Setoriais

Em `mart_clusters_setoriais_uf`, medimos a concentração relativa de cada seção CNAE 2.0 (`A–U`) por UF usando o **Quociente Locacional (`QL`)** clássico da economia regional:

$$\text{QL}_{uf, setor} = \frac{\text{Emprego}_{uf, setor} / \text{Emprego}_{uf}}{\text{Emprego}_{BR, setor} / \text{Emprego}_{BR}}$$

Calculado tanto por pessoal ocupado (`quociente_locacional_emprego`) quanto por massa salarial (`quociente_locacional_massa_salarial`):
- **`QL >= 1.50` (`CLUSTER_DOMINANTE`)**: forte vocação/concentração produtiva na UF (ex.: Extrativa no RJ, Financeira no DF, Agro no MT/MS).
- **`1.25 <= QL < 1.50` (`CLUSTER_ESPECIALIZADO`)**: especialização relevante acima da média nacional.
- **`0.85 <= QL < 1.25` (`EQUILIBRADO_MEDIA_NACIONAL`)**: aderência próxima à estrutura brasileira.
- **`QL < 0.85` (`SUB_REPRESENTADO`)**: baixa densidade setorial relativa.
- Quando há omissão por sigilo (`X`) na célula do CEMPRE, `has_sigilo_estatistico = true` sinaliza a restrição ao consumidor.

---

## 6. Pulso do Varejo (`PMC × IPCA`) e Regimes de Consumo

Em `mart_pulso_consumo_macro`, cruzamos receita nominal e volume de vendas por UF e atividade comercial (PMC `8883`) com a inflação oficial (IPCA `1737`):
- **`spread_preco_vs_volume_yoy_pp`** (`var_yoy_receita_nominal_pct - var_yoy_volume_pct`): aproxima o quanto o crescimento do faturamento nominal decorre de repasse de preços versus demanda física real.
- **Médias móveis 3m e 12m** sobre `indice_volume_vendas` suavizam sazonalidades do varejo.
- **`regime_consumo`** classifica cada UF × Atividade × Mês em:
  - `EXPANSAO_REAL`: variação YoY do volume `> +2.0%`
  - `PRESSAO_INFLACIONARIA`: volume estagnado/positivo (`>= 0.0%`), porém com spread receita-volume `> +4.0 pp`
  - `ESTABILIDADE`: variação YoY do volume entre `-2.0%` e `+2.0%` sem pressão inflacionária severa
  - `RETRACAO`: queda real de volume (`< -2.0%`)

---

## 7. Pulso Mensal de Serviços (`PMS × IPCA`)

Em `mart_pulso_servicos_uf`, aplicamos a mesma leitura cíclica à Pesquisa Mensal de Serviços (`SIDRA 5906`, `N3`, índice base 2022 = 100 em receita nominal e volume):
- **Ajuste sazonal e médias móveis**: incorpora variação mês contra mês dessazonalizada (`var_mom_sa_volume_pct`) e médias móveis de 3m/12m sobre `indice_volume_servicos`.
- **Spreads e regimes (`regime_servicos`)**: calcula `spread_preco_vs_volume_yoy_pp` e `spread_volume_vs_ipca_12m_pp`, classificando cada UF × Mês em `EXPANSAO_REAL`, `PRESSAO_INFLACIONARIA`, `ESTABILIDADE`, `RETRACAO` ou `SEM_DADO` sob o mesmo critério do varejo.

---

## 8. Mercado de Trabalho e Hiato Salarial (`PNAD Contínua`)

Em `mart_mercado_trabalho_uf`, consolidamos séries trimestrais estaduais (`2018+`) da PNAD Contínua abrangendo mercado formal e informal:
- **Subutilização da força de trabalho (`SIDRA 4099`)**: `taxa_desocupacao_pct` (`4099`), `taxa_desocupacao_subocupacao_pct` (`4114`), `taxa_desocupacao_forca_potencial_pct` (`4116`), `taxa_subutilizacao_composta_pct` (`4118`) e variação interanual `var_yoy_desocupacao_pp`.
- **Rendimento real habitual (`SIDRA 5436`, variável `5933`)**: médio total, homens e mulheres, além do crescimento real `var_yoy_rendimento_real_pct` e do `hiato_salarial_genero_pct = ((mulheres - homens) / homens) * 100.0`.

---

## 9. Demografia Municipal e Regiões Geográficas Imediatas

Em `mart_demografia_municipal`, consolidamos o perfil populacional corrente dos municípios ativos com **linha de base estrita no Censo Demográfico 2022**:
- **Sem substituição silenciosa de base**: `populacao_censo_2022` reflete exclusivamente `ano_referencia = 2022` para calcular `saldo_populacional_desde_2022`, `crescimento_populacional_desde_2022_pct` e `rank_populacao_uf`.
- **Aderência às Regiões Geográficas Imediatas (RGIs)**: comparações regionais no Raio-X Municipal agrupam estritamente por `nome_regiao_imediata` do IBGE (ex.: *Amparo-SP* na RGI *Amparo* com 5 cidades e *Pedreira-SP* na RGI *Campinas* com 18 cidades, embora ambas integrem a Região Intermediária *Campinas*). Detalhes em [`ADR-006`](../../decisions/ADR-006-strict-ibge-immediate-region-boundaries.md).
