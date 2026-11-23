---
title: SidraLake 360° — Inteligência de Mercado IBGE
---

Visão executiva dos **5.571 municípios brasileiros** a partir da camada **Gold** do **SidraLake** (PIB Real deflacionado pelo IPCA, Censo 2022 + Estimativas, CEMPRE e PMC), desenhada sob princípios de **alto Data-Ink Ratio** — destaque pré-atentivo em azul no líder de cada análise e foco imediato na tomada de decisão.

```sql regioes_disponiveis
select 'TODAS' as nome_regiao, 0 as ordem
union all
select distinct nome_regiao, 1 as ordem
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
order by ordem, nome_regiao
```

```sql ufs_disponiveis
select 'TODAS' as sigla_uf, 0 as ordem
union all
select distinct sigla_uf, 1 as ordem
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
order by ordem, sigla_uf
```

```sql tiers_disponiveis
select 'TODOS' as tier_mercado, 0 as ordem
union all
select distinct tier_mercado, 1 as ordem
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
order by ordem, tier_mercado
```

<Dropdown data={regioes_disponiveis} name=regiao value=nome_regiao title="Grande Região" defaultValue="TODAS" />
<Dropdown data={ufs_disponiveis} name=uf value=sigla_uf title="UF" defaultValue="TODAS" />
<Dropdown data={tiers_disponiveis} name=tier value=tier_mercado title="Tier de Mercado" defaultValue="TODOS" />

```sql kpis_gerais
select
    count(*) as total_municipios,
    max(ano_referencia) as ano_base,
    sum(populacao_residente) as populacao_total,
    sum(pib_real_mil_brl) / 1e9 as pib_real_tri,
    sum(massa_salarial_real_mil_brl) / 1e6 as massa_salarial_bi,
    sum(num_empresas_atuantes) as empresas_atuantes,
    round(avg(ims_score_0_100), 2) as ims_medio
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
  and ('${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}')
  and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
  and ('${inputs.tier.value}' = 'TODOS' or tier_mercado = '${inputs.tier.value}')
```

<BigValue data={kpis_gerais} value=total_municipios title="Municípios no Recorte" fmt="#,##0" />
<BigValue data={kpis_gerais} value=pib_real_tri title="PIB Real Total (R$ Tri)" fmt="#,##0.00" />
<BigValue data={kpis_gerais} value=populacao_total title="População Residente" fmt="#,##0" />
<BigValue data={kpis_gerais} value=empresas_atuantes title="Empresas Atuantes" fmt="#,##0" />
<BigValue data={kpis_gerais} value=ims_medio title="Score IMS Médio" fmt="0.00" />

---

```sql top_12_ims
with base as (
    select
        rank_nacional_ims,
        nome_municipio || ' - ' || sigla_uf as municipio,
        round(ims_score_0_100, 2) as ims_score_0_100,
        row_number() over (order by ims_score_0_100 desc, pib_real_mil_brl desc) as pos
    from sidralake.mart_inteligencia_mercado_municipal
    where is_ultimo_ano_completo
      and ims_score_0_100 is not null
      and ('${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}')
      and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
      and ('${inputs.tier.value}' = 'TODOS' or tier_mercado = '${inputs.tier.value}')
    order by pos asc
    limit 12
)
select
    municipio,
    ims_score_0_100,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from base
order by pos asc
```

```sql top_12_pib
with base as (
    select
        nome_municipio || ' - ' || sigla_uf as municipio,
        round(pib_real_mil_brl / 1e6, 1) as pib_real_bi,
        row_number() over (order by pib_real_mil_brl desc) as pos
    from sidralake.mart_inteligencia_mercado_municipal
    where is_ultimo_ano_completo
      and pib_real_mil_brl is not null
      and ('${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}')
      and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
      and ('${inputs.tier.value}' = 'TODOS' or tier_mercado = '${inputs.tier.value}')
    order by pos asc
    limit 12
)
select
    municipio,
    pib_real_bi,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from base
order by pos asc
```

<Grid cols=2>
    <BarChart
        data={top_12_ims}
        x=municipio
        y=ims_score_0_100
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
        title="Quais municípios lideram o Score IMS?"
        subtitle="Índice de Mercado SidraLake (0–100) · Líder em destaque"
    />
    <BarChart
        data={top_12_pib}
        x=municipio
        y=pib_real_bi
        series=destaque
        type=stacked
        swapXY=true
        sort=false
        labels=true
        labelPosition=outside
        showAllLabels=true
        labelFmt="#,##0.0"
        legend=false
        yGridlines=false
        xGridlines=false
        yAxisLabels=false
        yBaseline=false
        seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525866'}}
        title="Quais municípios concentram maior PIB real?"
        subtitle="PIB real a preços constantes (R$ Bilhões) · Líder em destaque"
    />
</Grid>

---

```sql resumo_tiers
with agg as (
    select
        tier_mercado,
        count(*) as municipios,
        round(avg(ims_score_0_100), 2) as ims_medio,
        round(sum(pib_real_mil_brl) / 1e6, 1) as pib_real_bi,
        sum(populacao_residente) as populacao
    from sidralake.mart_inteligencia_mercado_municipal
    where is_ultimo_ano_completo
      and ('${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}')
      and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
    group by 1
),
ranked as (
    select
        *,
        row_number() over (order by pib_real_bi desc nulls last) as pos
    from agg
)
select
    tier_mercado,
    municipios,
    ims_medio,
    pib_real_bi,
    populacao,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from ranked
order by pos asc
```

```sql pib_por_regiao
with agg as (
    select
        nome_regiao as regiao,
        count(*) as municipios,
        round(sum(pib_real_mil_brl) / 1e6, 1) as pib_real_bi,
        round(avg(ims_score_0_100), 2) as ims_medio
    from sidralake.mart_inteligencia_mercado_municipal
    where is_ultimo_ano_completo
      and ('${inputs.tier.value}' = 'TODOS' or tier_mercado = '${inputs.tier.value}')
    group by 1
),
ranked as (
    select
        *,
        row_number() over (order by pib_real_bi desc nulls last) as pos
    from agg
)
select
    regiao,
    municipios,
    pib_real_bi,
    ims_medio,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from ranked
order by pos asc
```

<Grid cols=2>
    <BarChart
        data={resumo_tiers}
        x=tier_mercado
        y=pib_real_bi
        series=destaque
        type=stacked
        swapXY=true
        sort=false
        labels=true
        labelPosition=outside
        showAllLabels=true
        labelFmt="#,##0.0"
        legend=false
        yGridlines=false
        xGridlines=false
        yAxisLabels=false
        yBaseline=false
        seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525866'}}
        title="Onde se concentra o PIB real por Tier?"
        subtitle="PIB real acumulado (R$ Bilhões) por Tier estratégico"
    />
    <BarChart
        data={pib_por_regiao}
        x=regiao
        y=pib_real_bi
        series=destaque
        type=stacked
        swapXY=true
        sort=false
        labels=true
        labelPosition=outside
        showAllLabels=true
        labelFmt="#,##0.0"
        legend=false
        yGridlines=false
        xGridlines=false
        yAxisLabels=false
        yBaseline=false
        seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525866'}}
        title="Como o PIB real se distribui por Grande Região?"
        subtitle="PIB real acumulado (R$ Bilhões) · Região líder em destaque"
    />
</Grid>

---

## Explorador Completo de Municípios

```sql tabela_municipios
select
    rank_nacional_ims as rk_br,
    rank_estadual_ims as rk_uf,
    nome_municipio as municipio,
    sigla_uf as uf,
    nome_regiao as regiao,
    ano_referencia as ano,
    populacao_residente as populacao,
    round(pib_real_mil_brl / 1e6, 3) as pib_real_bi,
    round(pib_per_capita_real_brl, 0) as pib_pc_real,
    num_empresas_atuantes as empresas,
    round(salario_medio_real_brl, 0) as salario_medio_real,
    round(cagr_pib_real_3a_pct, 2) as cagr_3a_pct,
    ims_score_0_100 as ims,
    tier_mercado as tier
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
  and ('${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}')
  and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
  and ('${inputs.tier.value}' = 'TODOS' or tier_mercado = '${inputs.tier.value}')
order by rank_nacional_ims asc
```

<DataTable data={tabela_municipios} search=true rows=20 />

---

> **Fonte dos Dados:** Os dados primários pertencem ao **Instituto Brasileiro de Geografia e Estatística (IBGE)** e são de acesso público nos termos da Política de Dados Abertos do Governo Federal. Código-fonte licenciado sob **GNU GPL v3.0**.
