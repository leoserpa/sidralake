---
title: Pulso do Consumo Macro (PMC × IPCA)
---

Acompanhamento mensal do **Varejo Ampliado (PMC — SIDRA 8883)** cruzado com o **IPCA (SIDRA 1737)**, destacando o **Volume Real YoY (%)** em azul sobre a receita nominal e a inflação acumulada em 12 meses.

```sql ufs_pmc
select distinct sigla_uf
from sidralake.mart_pulso_consumo_macro
order by sigla_uf
```

```sql atividades_pmc
select distinct nome_atividade_pmc
from sidralake.mart_pulso_consumo_macro
order by nome_atividade_pmc
```

<Dropdown data={ufs_pmc} name=uf value=sigla_uf title="UF" defaultValue="SP" />
<Dropdown data={atividades_pmc} name=atividade value=nome_atividade_pmc title="Atividade Comercial (PMC)" defaultValue="Hipermercados e supermercados" />

```sql serie_mensal_pmc
select
    data_referencia,
    ano_mes,
    round(var_yoy_volume_pct, 2) as volume_yoy_pct,
    round(var_yoy_receita_nominal_pct, 2) as receita_yoy_pct,
    round(ipca_variacao_acum_12m_pct, 2) as ipca_12m_pct,
    round(spread_preco_vs_volume_yoy_pp, 2) as spread_preco_vol_pp,
    regime_consumo
from sidralake.mart_pulso_consumo_macro
where sigla_uf = '${inputs.uf.value}'
  and nome_atividade_pmc = '${inputs.atividade.value}'
  and var_yoy_volume_pct is not null
order by data_referencia asc
```

<LineChart
    data={serie_mensal_pmc}
    x=data_referencia
    y={["volume_yoy_pct", "receita_yoy_pct", "ipca_12m_pct"]}
    yGridlines=false
    xGridlines=false
    seriesColors={{'volume_yoy_pct': '#3b82f6', 'receita_yoy_pct': '#6b7280', 'ipca_12m_pct': '#f59e0b'}}
    title="Como o volume real do varejo evoluiu frente à inflação?"
    subtitle="Volume Real YoY em azul · Receita Nominal YoY em cinza · IPCA 12m em âmbar"
    yAxisTitle="Variação (%)"
/>

---

```sql regimes_ultimo_mes
with agg as (
    select
        regime_consumo,
        count(*) as series_uf_atividade,
        round(avg(var_yoy_volume_pct), 2) as vol_yoy_medio_pct,
        round(avg(spread_preco_vs_volume_yoy_pp), 2) as spread_medio_pp
    from sidralake.mart_pulso_consumo_macro
    where ano_mes = (select max(ano_mes) from sidralake.mart_pulso_consumo_macro)
      and regime_consumo <> 'SEM_DADO'
    group by 1
),
ranked as (
    select
        *,
        row_number() over (order by series_uf_atividade desc) as pos
    from agg
)
select
    regime_consumo,
    series_uf_atividade,
    vol_yoy_medio_pct,
    spread_medio_pp,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from ranked
order by pos asc
```

<BarChart
    data={regimes_ultimo_mes}
    x=regime_consumo
    y=series_uf_atividade
    series=destaque
    type=stacked
    swapXY=true
    sort=false
    labels=true
    labelPosition=outside
    showAllLabels=true
    labelFmt="#,##0"
    legend=false
    yGridlines=false
    xGridlines=false
    yAxisLabels=false
    yBaseline=false
    seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525866'}}
    title="Como o varejo nacional está distribuído por regime de consumo?"
    subtitle="Séries UF × Atividade na última competência · Regime predominante em destaque"
/>

<DataTable data={regimes_ultimo_mes} />

---

## Histórico Mensal Detalhado da Série Selecionada

<DataTable data={serie_mensal_pmc} search=true rows=15 />
