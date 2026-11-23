---
title: SidraLake 360° — Inteligência de Mercado IBGE
---

Painel interativo alimentado diretamente pela camada **Gold** do Lakehouse **SidraLake** (Delta Lake + DuckDB + dbt Semantic Layer), integrando dados oficiais do **IBGE** (PIB Municipal deflacionado pelo IPCA, Censo 2022 + Estimativas Populacionais, CEMPRE e PMC) para todos os **5.571 municípios brasileiros**.

```sql ufs_disponiveis
select 'TODAS' as sigla_uf, 0 as ordem
union all
select distinct sigla_uf, 1 as ordem
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
order by ordem, sigla_uf
```

```sql regioes_disponiveis
select 'TODAS' as nome_regiao, 0 as ordem
union all
select distinct nome_regiao, 1 as ordem
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
order by ordem, nome_regiao
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
<BigValue data={kpis_gerais} value=empresas_atuantes title="Empresas Atuantes (CEMPRE)" fmt="#,##0" />
<BigValue data={kpis_gerais} value=ims_medio title="Score IMS Médio (0-100)" fmt="0.00" />

---

## Top 20 Municípios por Score IMS (Último Ano Completo)

```sql top_20_ims
select
    rank_nacional_ims,
    nome_municipio || ' - ' || sigla_uf as municipio,
    sigla_uf,
    nome_regiao,
    ims_score_0_100,
    round(pib_real_mil_brl / 1e6, 2) as pib_real_bi,
    round(pib_per_capita_real_brl, 0) as pib_pc_real,
    populacao_residente,
    tier_mercado
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
  and ims_score_0_100 is not null
  and ('${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}')
  and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
  and ('${inputs.tier.value}' = 'TODOS' or tier_mercado = '${inputs.tier.value}')
order by rank_nacional_ims asc
limit 20
```

<BarChart
    data={top_20_ims}
    x=municipio
    y=ims_score_0_100
    swapXY=true
    sort=false
    title="Ranking IMS (0 a 100) — Índice de Mercado SidraLake"
    yAxisTitle="Score IMS (0-100)"
/>

---

## Distribuição Nacional por Tier de Mercado

```sql resumo_tiers
select
    tier_mercado,
    count(*) as municipios,
    round(avg(ims_score_0_100), 2) as ims_medio,
    round(sum(pib_real_mil_brl) / 1e6, 2) as pib_real_bi,
    sum(populacao_residente) as populacao
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
  and ('${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}')
  and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
group by 1
order by ims_medio desc nulls last
```

<BarChart
    data={resumo_tiers}
    x=tier_mercado
    y=pib_real_bi
    title="PIB Real Acumulado por Tier de Mercado (R$ Bilhões)"
    yAxisTitle="PIB Real (R$ Bi)"
/>

<DataTable data={resumo_tiers} />

---

## Explorador Completo de Municípios (Pesquisável)

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
