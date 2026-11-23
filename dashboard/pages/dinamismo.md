---
title: Dinamismo Econômico & Estrutura Produtiva (VAB / HHI)
---

Crescimento real composto do PIB (**CAGR 3 anos deflacionado pelo IPCA**), contraste da **composição setorial do Valor Adicionado Bruto (VAB)** entre regiões e relação entre poder de compra per capita e maturidade de mercado.

```sql ufs_dinamismo
select 'TODAS' as sigla_uf, 0 as ordem
union all
select distinct sigla_uf, 1 as ordem
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
order by ordem, sigla_uf
```

<Grid cols=2>
    <div>
        <Dropdown data={ufs_dinamismo} name=uf value=sigla_uf title="UF" defaultValue="TODAS" />
    </div>
    <div>
        <Slider name=min_pop_din title="População Mínima" min=0 max=200000 step=10000 defaultValue=50000 fmt="#,##0" size=full />
    </div>
</Grid>

```sql top_cagr
with base as (
    select
        nome_municipio || ' - ' || sigla_uf as municipio,
        round(cagr_pib_real_3a_pct / 100.0, 4) as cagr_3a_pct,
        row_number() over (order by cagr_pib_real_3a_pct desc) as pos
    from sidralake.mart_inteligencia_mercado_municipal
    where is_ultimo_ano_completo
      and coalesce(populacao_residente, 0) >= coalesce(try_cast('${inputs.min_pop_din}' as double), 50000)
      and cagr_pib_real_3a_pct is not null
      and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
    order by pos asc
    limit 12
)
select
    municipio,
    cagr_3a_pct,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from base
order by pos asc
```

```sql vab_empilhado_regiao
with ult_vab as (
    select
        nome_regiao as regiao,
        round(avg(share_vab_servicos_privados), 4) as servicos,
        round(avg(share_vab_agropecuaria), 4) as agropecuaria,
        round(avg(share_vab_industria), 4) as industria,
        round(avg(share_vab_adm_publica), 4) as adm_publica
    from sidralake.mart_inteligencia_mercado_municipal
    where ano_referencia = (
        select max(ano_referencia)
        from sidralake.mart_inteligencia_mercado_municipal
        where indice_diversificacao_setorial is not null
    )
      and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
    group by 1
)
select regiao, 'Serviços' as setor, servicos as share from ult_vab
union all select regiao, 'Agro', agropecuaria from ult_vab
union all select regiao, 'Indústria', industria from ult_vab
union all select regiao, 'Adm. Púb.', adm_publica from ult_vab
order by regiao asc
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
        stackTotalLabel=false
        labelPosition=outside
        showAllLabels=true
        labelFmt="0.0%"
        leftPadding=28
        rightPadding=34
        legend=false
        yGridlines=false
        xGridlines=false
        yAxisLabels=false
        yBaseline=false
        seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525866'}}
        title="Quais municípios mais cresceram?"
        subtitle="CAGR real 3 anos · Líder em azul"
    />
    <BarChart
        data={vab_empilhado_regiao}
        x=regiao
        y=share
        series=setor
        type=stacked100
        swapXY=true
        leftPadding=20
        rightPadding=16
        yGridlines=false
        xGridlines=false
        yAxisLabels=false
        yBaseline=false
        seriesColors={{'Serviços': '#3b82f6', 'Agro': '#10b981', 'Indústria': '#f59e0b', 'Adm. Púb.': '#525866'}}
        title="Composição setorial do VAB por Região"
        subtitle="Proporção 100% · Último VAB IBGE (2021)"
    />
</Grid>

---

## Poder de Compra (PIB Per Capita Real) × Score IMS

```sql scatter_poder_compra
select
    nome_municipio || ' - ' || sigla_uf as municipio,
    case
        when tier_mercado = 'Tier 1 - Polo Nacional' then 'Tier 1 · Polo'
        else 'Demais Municípios'
    end as grupo_tier,
    round(pib_per_capita_real_brl, 0) as pib_per_capita_real,
    ims_score_0_100 as ims
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
  and coalesce(populacao_residente, 0) >= coalesce(try_cast('${inputs.min_pop_din}' as double), 50000)
  and pib_per_capita_real_brl is not null
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
    xFmt="#,##0"
    yGridlines=false
    xGridlines=false
    seriesColors={{'Tier 1 · Polo': '#3b82f6', 'Demais Municípios': '#525866'}}
    title="Polos Nacionais (Tier 1) em destaque azul frente aos demais municípios"
    xAxisTitle="PIB Per Capita Real (R$)"
    yAxisTitle="Score IMS (0-100)"
/>

---

## Estrutura Produtiva Média por UF (Último VAB Publicado — 2021)

```sql vab_por_uf
select
    cast(max(ano_referencia) as varchar) as ano,
    sigla_uf as uf,
    nome_regiao as regiao,
    count(*) as municipios,
    round(avg(share_vab_agropecuaria), 4) as agro_pct,
    round(avg(share_vab_industria), 4) as ind_pct,
    round(avg(share_vab_servicos_privados), 4) as servicos_pct,
    round(avg(share_vab_adm_publica), 4) as adm_pub_pct,
    round(avg(indice_diversificacao_setorial), 3) as hhi_div
from sidralake.mart_inteligencia_mercado_municipal
where ano_referencia = (
    select max(ano_referencia)
    from sidralake.mart_inteligencia_mercado_municipal
    where indice_diversificacao_setorial is not null
)
  and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
group by 2, 3
order by hhi_div desc
```

<DataTable data={vab_por_uf} search=true rows=15 />
