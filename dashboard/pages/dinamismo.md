---
title: Dinamismo Econômico & Diversificação (HHI)
---

Análise de crescimento real do PIB (**CAGR 3 anos deflacionado pelo IPCA**), poder de compra per capita e **diversificação produtiva (`1 - HHI`)** entre Agropecuária, Indústria, Serviços Privados e Administração Pública.

```sql ufs_dinamismo
select 'TODAS' as sigla_uf, 0 as ordem
union all
select distinct sigla_uf, 1 as ordem
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
order by ordem, sigla_uf
```

<Dropdown data={ufs_dinamismo} name=uf value=sigla_uf title="UF" defaultValue="TODAS" />

## Top 20 Municípios em Dinamismo Real (CAGR PIB 3 Anos, Pop >= 50 mil)

```sql top_cagr
select
    nome_municipio || ' - ' || sigla_uf as municipio,
    sigla_uf as uf,
    nome_regiao as regiao,
    populacao_residente as populacao,
    round(cagr_pib_real_3a_pct, 2) as cagr_3a_pct,
    round(pib_real_mil_brl / 1e6, 2) as pib_real_bi,
    round(indice_diversificacao_setorial, 3) as diversificacao_1_hhi,
    ims_score_0_100 as ims
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
  and populacao_residente >= 50000
  and cagr_pib_real_3a_pct is not null
  and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
order by cagr_pib_real_3a_pct desc
limit 20
```

<BarChart
    data={top_cagr}
    x=municipio
    y=cagr_3a_pct
    swapXY=true
    sort=false
    title="Maior Crescimento Real Composto (CAGR 3a %)"
    yAxisTitle="CAGR Real 3 Anos (%)"
/>

---

## Poder de Compra (PIB Per Capita Real) × Score IMS

```sql scatter_poder_compra
select
    nome_municipio || ' - ' || sigla_uf as municipio,
    nome_regiao as regiao,
    round(pib_per_capita_real_brl, 0) as pib_per_capita_real,
    ims_score_0_100 as ims,
    round(indice_diversificacao_setorial, 3) as diversificacao
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
    series=regiao
    tooltipTitle=municipio
    title="Municípios (>= 50 mil hab.): PIB Per Capita Real (R$) × Score IMS"
    xAxisTitle="PIB Per Capita Real (R$)"
    yAxisTitle="Score IMS (0-100)"
/>

---

## Estrutura Produtiva Média por Grande Região (Participação no VAB)

```sql vab_por_regiao
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
order by diversificacao_media desc
```

<DataTable data={vab_por_regiao} />

<DataTable data={top_cagr} search=true rows=20 />
