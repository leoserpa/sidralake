---
title: Macroeconomia (IPCA) & Pulso do Varejo (PMC)
---

Painel macroeconômico integrando a **Inflação Oficial IPCA (SIDRA 1737 · 2018–2026)** e a **Pesquisa Mensal de Comércio Ampliado (PMC · SIDRA 8883)**, com **codificação semântica de cores** (Verde = Expansão Real, Âmbar = Pressão Inflacionária, Cinza = Estabilidade, Vermelho = Retração).

## 1. Cenário Inflacionário Oficial (IPCA Brasil · 2018–2026)

```sql ipca_kpis
with ult as (
    select *
    from sidralake.fct_ipca_mensal
    order by data_referencia desc
    limit 1
),
pri as (
    select numero_indice_ipca as idx_ini
    from sidralake.fct_ipca_mensal
    order by data_referencia asc
    limit 1
)
select
    ult.ano_mes as ultima_competencia,
    round(ult.variacao_mensal_pct, 2) as ipca_mes_pct,
    round(ult.variacao_acum_ano_pct, 2) as ipca_ano_pct,
    round(ult.variacao_acum_12m_pct, 2) as ipca_12m_pct,
    round(((ult.numero_indice_ipca / pri.idx_ini) - 1.0) * 100.0, 1) as inflacao_acum_2018_pct
from ult
cross join pri
```

<BigValue data={ipca_kpis} value=ultima_competencia title="Última Competência IPCA" />
<BigValue data={ipca_kpis} value=ipca_mes_pct title="IPCA Mensal (%)" fmt="0.00" />
<BigValue data={ipca_kpis} value=ipca_ano_pct title="IPCA Acum. Ano (%)" fmt="0.00" />
<BigValue data={ipca_kpis} value=ipca_12m_pct title="IPCA Acum. 12m (%)" fmt="0.00" />
<BigValue data={ipca_kpis} value=inflacao_acum_2018_pct title="Inflação Acum. (2018+ %)" fmt="0.0" />

```sql serie_ipca
select
    data_referencia,
    round(variacao_acum_12m_pct, 2) as ipca_12m_pct,
    round(variacao_mensal_pct, 2) as ipca_mensal_pct
from sidralake.fct_ipca_mensal
order by data_referencia asc
```

<LineChart
    data={serie_ipca}
    x=data_referencia
    y={["ipca_12m_pct", "ipca_mensal_pct"]}
    yGridlines=false
    xGridlines=false
    seriesColors={{'ipca_12m_pct': '#f59e0b', 'ipca_mensal_pct': '#64748b'}}
    title="Trajetória da Inflação Oficial (IPCA Brasil · 2018–2026)"
    subtitle="IPCA acumulado em 12 meses em âmbar · Variação mensal em cinza"
    yAxisTitle="Variação (%)"
/>

---

## 2. Pulso do Varejo Ampliado por UF e Atividade (PMC × IPCA)

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
    seriesColors={{'volume_yoy_pct': '#3b82f6', 'receita_yoy_pct': '#64748b', 'ipca_12m_pct': '#f59e0b'}}
    title="Volume Real do Varejo vs. Receita Nominal e Inflação (YoY %)"
    subtitle="Volume Real em azul · Receita Nominal em cinza · IPCA 12m em âmbar"
    yAxisTitle="Variação (%)"
/>

---

## 3. Saúde do Varejo Nacional (Cores Semânticas & Mapa UF × Grupo)

```sql regimes_ultimo_mes
select
    regime_consumo,
    count(*) as series_uf_atividade,
    round(avg(var_yoy_volume_pct), 2) as vol_yoy_medio_pct,
    round(avg(spread_preco_vs_volume_yoy_pp), 2) as spread_medio_pp
from sidralake.mart_pulso_consumo_macro
where ano_mes = (select max(ano_mes) from sidralake.mart_pulso_consumo_macro)
  and regime_consumo <> 'SEM_DADO'
group by 1
order by series_uf_atividade desc
```

```sql heatmap_varejo_uf
select
    sigla_uf as uf,
    grupo_consumo as grupo,
    round(avg(var_yoy_volume_pct), 1) as vol_yoy_pct
from sidralake.mart_pulso_consumo_macro
where ano_mes = (select max(ano_mes) from sidralake.mart_pulso_consumo_macro)
  and var_yoy_volume_pct is not null
group by 1, 2
order by sigla_uf asc, grupo_consumo asc
```

<Grid cols=2>
    <BarChart
        data={regimes_ultimo_mes}
        x=regime_consumo
        y=series_uf_atividade
        series=regime_consumo
        type=stacked
        swapXY=true
        sort=false
        labels=true
        stackTotalLabel=false
        labelPosition=outside
        showAllLabels=true
        labelFmt="#,##0"
        rightPadding=24
        legend=false
        yGridlines=false
        xGridlines=false
        yAxisLabels=false
        yBaseline=false
        seriesColors={{'EXPANSAO_REAL': '#10b981', 'PRESSAO_INFLACIONARIA': '#f59e0b', 'ESTABILIDADE': '#64748b', 'RETRACAO': '#ef4444'}}
        title="Saúde do varejo por regime de consumo"
        subtitle="Verde=Expansão · Âmbar=Inflação · Vermelho=Retração"
    />
    <Heatmap
        data={heatmap_varejo_uf}
        x=grupo
        y=uf
        value=vol_yoy_pct
        valueFmt="0.0"
        colorScale={['#dc2626', '#334155', '#10b981']}
        title="Volume Real YoY (%) — UF × Grupo de Consumo"
        subtitle="Última competência PMC · Vermelho = queda · Verde = expansão"
    />
</Grid>

---

## Histórico Mensal Detalhado da Série Selecionada

<DataTable data={serie_mensal_pmc} search=true rows=15 />
