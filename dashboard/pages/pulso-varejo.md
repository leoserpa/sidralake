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
    substr(ult.ano_mes, 5, 2) || '/' || substr(ult.ano_mes, 1, 4) as ultima_competencia,
    round(ult.variacao_mensal_pct / 100.0, 4) as ipca_mes_pct,
    round(ult.variacao_acum_ano_pct / 100.0, 4) as ipca_ano_pct,
    round(ult.variacao_acum_12m_pct / 100.0, 4) as ipca_12m_pct,
    round((ult.numero_indice_ipca / pri.idx_ini) - 1.0, 4) as inflacao_acum_2018_pct
from ult
cross join pri
```

<BigValue data={ipca_kpis} value=ultima_competencia title="Última Competência" />
<BigValue data={ipca_kpis} value=ipca_mes_pct title="IPCA Mensal" fmt="0.00%" />
<BigValue data={ipca_kpis} value=ipca_ano_pct title="IPCA Acum. Ano" fmt="0.00%" />
<BigValue data={ipca_kpis} value=ipca_12m_pct title="IPCA Acum. 12m" fmt="0.00%" />
<BigValue data={ipca_kpis} value=inflacao_acum_2018_pct title="Inflação (2018+)" fmt="0.0%" />

```sql serie_ipca
select
    data_referencia,
    round(variacao_acum_12m_pct / 100.0, 4) as ipca_12m_pct,
    round(variacao_mensal_pct / 100.0, 4) as ipca_mensal_pct
from sidralake.fct_ipca_mensal
order by data_referencia asc
```

<LineChart
    data={serie_ipca}
    x=data_referencia
    y={["ipca_12m_pct", "ipca_mensal_pct"]}
    yFmt="0.0%"
    yGridlines=false
    xGridlines=false
    colorPalette={['#f59e0b', '#64748b']}
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
    substr(ano_mes, 5, 2) || '/' || substr(ano_mes, 1, 4) as competencia,
    round(var_yoy_volume_pct / 100.0, 4) as volume_yoy_pct,
    round(var_yoy_receita_nominal_pct / 100.0, 4) as receita_yoy_pct,
    round(ipca_variacao_acum_12m_pct / 100.0, 4) as ipca_12m_pct,
    round(spread_preco_vs_volume_yoy_pp, 2) as spread_pp,
    case regime_consumo
        when 'EXPANSAO_REAL' then 'Expansão Real'
        when 'PRESSAO_INFLACIONARIA' then 'Pressão Inflac.'
        when 'ESTABILIDADE' then 'Estabilidade'
        when 'RETRACAO' then 'Retração'
        else regime_consumo
    end as regime
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
    yFmt="0.0%"
    yGridlines=false
    xGridlines=false
    colorPalette={['#3b82f6', '#64748b', '#f59e0b']}
    title="Volume Real do Varejo vs. Receita Nominal e Inflação (YoY %)"
    subtitle="Volume Real em azul · Receita Nominal em cinza · IPCA 12m em âmbar"
    yAxisTitle="Variação (%)"
/>

---

## 3. Saúde do Varejo Nacional (Cores Semânticas & Mapa UF × Grupo)

```sql regimes_ultimo_mes
select
    case regime_consumo
        when 'EXPANSAO_REAL' then 'Expansão Real'
        when 'PRESSAO_INFLACIONARIA' then 'Pressão Inflac.'
        when 'ESTABILIDADE' then 'Estabilidade'
        when 'RETRACAO' then 'Retração'
        else regime_consumo
    end as regime,
    count(*) as series,
    round(avg(var_yoy_volume_pct) / 100.0, 4) as vol_yoy_pct,
    round(avg(spread_preco_vs_volume_yoy_pp), 2) as spread_pp
from sidralake.mart_pulso_consumo_macro
where ano_mes = (select max(ano_mes) from sidralake.mart_pulso_consumo_macro)
  and regime_consumo <> 'SEM_DADO'
group by 1
order by series desc
```

```sql heatmap_varejo_uf
select
    sigla_uf as uf,
    case grupo_consumo
        when 'ALIMENTACAO_ATACAREJO' then 'Alimentos'
        when 'AUTOMOTIVO_CONSTRUCAO' then 'Autos/Obra'
        when 'BENS_DURAVEIS_LAR' then 'Lar/Eletro'
        when 'COMBUSTIVEIS' then 'Combustíveis'
        when 'FARMACIA_VESTUARIO_CONVENIENCIA' then 'Farma/Moda'
        else grupo_consumo
    end as grupo,
    round(avg(var_yoy_volume_pct) / 100.0, 4) as vol_yoy_pct
from sidralake.mart_pulso_consumo_macro
where ano_mes = (select max(ano_mes) from sidralake.mart_pulso_consumo_macro)
  and var_yoy_volume_pct is not null
group by 1, 2
order by sigla_uf asc, grupo asc
```

<Grid cols=2>
    <BarChart
        data={regimes_ultimo_mes}
        x=regime
        y=series
        series=regime
        type=stacked
        swapXY=true
        sort=false
        labels=true
        stackTotalLabel=false
        labelPosition=outside
        showAllLabels=true
        labelFmt="#,##0"
        leftPadding=24
        rightPadding=28
        legend=false
        yGridlines=false
        xGridlines=false
        yAxisLabels=false
        yBaseline=false
        seriesColors={{'Expansão Real': '#10b981', 'Pressão Inflac.': '#f59e0b', 'Estabilidade': '#64748b', 'Retração': '#ef4444'}}
        title="Saúde do varejo por regime de consumo"
        subtitle="Verde=Expansão · Âmbar=Inflação · Vermelho=Retração"
    />
    <Heatmap
        data={heatmap_varejo_uf}
        x=grupo
        y=uf
        value=vol_yoy_pct
        valueFmt="0.0%"
        xLabelRotation=0
        colorScale={['#dc2626', '#334155', '#10b981']}
        title="Volume Real YoY (%) — UF × Grupo"
        subtitle="Última competência PMC · Vermelho = queda · Verde = expansão"
    />
</Grid>

---

## Histórico Mensal Detalhado da Série Selecionada

```sql tabela_mensal_pmc
select
    substr(ano_mes, 5, 2) || '/' || substr(ano_mes, 1, 4) as competencia,
    round(var_yoy_volume_pct / 100.0, 4) as volume_yoy_pct,
    round(var_yoy_receita_nominal_pct / 100.0, 4) as receita_yoy_pct,
    round(ipca_variacao_acum_12m_pct / 100.0, 4) as ipca_12m_pct,
    round(spread_preco_vs_volume_yoy_pp, 2) as spread_pp,
    case regime_consumo
        when 'EXPANSAO_REAL' then 'Expansão Real'
        when 'PRESSAO_INFLACIONARIA' then 'Pressão Inflac.'
        when 'ESTABILIDADE' then 'Estabilidade'
        when 'RETRACAO' then 'Retração'
        else regime_consumo
    end as regime
from sidralake.mart_pulso_consumo_macro
where sigla_uf = '${inputs.uf.value}'
  and nome_atividade_pmc = '${inputs.atividade.value}'
  and var_yoy_volume_pct is not null
order by data_referencia desc
```

<DataTable data={tabela_mensal_pmc} search=true rows=15 />
