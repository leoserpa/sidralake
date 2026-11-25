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
		<h1 class="sl-page-title">Macroeconomia (IPCA), Varejo (PMC) &amp; Serviços (PMS)</h1>
		<p class="sl-page-subtitle">Inflação Oficial IPCA (SIDRA 1737 · 2018+) integrada ao Varejo Ampliado (PMC · SIDRA 8883) e aos Serviços (PMS · SIDRA 5906)</p>
	</div>
	<div class="sl-filter-bar">
		<Dropdown data={ufs_pmc} name=uf value=sigla_uf title="UF" defaultValue="SP" />
		<Dropdown data={atividades_pmc} name=atividade value=nome_atividade_pmc title="Atividade PMC" defaultValue="Hipermercados e supermercados" />
		<ResetFilters />
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
    'IPCA Acum. 12m' as indicador,
    round(variacao_acum_12m_pct / 100.0, 4) as valor_pct
from sidralake.fct_ipca_mensal
union all
select
    data_referencia,
    'IPCA Mensal' as indicador,
    round(variacao_mensal_pct / 100.0, 4) as valor_pct
from sidralake.fct_ipca_mensal
order by data_referencia asc, indicador asc
```

```sql serie_mensal_pmc
with base as (
    select
        data_referencia,
        round(var_yoy_volume_pct / 100.0, 4) as volume_yoy_pct,
        round(var_yoy_receita_nominal_pct / 100.0, 4) as receita_yoy_pct,
        round(ipca_variacao_acum_12m_pct / 100.0, 4) as ipca_12m_pct
    from sidralake.mart_pulso_consumo_macro
    where sigla_uf = '${inputs.uf.value}'
      and nome_atividade_pmc = '${inputs.atividade.value}'
      and var_yoy_volume_pct is not null
)
select data_referencia, 'Volume Real YoY' as indicador, volume_yoy_pct as valor_pct from base
union all
select data_referencia, 'Receita Nominal YoY' as indicador, receita_yoy_pct as valor_pct from base
union all
select data_referencia, 'IPCA Acum. 12m' as indicador, ipca_12m_pct as valor_pct from base
order by data_referencia asc, indicador asc
```

<div class="sl-grid-2">
	<div class="sl-card">
		<div class="sl-chart-head">
			<h3 class="sl-card-title">Trajetória da Inflação Oficial (IPCA Brasil · 2018+)</h3>
			<p class="sl-card-subtitle">IPCA acumulado em 12 meses em azul · Variação mensal em ardósia</p>
		</div>
		<LineChart
			data={serie_ipca}
			x=data_referencia
			y=valor_pct
			series=indicador
			yFmt="0.0%"
			yGridlines=false
			xGridlines=false
			seriesColors={{'IPCA Acum. 12m': '#3b82f6', 'IPCA Mensal': '#686e6c'}}
			echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f5f7f6' }, subtextStyle: { color: '#9ca3a0' } }, legend: { textStyle: { color: '#f5f7f6' } }, grid: { containLabel: true }, xAxis: { axisLabel: { color: '#f5f7f6' }, axisLine: { lineStyle: { color: '#2d3231' } } }, yAxis: { axisLabel: { color: '#f5f7f6' }, nameTextStyle: { color: '#d4d8d6' } } }}
			yAxisTitle="Variação (%)"
		/>
	</div>
	<div class="sl-card">
		<div class="sl-chart-head">
			<h3 class="sl-card-title">Volume Real do Varejo vs. Receita Nominal e IPCA (YoY %)</h3>
			<p class="sl-card-subtitle">Volume Real em azul pré-atentivo · Receita Nominal e IPCA 12m em ardósia</p>
		</div>
		<LineChart
			data={serie_mensal_pmc}
			x=data_referencia
			y=valor_pct
			series=indicador
			yFmt="0.0%"
			yGridlines=false
			xGridlines=false
			seriesColors={{'Volume Real YoY': '#3b82f6', 'Receita Nominal YoY': '#9ca3a0', 'IPCA Acum. 12m': '#3f4543'}}
			echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f5f7f6' }, subtextStyle: { color: '#9ca3a0' } }, legend: { textStyle: { color: '#f5f7f6' } }, grid: { containLabel: true }, xAxis: { axisLabel: { color: '#f5f7f6' }, axisLine: { lineStyle: { color: '#2d3231' } } }, yAxis: { axisLabel: { color: '#f5f7f6' }, nameTextStyle: { color: '#d4d8d6' } } }}
			yAxisTitle="Variação (%)"
		/>
	</div>
</div>

```sql tendencia_volume_pmc
with base as (
    select
        data_referencia,
        round(media_movel_3m_volume, 2) as mm3,
        round(media_movel_12m_volume, 2) as mm12
    from sidralake.mart_pulso_consumo_macro
    where sigla_uf = '${inputs.uf.value}'
      and nome_atividade_pmc = '${inputs.atividade.value}'
      and media_movel_3m_volume is not null
      and media_movel_12m_volume is not null
)
select data_referencia, 'Média Móvel 3m (Curto Prazo)' as serie, mm3 as indice from base
union all
select data_referencia, 'Média Móvel 12m (Tendência)' as serie, mm12 as indice from base
order by data_referencia asc, serie asc
```

```sql spread_real_varejo
select
    data_referencia,
    round(spread_volume_vs_ipca_12m_pp, 2) as spread_pp,
    case
        when spread_volume_vs_ipca_12m_pp >= 0 then 'Acima do IPCA'
        else 'Abaixo do IPCA'
    end as regime_spread
from sidralake.mart_pulso_consumo_macro
where sigla_uf = '${inputs.uf.value}'
  and nome_atividade_pmc = '${inputs.atividade.value}'
  and spread_volume_vs_ipca_12m_pp is not null
order by data_referencia asc
```

<div class="sl-grid-2">
	<div class="sl-card">
		<div class="sl-chart-head">
			<h3 class="sl-card-title">Tendência de Volume do Varejo (MM 3m × MM 12m)</h3>
			<p class="sl-card-subtitle">Índice base 2022=100 · Curto prazo (MM 3m) acima da MM 12m indica aceleração</p>
		</div>
		<LineChart
			data={tendencia_volume_pmc}
			x=data_referencia
			y=indice
			series=serie
			yFmt="#,##0.0"
			yGridlines=false
			xGridlines=false
			seriesColors={{'Média Móvel 3m (Curto Prazo)': '#3b82f6', 'Média Móvel 12m (Tendência)': '#686e6c'}}
			echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f5f7f6' }, subtextStyle: { color: '#9ca3a0' } }, legend: { textStyle: { color: '#f5f7f6' } }, grid: { containLabel: true }, xAxis: { axisLabel: { color: '#f5f7f6' }, axisLine: { lineStyle: { color: '#2d3231' } } }, yAxis: { axisLabel: { color: '#f5f7f6' }, nameTextStyle: { color: '#d4d8d6' } } }}
			yAxisTitle="Índice (2022 = 100)"
		/>
	</div>
	<div class="sl-card">
		<div class="sl-chart-head">
			<h3 class="sl-card-title">Spread de Taxas: Volume do Varejo vs. IPCA (p.p.)</h3>
			<p class="sl-card-subtitle">Diferença entre variação acumulada em 12m do volume (PMC) e do IPCA · Barras em azul indicam ritmo de volume acima da inflação</p>
		</div>
		<BarChart
			data={spread_real_varejo}
			x=data_referencia
			y=spread_pp
			series=regime_spread
			type=stacked
			yFmt="#,##0.0"
			yGridlines=false
			xGridlines=false
			seriesColors={{'Acima do IPCA': '#3b82f6', 'Abaixo do IPCA': '#525755'}}
			echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f5f7f6' }, subtextStyle: { color: '#9ca3a0' } }, legend: { textStyle: { color: '#f5f7f6' } }, grid: { containLabel: true }, xAxis: { axisLabel: { color: '#f5f7f6' }, axisLine: { lineStyle: { color: '#2d3231' } } }, yAxis: { axisLabel: { color: '#f5f7f6' }, nameTextStyle: { color: '#d4d8d6' } } }}
			yAxisTitle="Pontos Percentuais (p.p.)"
		/>
	</div>
</div>

```sql servicos_vs_varejo
select
    data_referencia,
    'Serviços (PMS YoY)' as setor,
    round(var_yoy_volume_pct / 100.0, 4) as valor_pct
from sidralake.mart_pulso_servicos_uf
where sigla_uf = '${inputs.uf.value}'
  and var_yoy_volume_pct is not null
union all
select
    data_referencia,
    'Varejo (PMC YoY)' as setor,
    round(var_yoy_volume_pct / 100.0, 4) as valor_pct
from sidralake.mart_pulso_consumo_macro
where sigla_uf = '${inputs.uf.value}'
  and nome_atividade_pmc = '${inputs.atividade.value}'
  and var_yoy_volume_pct is not null
order by data_referencia asc, setor asc
```

```sql pms_mom_sa
select
    data_referencia,
    round(var_mom_sa_volume_pct / 100.0, 4) as mom_sa_pct,
    case
        when var_mom_sa_volume_pct >= 0 then 'Alta MoM SA'
        else 'Queda MoM SA'
    end as direcao
from sidralake.mart_pulso_servicos_uf
where sigla_uf = '${inputs.uf.value}'
  and var_mom_sa_volume_pct is not null
order by data_referencia asc
```

<div class="sl-grid-2">
	<div class="sl-card">
		<div class="sl-chart-head">
			<h3 class="sl-card-title">Serviços (PMS) vs. Varejo (PMC) — Volume Real YoY (%)</h3>
			<p class="sl-card-subtitle">Comparação direta na UF selecionada · Serviços (PMS 5906) em azul</p>
		</div>
		<LineChart
			data={servicos_vs_varejo}
			x=data_referencia
			y=valor_pct
			series=setor
			yFmt="0.0%"
			yGridlines=false
			xGridlines=false
			seriesColors={{'Serviços (PMS YoY)': '#3b82f6', 'Varejo (PMC YoY)': '#686e6c'}}
			echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f5f7f6' }, subtextStyle: { color: '#9ca3a0' } }, legend: { textStyle: { color: '#f5f7f6' } }, grid: { containLabel: true }, xAxis: { axisLabel: { color: '#f5f7f6' }, axisLine: { lineStyle: { color: '#2d3231' } } }, yAxis: { axisLabel: { color: '#f5f7f6' }, nameTextStyle: { color: '#d4d8d6' } } }}
			yAxisTitle="Variação YoY (%)"
		/>
	</div>
	<div class="sl-card">
		<div class="sl-chart-head">
			<h3 class="sl-card-title">Pulso Mensal de Serviços com Ajuste Sazonal (PMS MoM SA %)</h3>
			<p class="sl-card-subtitle">Variação mês contra mês imediatamente anterior na UF selecionada · Altas em azul</p>
		</div>
		<BarChart
			data={pms_mom_sa}
			x=data_referencia
			y=mom_sa_pct
			series=direcao
			type=stacked
			yFmt="0.0%"
			yGridlines=false
			xGridlines=false
			seriesColors={{'Alta MoM SA': '#3b82f6', 'Queda MoM SA': '#525755'}}
			echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f5f7f6' }, subtextStyle: { color: '#9ca3a0' } }, legend: { textStyle: { color: '#f5f7f6' } }, grid: { containLabel: true }, xAxis: { axisLabel: { color: '#f5f7f6' }, axisLine: { lineStyle: { color: '#2d3231' } } }, yAxis: { axisLabel: { color: '#f5f7f6' }, nameTextStyle: { color: '#d4d8d6' } } }}
			yAxisTitle="Variação MoM SA (%)"
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
        row_number() over (order by series desc) as pos,
        row_number() over (order by vol_yoy_pct desc) as vol_pos
    from base
)
select
    regime,
    series,
    share_pct,
    vol_yoy_pct,
    spread_pp,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque,
    case when vol_pos = 1 then 'Destaque' else 'Demais' end as destaque_vol
from ranked
order by pos asc
```

<div class="sl-grid-2">
	<div class="sl-card">
		<div class="sl-chart-head">
			<h3 class="sl-card-title">Qual regime domina o varejo nacional (PMC × IPCA)?</h3>
			<p class="sl-card-subtitle">Distribuição das séries UF × Atividade · Regime dominante em azul</p>
		</div>
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
			rightPadding=44
			legend=false
			yGridlines=false
			xGridlines=false
			yAxisLabels=false
			yBaseline=false
			seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525755'}}
			echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f5f7f6' }, subtextStyle: { color: '#9ca3a0' } }, xAxis: { axisLabel: { color: '#f5f7f6' } }, yAxis: { axisLabel: { color: '#f5f7f6' }, axisLine: { lineStyle: { color: '#2d3231' } } } }}
		/>
	</div>
	<div class="sl-card">
		<div class="sl-chart-head">
			<h3 class="sl-card-title">Qual o ritmo médio de volume real em cada regime?</h3>
			<p class="sl-card-subtitle">Variação média YoY do volume de vendas (%) · Maior expansão em azul</p>
		</div>
		<BarChart
			data={regimes_ultimo_mes}
			x=regime
			y=vol_yoy_pct
			series=destaque_vol
			type=stacked
			swapXY=true
			sort=false
			labels=true
			stackTotalLabel=false
			labelPosition=outside
			showAllLabels=true
			labelFmt="0.0%"
			leftPadding=24
			rightPadding=44
			legend=false
			yGridlines=false
			xGridlines=false
			yAxisLabels=false
			yBaseline=false
			seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525755'}}
			echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f5f7f6' }, subtextStyle: { color: '#9ca3a0' } }, xAxis: { axisLabel: { color: '#f5f7f6' } }, yAxis: { axisLabel: { color: '#f5f7f6' }, axisLine: { lineStyle: { color: '#2d3231' } } } }}
		/>
	</div>
</div>

```sql ranking_servicos_uf
with base as (
    select
        sigla_uf as uf,
        round(var_yoy_volume_pct / 100.0, 4) as pms_yoy_pct,
        row_number() over (order by var_yoy_volume_pct desc) as pos
    from sidralake.mart_pulso_servicos_uf
    where ano_mes = (select max(ano_mes) from sidralake.mart_pulso_servicos_uf)
      and var_yoy_volume_pct is not null
    order by pos asc
    limit 12
)
select
    uf,
    pms_yoy_pct,
    case when pos = 1 then 'Destaque' else 'Demais' end as destaque
from base
order by pos asc
```

<div class="sl-card sl-stack">
	<div class="sl-chart-head">
		<h3 class="sl-card-title">Quais UFs lideram o crescimento real de Serviços (PMS)?</h3>
		<p class="sl-card-subtitle">Top 12 UFs por variação YoY do volume de serviços na última competência PMS (SIDRA 5906) · Líder em azul</p>
	</div>
	<BarChart
		data={ranking_servicos_uf}
		x=uf
		y=pms_yoy_pct
		series=destaque
		type=stacked
		swapXY=true
		sort=false
		labels=true
		stackTotalLabel=false
		labelPosition=outside
		showAllLabels=true
		labelFmt="0.0%"
		leftPadding=14
		rightPadding=44
		legend=false
		yGridlines=false
		xGridlines=false
		yAxisLabels=false
		yBaseline=false
		seriesColors={{'Destaque': '#3b82f6', 'Demais': '#525755'}}
		echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f5f7f6' }, subtextStyle: { color: '#9ca3a0' } }, xAxis: { axisLabel: { color: '#f5f7f6' } }, yAxis: { axisLabel: { color: '#f5f7f6' }, axisLine: { lineStyle: { color: '#2d3231' } } } }}
	/>
</div>

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

<div class="sl-card sl-stack">
	<div class="sl-chart-head">
		<h3 class="sl-card-title">Volume Real YoY (%) — UF × Grupo de Consumo</h3>
		<p class="sl-card-subtitle">Última competência PMC · Intensidade azul indica maior expansão real</p>
	</div>
	<p class="sl-mobile-scroll-hint">Arraste lateralmente para ver todas as colunas →</p>
	<div class="sl-heatmap-scroll">
		<div class="sl-heatmap-inner sl-heatmap-inner--compact">
			<Heatmap
				data={heatmap_varejo_uf}
				x=grupo
				y=uf
				value=vol_yoy_pct
				valueFmt="0.0%"
				xLabelRotation=0
				colorScale={['#131716', '#2d3231', '#3b82f6']}
				echartsOptions={{ backgroundColor: 'transparent', title: { textStyle: { color: '#f5f7f6' }, subtextStyle: { color: '#9ca3a0' } }, xAxis: { axisLabel: { color: '#f5f7f6' } }, yAxis: { axisLabel: { color: '#f5f7f6' } } }}
			/>
		</div>
	</div>
</div>

```sql tabela_mensal_pmc
select
    substr(c.ano_mes, 5, 2) || '/' || substr(c.ano_mes, 1, 4) as competencia,
    round(c.var_yoy_volume_pct / 100.0, 4) as volume_yoy_pct,
    round(c.var_yoy_receita_nominal_pct / 100.0, 4) as receita_yoy_pct,
    round(c.ipca_variacao_acum_12m_pct / 100.0, 4) as ipca_12m_pct,
    round(c.spread_preco_vs_volume_yoy_pp, 2) as spread_pp,
    case c.regime_consumo
        when 'EXPANSAO_REAL' then 'Expansão Real'
        when 'PRESSAO_INFLACIONARIA' then 'Pressão Inflac.'
        when 'ESTABILIDADE' then 'Estabilidade'
        when 'RETRACAO' then 'Retração'
        else c.regime_consumo
    end as regime,
    round(s.var_yoy_volume_pct / 100.0, 4) as pms_yoy_pct,
    case s.regime_servicos
        when 'EXPANSAO_REAL' then 'Expansão Real'
        when 'PRESSAO_INFLACIONARIA' then 'Pressão Inflac.'
        when 'ESTABILIDADE' then 'Estabilidade'
        when 'RETRACAO' then 'Retração'
        else s.regime_servicos
    end as regime_serv
from sidralake.mart_pulso_consumo_macro as c
left join sidralake.mart_pulso_servicos_uf as s
    on c.sigla_uf = s.sigla_uf
   and c.ano_mes = s.ano_mes
where c.sigla_uf = '${inputs.uf.value}'
  and c.nome_atividade_pmc = '${inputs.atividade.value}'
  and c.var_yoy_volume_pct is not null
order by c.data_referencia desc
```

<ExecTable
	data={tabela_mensal_pmc}
	title="Histórico Mensal Detalhado (Varejo PMC × Serviços PMS)"
	subtitle="Destaque azul: competência mais recente, Expansão Real, Volume/Serviços YoY ≥ +5% e Receita YoY ≥ +8%"
	search={true}
	searchPlaceholder="Buscar competência ou regime..."
	exportCsv={true}
	csvFilename="sidralake_pulso_varejo_pmc.csv"
	rowsPerPage={15}
	highlightFirstRow={true}
	columns={[
		{ key: 'competencia', label: 'Competência', kind: 'year' },
		{ key: 'volume_yoy_pct', label: 'Volume YoY', align: 'right', kind: 'growth', highlightThreshold: 0.05 },
		{ key: 'receita_yoy_pct', label: 'Receita YoY', align: 'right', kind: 'growth', highlightThreshold: 0.08 },
		{ key: 'ipca_12m_pct', label: 'IPCA 12m', align: 'right', fmt: 'pct2' },
		{ key: 'spread_pp', label: 'Spread Preço×Vol', align: 'right', kind: 'growth', fmt: 'signed_pp' },
		{ key: 'regime', label: 'Regime Varejo', align: 'center', kind: 'tier_badge' },
		{ key: 'pms_yoy_pct', label: 'Serviços YoY', align: 'right', kind: 'growth', highlightThreshold: 0.05 },
		{ key: 'regime_serv', label: 'Regime Serviços', align: 'center', kind: 'tier_badge' }
	]}
/>
