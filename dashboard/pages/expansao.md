---
title: Radar de Expansão & Oportunidades (Screener)
---

Ferramenta de **prospecção territorial B2B e Varejo**: ajuste os filtros de **porte populacional**, **Score IMS mínimo** e **salário médio real** para filtrar o mercado endereçável e gerar uma shortlist pronta para expansão.

```sql regioes_exp
select 'TODAS' as nome_regiao, 0 as ordem
union all
select distinct nome_regiao, 1 as ordem
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
order by ordem, nome_regiao
```

```sql ufs_exp
select 'TODAS' as sigla_uf, 0 as ordem
union all
select distinct sigla_uf, 1 as ordem
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
order by ordem, sigla_uf
```

<Dropdown data={regioes_exp} name=regiao value=nome_regiao title="Grande Região" defaultValue="TODAS" />
<Dropdown data={ufs_exp} name=uf value=sigla_uf title="UF" defaultValue="TODAS" />

<Grid cols=3>
    <Slider name=min_pop title="População Mínima" min=0 max=500000 step=10000 defaultValue=50000 fmt="#,##0" size=full />
    <Slider name=min_ims title="Score IMS Mínimo" min=0 max=85 step=5 defaultValue=60 fmt="0" size=full />
    <Slider name=min_sal title="Salário Mín. (R$)" min=0 max=5000 step=250 defaultValue=2500 fmt="#,##0" size=full />
</Grid>

```sql funil_expansao
select
    count(*) as cidades_qualificadas,
    sum(populacao_residente) as pop_enderecavel,
    round(sum(pib_real_mil_brl) / 1e6, 1) as pib_real_bi,
    round(sum(massa_salarial_real_mil_brl) / 1e6, 1) as massa_salarial_bi,
    sum(num_empresas_atuantes) as empresas_alvo
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
  and ('${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}')
  and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
  and coalesce(populacao_residente, 0) >= coalesce(try_cast('${inputs.min_pop}' as double), 50000)
  and coalesce(ims_score_0_100, 0) >= coalesce(try_cast('${inputs.min_ims}' as double), 60)
  and coalesce(salario_medio_real_brl, 0) >= coalesce(try_cast('${inputs.min_sal}' as double), 2500)
```

<BigValue data={funil_expansao} value=cidades_qualificadas title="Cidades Qualificadas" fmt="#,##0" />
<BigValue data={funil_expansao} value=pop_enderecavel title="População Endereçável" fmt="#,##0" />
<BigValue data={funil_expansao} value=pib_real_bi title="PIB Combinado (R$ Bi)" fmt="#,##0.0" />
<BigValue data={funil_expansao} value=massa_salarial_bi title="Massa Salarial (R$ Bi)" fmt="#,##0.0" />
<BigValue data={funil_expansao} value=empresas_alvo title="Empresas Atuantes Alvo" fmt="#,##0" />

---

## Matriz de Atratividade: Crescimento Real (CAGR 3a) × Poder de Compra × População

```sql matriz_oportunidades
select
    nome_municipio || ' - ' || sigla_uf as municipio,
    case
        when tier_mercado = 'Tier 1 - Polo Nacional' then 'Tier 1 · Polo'
        when tier_mercado = 'Tier 2 - Expansao Prioritaria' then 'Tier 2 · Expansão'
        else 'Demais Tiers'
    end as tier_destaque,
    round(cagr_pib_real_3a_pct / 100.0, 4) as cagr_3a_pct,
    round(pib_per_capita_real_brl, 0) as pib_pc_real,
    populacao_residente as populacao,
    ims_score_0_100 as ims
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
  and ('${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}')
  and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
  and coalesce(populacao_residente, 0) >= coalesce(try_cast('${inputs.min_pop}' as double), 50000)
  and coalesce(ims_score_0_100, 0) >= coalesce(try_cast('${inputs.min_ims}' as double), 60)
  and coalesce(salario_medio_real_brl, 0) >= coalesce(try_cast('${inputs.min_sal}' as double), 2500)
  and cagr_pib_real_3a_pct is not null
  and pib_per_capita_real_brl is not null
order by ims_score_0_100 desc
limit 300
```

<BubbleChart
    data={matriz_oportunidades}
    x=cagr_3a_pct
    y=pib_pc_real
    size=populacao
    series=tier_destaque
    tooltipTitle=municipio
    xFmt="0.0%"
    yFmt="#,##0"
    yGridlines=false
    xGridlines=false
    seriesColors={{'Tier 1 · Polo': '#3b82f6', 'Tier 2 · Expansão': '#10b981', 'Demais Tiers': '#525866'}}
    title="Onde cruzar alto crescimento real com poder de compra?"
    subtitle="Eixo X: CAGR 3a (%) · Eixo Y: PIB Per Capita (R$) · Bolha: População"
    xAxisTitle="CAGR PIB Real 3 Anos (%)"
    yAxisTitle="PIB Per Capita Real (R$)"
/>

---

## Shortlist Acionável de Mercados Alvo (Exportável em CSV)

```sql shortlist_expansao
select
    rank_nacional_ims as rk,
    nome_municipio as municipio,
    sigla_uf as uf,
    case tier_mercado
        when 'Tier 1 - Polo Nacional' then 'Tier 1'
        when 'Tier 2 - Expansao Prioritaria' then 'Tier 2'
        when 'Tier 3 - Emergente' then 'Tier 3'
        else 'Tier 4'
    end as tier,
    ims_score_0_100 as ims,
    populacao_residente as populacao,
    round(pib_real_mil_brl / 1e6, 2) as pib_bi,
    round(pib_per_capita_real_brl, 0) as pib_pc,
    round(cagr_pib_real_3a_pct / 100.0, 4) as cagr_3a_pct,
    num_empresas_atuantes as empresas,
    round(salario_medio_real_brl, 0) as salario_real
from sidralake.mart_inteligencia_mercado_municipal
where is_ultimo_ano_completo
  and ('${inputs.regiao.value}' = 'TODAS' or nome_regiao = '${inputs.regiao.value}')
  and ('${inputs.uf.value}' = 'TODAS' or sigla_uf = '${inputs.uf.value}')
  and coalesce(populacao_residente, 0) >= coalesce(try_cast('${inputs.min_pop}' as double), 50000)
  and coalesce(ims_score_0_100, 0) >= coalesce(try_cast('${inputs.min_ims}' as double), 60)
  and coalesce(salario_medio_real_brl, 0) >= coalesce(try_cast('${inputs.min_sal}' as double), 2500)
order by ims_score_0_100 desc, pib_real_mil_brl desc
```

<DataTable data={shortlist_expansao} search=true rows=25 />
