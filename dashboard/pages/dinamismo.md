---
title: Dinamismo Econômico & Diversificação (HHI)
---

Análise de crescimento real composto (**CAGR 3 anos deflacionado pelo IPCA**), poder de compra per capita e **diversificação produtiva (`1 - HHI`)** com destaque visual nos líderes de expansão e resiliência setorial.

```sql ufs_dinamismo
select 'TODAS' as sigla_uf, 0 as ordem
union all
select distinct sigla_uf, 1 as ordem
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
order by ordem, sigla_uf
```

<Dropdown data={ufs_dinamismo} name=uf value=sigla_uf title="UF" defaultValue="TODAS" />

```sql top_cagr
with base as (
    select
        nome_municipio || ' - ' || sigla_uf as municipio,
        sigla_uf as uf,
        nome_regiao as regiao,
        populacao_residente as populacao,
        round(cagr_pib_real_3a_pct, 1) as cagr_3a_pct,
        round(pib_real_mil_brl / 1e6, 2) as pib_real_bi,
        round(indice_diversificacao_setorial, 3) as diversificacao_1_hhi,
        ims_score_0_100 as ims,
        row_number() over (order by cagr_pib_real_3a_pct desc) as pos
    from sidralake.mart_inteligencia_mercado_municipal
    where is_ultimo_ano_completo
      and populacao_residente >= 50000
      and cagr_pib_real_3a_pct is not null
      and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
    order by pos asc
    limit 12
)
select
    municipio,
    uf,
    regiao,
    populacao,
    cagr_3a_pct,
    pib_real_bi,
    diversificacao_1_hhi,
    ims,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from base
order by pos asc
```

```sql vab_por_regiao
with agg as (
    select
        nome_regiao as regiao,
        round(avg(share_vab_agropecuaria) * 100, 1) as agropecuaria_pct,
        round(avg(share_vab_industria) * 100, 1) as industria_pct,
        round(avg(share_vab_servicos_privados) * 100, 1) as servicos_privados_pct,
        round(avg(share_vab_adm_publica) * 100, 1) as adm_publica_pct,
        round(avg(indice_diversificacao_setorial), 3) as diversificacao_media
    from sidralake.mart_inteligencia_mercado_municipal
    where is_ultimo_ano_completo
      and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
    group by 1
),
ranked as (
    select
        *,
        row_number() over (order by diversificacao_media desc nulls last) as pos
    from agg
)
select
    regiao,
    agropecuaria_pct,
    industria_pct,
    servicos_privados_pct,
    adm_publica_pct,
    diversificacao_media,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from ranked
order by pos asc
```

<Grid cols=2>
    <BarChart
        data={top_cagr}
        x=municipio
        y=cagr_3a_pct
        series=destaque
        type=stacked
        swapXY=true
        sort=false
        labels=true
        labelPosition=outside
        showAllLabels=true
        labelFmt="0.0"
        legend=false
        yGridlines=false
        xGridlines=false
        yAxisLabels=false
        yBaseline=false
        seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525866'}}
        title="Quais municípios mais cresceram em PIB real?"
        subtitle="CAGR real 3 anos (%) · População >= 50 mil · Líder em destaque"
    />
    <BarChart
        data={vab_por_regiao}
        x=regiao
        y=diversificacao_media
        series=destaque
        type=stacked
        swapXY=true
        sort=false
        labels=true
        labelPosition=outside
        showAllLabels=true
        labelFmt="0.000"
        legend=false
        yGridlines=false
        xGridlines=false
        yAxisLabels=false
        yBaseline=false
        seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525866'}}
        title="Quais regiões são mais diversificadas?"
        subtitle="Índice médio de diversificação produtiva (1 − HHI) · Líder em destaque"
    />
</Grid>

---

## Onde está o maior poder de compra (PIB Per Capita Real × Score IMS)?

```sql scatter_poder_compra
select
    nome_municipio || ' - ' || sigla_uf as municipio,
    case
        when tier_mercado = 'Tier 1 - Polo Nacional' then 'Tier 1 - Polo Nacional'
        else 'Demais Municípios'
    end as grupo_tier,
    round(pib_per_capita_real_brl, 0) as pib_per_capita_real,
    ims_score_0_100 as ims
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
  and populacao_residente >= 50000
  and pib_per_capita_real_brl is not null
  and pib_per_capita_real_brl <= 400000
  and ims_score_0_100 is not null
  and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
order by ims_score_0_100 desc
limit 500
```

<ScatterPlot
    data={scatter_poder_compra}
    x=pib_per_capita_real
    y=ims
    series=grupo_tier
    tooltipTitle=municipio
    yGridlines=false
    xGridlines=false
    seriesColors={{'Tier 1 - Polo Nacional': '#3b82f6', 'Demais Municípios': '#525866'}}
    title="Municípios (>= 50 mil hab.): Polos Nacionais (Tier 1) em destaque azul"
    xAxisTitle="PIB Per Capita Real (R$)"
    yAxisTitle="Score IMS (0-100)"
/>

---

## Estrutura Produtiva por Região e Detalhamento de Crescimento

<DataTable data={vab_por_regiao} />

<DataTable data={top_cagr} search=true rows=15 />
