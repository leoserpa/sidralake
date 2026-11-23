---
title: Macroeconomia (IPCA) & Pulso do Varejo (PMC)
---

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

<header class="sl-page-header">
	<div class="sl-page-heading">
		<h1 class="sl-page-title">Macroeconomia (IPCA) &amp; Pulso do Varejo (PMC)</h1>
		<p class="sl-page-subtitle">Inflação Oficial IPCA (SIDRA 1737 · 2018–2026) integrada à Pesquisa Mensal de Comércio Ampliado (PMC · SIDRA 8883)</p>
	</div>
	<div class="sl-filter-bar">
		<Dropdown data={ufs_pmc} name=uf value=sigla_uf title="UF" defaultValue="SP" />
		<Dropdown data={atividades_pmc} name=atividade value=nome_atividade_pmc title="Atividade PMC" defaultValue="Hipermercados e supermercados" />
	</div>
</header>

<div class="sl-kpi-grid-5">
	<KpiCard data={ipca_kpis} value="ultima_competencia" title="Última Competência" fmt="raw" icon="calendar" subtitle="Fechamento oficial IBGE" />
	<KpiCard data={ipca_kpis} value="ipca_mes_pct" title="IPCA Mensal" fmt="pct2" icon="percent" subtitle="Variação no mês" />
	<KpiCard data={ipca_kpis} value="ipca_ano_pct" title="IPCA Acum. Ano" fmt="pct2" icon="trending" subtitle="Acumulado no ano civil" />
	<KpiCard data={ipca_kpis} value="ipca_12m_pct" title="IPCA Acum. 12m" fmt="pct2" icon="gauge" subtitle="Referência de deflação" />
	<KpiCard data={ipca_kpis} value="inflacao_acum_2018_pct" title="Inflação (2018+)" fmt="pct1" icon="layers" subtitle="Acumulada na janela do Lake" />
</div>

```sql serie_ipca
select
    data_referencia,
    round(variacao_acum_12m_pct / 100.0, 4) as ipca_12m_pct,
    round(variacao_mensal_pct / 100.0, 4) as ipca_mensal_pct
from sidralake.fct_ipca_mensal
order by data_referencia asc
```

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

<div class="sl-grid-2">
	<div class="sl-card">
		<LineChart
			data={serie_ipca}
			x=data_referencia
			y={["ipca_12m_pct", "ipca_mensal_pct"]}
			yFmt="0.0%"
			yGridlines=false
			xGridlines=false
			colorPalette={['#3b82f6', '#64748b']}
			title="Trajetória da Inflação Oficial (IPCA Brasil · 2018–2026)"
			subtitle="IPCA acumulado em 12 meses em azul · Variação mensal em ardósia"
			yAxisTitle="Variação (%)"
		/>
	</div>
	<div class="sl-card">
		<LineChart
			data={serie_mensal_pmc}
			x=data_referencia
			y={["volume_yoy_pct", "receita_yoy_pct", "ipca_12m_pct"]}
			yFmt="0.0%"
			yGridlines=false
			xGridlines=false
			colorPalette={['#3b82f6', '#94a3b8', '#475569']}
			title="Volume Real do Varejo vs. Receita Nominal e IPCA (YoY %)"
			subtitle="Volume Real em azul pré-atentivo · Receita Nominal e IPCA 12m em ardósia"
			yAxisTitle="Variação (%)"
		/>
	</div>
</div>

```sql regimes_ultimo_mes
with base as (
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
),
ranked as (
    select
        regime,
        series,
        round(series * 1.0 / sum(series) over (), 4) as share_pct,
        vol_yoy_pct,
        spread_pp,
        row_number() over (order by series desc) as pos
    from base
)
select
    regime,
    series,
    share_pct,
    vol_yoy_pct,
    spread_pp,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from ranked
order by pos asc
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

<div class="sl-grid-2">
	<div class="sl-card">
		<BarChart
			data={regimes_ultimo_mes}
			x=regime
			y=share_pct
			series=destaque
			type=stacked
			swapXY=true
			sort=false
			labels=true
			stackTotalLabel=false
			labelPosition=outside
			showAllLabels=true
			labelFmt="0.0%"
			leftPadding=24
			rightPadding=40
			legend=false
			yGridlines=false
			xGridlines=false
			yAxisLabels=false
			yBaseline=false
			seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525866'}}
			title="Qual regime domina o varejo nacional (PMC × IPCA)?"
			subtitle="Distribuição das séries UF × Atividade (PMC × IPCA) · Regime dominante em azul"
		/>
	</div>
	<div class="sl-card">
		<Heatmap
			data={heatmap_varejo_uf}
			x=grupo
			y=uf
			value=vol_yoy_pct
			valueFmt="0.0%"
			xLabelRotation=0
			colorScale={['#141b26', '#334155', '#3b82f6']}
			title="Volume Real YoY (%) — UF × Grupo de Consumo"
			subtitle="Última competência PMC · Intensidade azul indica maior expansão real"
		/>
	</div>
</div>

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

<ExecTable
	data={tabela_mensal_pmc}
	title="Histórico Mensal Detalhado da Série Selecionada"
	subtitle="Destaque azul: competência mais recente e Volume Real YoY ≥ +5%"
	search={true}
	searchPlaceholder="Buscar competência ou regime..."
	exportCsv={true}
	csvFilename="sidralake_pulso_varejo_pmc.csv"
	rowsPerPage={15}
	highlightFirstRow={true}
	columns={[
		{ key: 'competencia', label: 'Competência', kind: 'year' },
		{ key: 'volume_yoy_pct', label: 'Volume YoY', align: 'right', kind: 'growth', highlightThreshold: 0.05 },
		{ key: 'receita_yoy_pct', label: 'Receita YoY', align: 'right', fmt: 'signed_pct1' },
		{ key: 'ipca_12m_pct', label: 'IPCA 12m', align: 'right', fmt: 'pct2' },
		{ key: 'spread_pp', label: 'Spread Preço×Vol', align: 'right', fmt: 'signed_pp' },
		{ key: 'regime', label: 'Regime de Consumo', align: 'center', kind: 'tier_badge' }
	]}
/>
