---
title: SidraLake 360° — Visão Executiva Brasil
---

Plataforma completa de **Inteligência de Mercado 360°** sobre todos os **5.571 municípios brasileiros**, alimentada pela camada **Gold** do Lakehouse **SidraLake** (IBGE PIB Municipal deflacionado pelo IPCA, Censo 2022 + Estimativas, CEMPRE Municipal/Setorial e PMC). Utilize o menu lateral para navegar entre **Visão Executiva**, **Raio-X Municipal (5.571 Cidades)**, **Comparador Head-to-Head**, **Radar de Expansão**, **Dinamismo & VAB**, **Clusters CNAE** e **Macroeconomia & Varejo**.

```sql anos_disponiveis
select distinct ano_referencia
from sidralake.mart_inteligencia_mercado_municipal
where pib_real_mil_brl is not null
order by ano_referencia desc
```

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

<Dropdown data={anos_disponiveis} name=ano value=ano_referencia title="Ano" defaultValue={2023} />
<Dropdown data={regioes_disponiveis} name=regiao value=nome_regiao title="Grande Região" defaultValue="TODAS" />
<Dropdown data={ufs_disponiveis} name=uf value=sigla_uf title="UF" defaultValue="TODAS" />
<Dropdown data={tiers_disponiveis} name=tier value=tier_mercado title="Tier de Mercado" defaultValue="TODOS" />

```sql kpis_gerais
select
    count(*) as total_municipios,
    sum(populacao_residente) as populacao_total,
    sum(pib_real_mil_brl) / 1e9 as pib_real_tri,
    sum(massa_salarial_real_mil_brl) / 1e6 as massa_salarial_bi,
    sum(num_empresas_atuantes) as empresas_atuantes,
    round(avg(ims_score_0_100), 2) as ims_medio
from sidralake.mart_inteligencia_mercado_municipal
where ano_referencia = coalesce(try_cast('${inputs.ano.value}' as integer), 2023)
  and ('${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}')
  and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
  and ('${inputs.tier.value}' = 'TODOS' or tier_mercado = '${inputs.tier.value}')
```

<BigValue data={kpis_gerais} value=total_municipios title="Municípios no Recorte" fmt="#,##0" />
<BigValue data={kpis_gerais} value=pib_real_tri title="PIB Real (R$ Tri)" fmt="#,##0.00" />
<BigValue data={kpis_gerais} value=populacao_total title="População Residente" fmt="#,##0" />
<BigValue data={kpis_gerais} value=massa_salarial_bi title="Massa Salarial (R$ Bi)" fmt="#,##0.0" />
<BigValue data={kpis_gerais} value=ims_medio title="Score IMS Médio" fmt="0.00" />

---

```sql top_12_ims
with base as (
    select
        nome_municipio || ' - ' || sigla_uf as municipio,
        round(ims_score_0_100, 1) as ims_score_0_100,
        row_number() over (order by ims_score_0_100 desc, pib_real_mil_brl desc) as pos
    from sidralake.mart_inteligencia_mercado_municipal
    where ano_referencia = coalesce(try_cast('${inputs.ano.value}' as integer), 2023)
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

```sql pib_por_regiao
with agg as (
    select
        nome_regiao as regiao,
        count(*) as municipios,
        round(sum(pib_real_mil_brl) / 1e6, 1) as pib_real_bi,
        round(avg(ims_score_0_100), 2) as ims_medio
    from sidralake.mart_inteligencia_mercado_municipal
    where ano_referencia = coalesce(try_cast('${inputs.ano.value}' as integer), 2023)
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
        data={top_12_ims}
        x=municipio
        y=ims_score_0_100
        series=destaque
        type=stacked
        swapXY=true
        sort=false
        labels=true
        stackTotalLabel=false
        labelPosition=outside
        showAllLabels=true
        labelFmt="0.0"
        rightPadding=24
        legend=false
        yGridlines=false
        xGridlines=false
        yAxisLabels=false
        yBaseline=false
        seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525866'}}
        title="Quais municípios lideram o Score IMS?"
        subtitle="Top 12 (0–100) · Líder em azul"
    />
    <ECharts
        data={pib_por_regiao}
        height="340px"
        config={{
            title: [
                {
                    text: 'Como o PIB real se distribui por Região?',
                    subtext: 'Participação regional (R$ Bi) · Maior fatia em azul',
                    left: 'left',
                    textStyle: { fontSize: 15, fontWeight: 600 },
                    subtextStyle: { fontSize: 12 }
                },
                {
                    text: 'R$ ' + (Array.from(pib_por_regiao ?? []).reduce((a, r) => a + Number(r.pib_real_bi || 0), 0) / 1000).toFixed(2) + ' Tri',
                    subtext: 'PIB Real Total',
                    left: 'center',
                    top: '50%',
                    textStyle: { fontSize: 18, fontWeight: 700 },
                    subtextStyle: { fontSize: 11 }
                }
            ],
            tooltip: {
                trigger: 'item',
                formatter: '{b}: R$ {c} Bi ({d}%)'
            },
            series: [
                {
                    name: 'PIB Real',
                    type: 'pie',
                    radius: ['48%', '72%'],
                    center: ['50%', '58%'],
                    avoidLabelOverlap: true,
                    itemStyle: {
                        borderRadius: 4,
                        borderColor: '#0d1117',
                        borderWidth: 2
                    },
                    label: {
                        show: true,
                        formatter: '{b}\n{d}%',
                        fontSize: 11
                    },
                    data: Array.from(pib_por_regiao ?? []).map((r, idx) => ({
                        name: r.regiao,
                        value: r.pib_real_bi,
                        itemStyle: {
                            color: idx === 0 ? '#3b82f6' : idx === 1 ? '#64748b' : idx === 2 ? '#525866' : idx === 3 ? '#475569' : '#334155'
                        }
                    }))
                }
            ]
        }}
    />
</Grid>

---

```sql top_12_pib
with base as (
    select
        nome_municipio || ' - ' || sigla_uf as municipio,
        round(pib_real_mil_brl / 1e6, 1) as pib_real_bi,
        row_number() over (order by pib_real_mil_brl desc) as pos
    from sidralake.mart_inteligencia_mercado_municipal
    where ano_referencia = coalesce(try_cast('${inputs.ano.value}' as integer), 2023)
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

```sql resumo_tiers
with agg as (
    select
        tier_mercado,
        count(*) as municipios,
        round(avg(ims_score_0_100), 2) as ims_medio,
        round(sum(pib_real_mil_brl) / 1e6, 1) as pib_real_bi,
        sum(populacao_residente) as populacao
    from sidralake.mart_inteligencia_mercado_municipal
    where ano_referencia = coalesce(try_cast('${inputs.ano.value}' as integer), 2023)
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

<Grid cols=2>
    <BarChart
        data={top_12_pib}
        x=municipio
        y=pib_real_bi
        series=destaque
        type=stacked
        swapXY=true
        sort=false
        labels=true
        stackTotalLabel=false
        labelPosition=outside
        showAllLabels=true
        labelFmt="#,##0.0"
        rightPadding=28
        legend=false
        yGridlines=false
        xGridlines=false
        yAxisLabels=false
        yBaseline=false
        seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525866'}}
        title="Quais municípios têm maior PIB real?"
        subtitle="Top 12 (R$ Bi) · Líder em azul"
    />
    <BarChart
        data={resumo_tiers}
        x=tier_mercado
        y=pib_real_bi
        series=destaque
        type=stacked
        swapXY=true
        sort=false
        labels=true
        stackTotalLabel=false
        labelPosition=outside
        showAllLabels=true
        labelFmt="#,##0.0"
        rightPadding=32
        legend=false
        yGridlines=false
        xGridlines=false
        yAxisLabels=false
        yBaseline=false
        seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525866'}}
        title="Onde se concentra o PIB por Tier?"
        subtitle="PIB real acumulado (R$ Bi)"
    />
</Grid>

---

## Explorador Completo dos 5.571 Municípios

```sql tabela_municipios
select
    rank_nacional_ims as rk_br,
    rank_estadual_ims as rk_uf,
    nome_municipio as municipio,
    sigla_uf as uf,
    nome_regiao as regiao,
    nome_regiao_imediata as reg_imediata,
    populacao_residente as populacao,
    round(pib_real_mil_brl / 1e6, 3) as pib_real_bi,
    round(pib_per_capita_real_brl, 0) as pib_pc_real,
    num_empresas_atuantes as empresas,
    pessoal_ocupado_total as emprego,
    round(salario_medio_real_brl, 0) as salario_medio_real,
    round(cagr_pib_real_3a_pct, 2) as cagr_3a_pct,
    ims_score_0_100 as ims,
    tier_mercado as tier
from sidralake.mart_inteligencia_mercado_municipal
where ano_referencia = coalesce(try_cast('${inputs.ano.value}' as integer), 2023)
  and ('${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}')
  and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
  and ('${inputs.tier.value}' = 'TODOS' or tier_mercado = '${inputs.tier.value}')
order by rank_nacional_ims asc
```

<DataTable data={tabela_municipios} search=true rows=20 />

---

> **Fonte dos Dados:** Os dados primários pertencem ao **Instituto Brasileiro de Geografia e Estatística (IBGE)** e são de acesso público nos termos da Política de Dados Abertos do Governo Federal. Código-fonte licenciado sob **GNU GPL v3.0**.
